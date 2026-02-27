# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
import logging
import json
from datetime import datetime, timedelta
from markupsafe import Markup

from odoo import _, api, Command, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.mail import email_normalize, email_split_tuples, html_sanitize, is_html_empty, plaintext2html
from odoo.osv import expression
from odoo.addons.appointment.utils import invert_intervals
from odoo.addons.resource.models.utils import Intervals, timezone_datetime
from odoo.tools import (
    create_index,
    float_is_zero,
    format_amount,
    format_date,
    is_html_empty,
    SQL,
)
from odoo.tools.mail import html_keep_url

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    sale_order_id = fields.Many2one('sale.order', string="Sales Order")
    deposit_amount = fields.Integer(string="Deposit Amount")

    sale_order = fields.Many2many(
        'sale.order', 
        string='Sale Order',
        compute='_compute_sale_order',
    )

    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        compute='_compute_invoice_ids'
    )

    variant_count = fields.Integer(
        compute='_compute_variant_count',
        string='Variants'
    )

    product_tmpl_id = fields.Many2one(
        'product.product',
        string='Product template',
        compute="_compute_product_tmpl_id"
    )

    product_variant_id = fields.Many2one(
        'product.product', 
        string="Product Variant",
        store=True
    )

    @api.depends('appointment_type_id')
    def _compute_product_tmpl_id(self):
        for record in self:
            record.product_tmpl_id = record.appointment_type_id.product_id.product_tmpl_id.id

    @api.depends('appointment_type_id')
    def _compute_variant_count(self):
        for record in self:
            record.variant_count = record.appointment_type_id.product_id.product_variant_count

    @api.depends('sale_order_id')
    def _compute_sale_order(self):
        for record in self:
            if record.sale_order_id:
                # Fetch lines from the related sale order
                record.sale_order = record.sale_order_id
            else:
                record.sale_order = False

    @api.depends('sale_order_id')
    def _compute_invoice_ids(self):
        for record in self:
            if record.sale_order_id.invoice_ids:
                # Fetch lines from the related sale order
                record.invoice_ids = record.sale_order_id.invoice_ids
            else:
                record.invoice_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values['name'] == 'default_name':
                values['name'] = self._set_event_name(values)
        return super().create(vals_list)

    def action_make_deposit(self):
        self.ensure_one()
        
        # 1. Prevent duplicate orders
        if self.sale_order_id:
            return True

        dep_amount = self.deposit_amount

        # 3. Create the Sales Order for the service booking
        order = self.env['sale.order'].create({
            'partner_id': self.partner_ids.id,
            'origin': self.name,
            'order_line': [
                # The Main Service Line
                (0, 0, {
                    'product_id': self.product_variant_id.id,
                    'name': self.name,
                    'product_uom_qty': self.attendees_count,
                    'price_unit': self.product_variant_id.lst_price,
                }),
            ],
        })
        order.action_confirm()

        #create order for the down payment
        create_values = {
            'advance_payment_method': 'fixed',
            'fixed_amount': dep_amount
        }
        down_payment_wizard = (self.env['sale.advance.payment.inv']
            .with_context({
                'active_model': order._name, 
                'active_ids': order.ids,
                'deduct_down_payments': True
            })
            .create(create_values)
        )

        #create and post down payment invoice
        action_values = down_payment_wizard.create_invoices()
        dp_invoice = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice.action_post()

        # 3. Register a payment for the down payment invoice
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', 
            active_ids=dp_invoice.ids
        ).create({
            'amount': dep_amount,
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id, # Replace with a valid journal
        })
        payment_register.action_create_payments()

        #create invoice with down payment deducted and leave it in draft, so items can be added at payment
        context = {
            'active_model': 'sale.order',
            'active_ids': [order.id],
            'open_invoice': False,
            'deduct_down_payments': True
        }
        down_payment_wizard = (order.env['sale.advance.payment.inv']
            .with_context(context).create({
                'advance_payment_method': 'delivered'
            })
        )
        action = down_payment_wizard.create_invoices()
        invoice_ids = action.get('res_id') or action.get('domain',[('id','in',[])])[0][2]
        final_invoices = order.env['account.move'].browse(invoice_ids)
        for invoice in final_invoices:
            if invoice.state == 'draft':
                invoice.write({
                    'invoice_date_due': self.start,
                    'invoice_payment_term_id': False 
                })

        # 4. Link it back to the booking
        self.sale_order_id = order.id
        self.appointment_status = 'booked'
        self.write({
            'sale_order_id': order.id,
            'appointment_status': 'booked'
        })
        
        # Log to chatter so the admin sees it
        self.message_post(body=f"✅ Deposit Order {order.name} created.")

        return True

    def action_pos_booking_checkout(self):
        self.ensure_one()
        # 1. Ensure a Sales Order exists
        if not self.sale_order_id:
            self.action_make_deposit()
        
        # 2. Get the URL for your POS Shop
        # Replace '1' with your actual POS Config ID
        pos_config = self.env['pos.config'].search([], limit=1)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        # 3. Create a URL with the SO ID as a parameter
        # We will 'catch' this parameter with JavaScript in the POS
        pos_url = f"{base_url}/pos/ui?config_id={pos_config.id}&order_id={self.sale_order_id.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': pos_url,
            'target': 'new', # Opens in a new tab so you don't lose the calendar
        }

    def _set_event_name(self, values):
        appointment_type = self.env['appointment.type'].browse(values['appointment_type_id'])
        partner = self.env['res.partner'].browse(values['partner_ids'][0][1])
        return f"{partner.name} - {appointment_type.name} Booking"

