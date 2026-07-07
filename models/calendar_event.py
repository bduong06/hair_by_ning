# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools import config

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    sale_order_id = fields.Many2one('sale.order', string="Sales Order")

    deposit_amount = fields.Integer(
        string="Deposit Amount",
        compute='_compute_deposit_amount',
        inverse='_inverse_compute_deposit_amount',
    )

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
        compute="_compute_product_variant_id",
        inverse="_inverse_resource_ids_or_capacity",
        string="Variant",
    )

    total_price = fields.Float(
        string="Total Price",
        compute="_compute_total_price"
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id, 
        readonly=True
    )

    booking_id = fields.Char(
        string="Booking ID",
        store=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        resource_ids = self.env.context.get('default_resource_ids', [])
        if res.get('appointment_type_id') and resource_ids and 'appointment_type_id' in fields_list:
            res['appointment_type_id'] = False
        return res
        
    @api.depends('appointment_type_id')
    def _compute_deposit_amount(self):
        for record in self:
            for booking_line in record.booking_line_ids:
                price_unit = booking_line.product_variant_id.lst_price,
                if price_unit[0] <= 500:
                    record.deposit_amount += 150
                else:
                    record.deposit_amount += 300

    @api.depends('appointment_type_id')
    def _inverse_compute_deposit_amount(self):
        pass

    @api.depends('appointment_type_id', 'booking_line_ids')
    def _compute_product_variant_id(self):
        for record in self:
            if self.resource_total_capacity_reserved and record.booking_line_ids:
                    booking_line = record.booking_line_ids[0]
                    record.product_variant_id = booking_line.product_variant_id
            else:    
                record.product_variant_id = None

    @api.depends('appointment_type_id')
    def _compute_product_tmpl_id(self):
        for record in self:
            record.product_tmpl_id = record.appointment_type_id.product_id.product_tmpl_id.id

    @api.depends('booking_line_ids', 'booking_line_ids.product_variant_id')
    def _compute_total_price(self):
        for record in self:
            for product in record.booking_line_ids.product_variant_id:
                record.total_price += product.lst_price

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
        for vals in vals_list:
            if vals['name'] == 'default_name':
                vals['name'] = self._set_event_name(vals)
            vals['booking_id'] = self.env['ir.sequence'].next_by_code('booking_sequence_code')

            if 'resource_ids' in vals and not vals['resource_ids']:
                appointment_type_id = vals.get('appointment_type_id')
                start_str = vals.get('start')
                stop_str = vals.get('stop')

                if appointment_type_id and start_str and stop_str:
                    appt_type = self.env['appointment.type'].browse(appointment_type_id)
                    
                    # Convert Odoo's string timestamps to Python datetime objects for math
                    start_date = fields.Datetime.from_string(start_str)
                    stop_date = fields.Datetime.from_string(stop_str)

                    # --- NEW: Check for specialized salon service buffers ---
                    # Let's say your wife's blonde service has a specific keyword or code
                    # You can also add a custom integer field 'x_buffer_minutes' to the appointment.type model!
                    #buffer_minutes = 0
                    #if 'blonde' in appt_type.name.lower():
                    #    buffer_minutes = 45  # Add a 45-minute buffer for blonde sessions
                    #elif 'extension' in appt_type.name.lower():
                    #    buffer_minutes = 30  # Add a 30-minute buffer for extensions

                    #if buffer_minutes > 0:
                        # Dynamically extend the stop time to block out the chair buffer
                    #    stop_date = stop_date + timedelta(minutes=buffer_minutes)
                        # Update the values dictionary so Odoo physically saves the longer slot
                    #    vals['stop'] = fields.Datetime.to_string(stop_date)

                    # --- Resource Chair Check (Using the updated stop_date) ---
                    if appt_type.schedule_based_on == 'resources':
                        available_chairs = appt_type.resource_ids
                        assigned_chair = False
                        
                        vals['resource_ids'] = []
                        for chair in available_chairs:
                            # Scan for overlaps against the extended duration
                            overlapping_booking = self.env['calendar.event'].sudo().search([
                                ('resource_ids', '=', chair.id),
                                ('start', '<', fields.Datetime.to_string(stop_date)), #type: ignore
                                ('stop', '>', fields.Datetime.to_string(start_date)), #type: ignore
                            ], limit=1)
                            
                            if not overlapping_booking:
                                vals['resource_ids'].append([4, chair.id])
                                assigned_chair += 1

                            if assigned_chair == vals['resource_total_capacity_reserved']:
                                break

                        if not assigned_chair:
                            raise ValidationError(_(
                                "There are no chairs available for this time slot"
                            ))

        return super(CalendarEvent, self).create(vals_list)

    def action_make_deposit(self):
        self.ensure_one()
        
        # 1. Prevent duplicate orders
        if self.sale_order_id:
            return True

        dep_amount = self.deposit_amount

        order_line = []
        for booking_line in self.booking_line_ids:
            order_line.append((0, 0, {
                'product_id': booking_line.product_variant_id.id,
                'name': booking_line.display_name,
                'product_uom_qty': booking_line.capacity_reserved,
                'price_unit': booking_line.product_variant_id.lst_price,
            }))

        # 3. Create the Sales Order for the service booking
        order = self.env['sale.order'].create({
            'partner_id': self.partner_ids.id,
            'origin': self.name,
            'order_line': order_line,
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
        dp_invoice = self.env['account.move'].browse(action_values['res_id']) #type: ignore
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
        final_invoices = order.env['account.move'].browse(invoice_ids)  #type: ignore
        invoice_url = ''
        for invoice in final_invoices:
            if invoice.state == 'draft':
                invoice.write({
                    'invoice_date_due': self.start,
                    'invoice_payment_term_id': False 
                })
                invoice_url = f"/inv/{invoice.id}"

        base_url = config.get("base_url", "https://hairbyning.com")
        uri = f"{base_url}/{invoice_url}"

        # 4. Link it back to the booking
        self.sale_order_id = order.id
        self.appointment_status = 'booked'
        
        attendee = self.env['calendar.attendee'].search([('event_id', '=', self.id)])
        if attendee.partner_id.line_user_id or attendee.partner_id.mm_channel_count:  #type: ignore
            attendee._send_appointment_confirmation(uri) #type: ignore

        # Log to chatter so the admin sees it
        self.message_post(body=f"✅ Deposit Order {order.name} created.")

        return True

    def action_checkout_booking(self):
        self.ensure_one()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        res_id = None
        for invoice in self.invoice_ids:
            if invoice.state == 'draft':
                res_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',  # Target model
            'name': 'Open',  # Target model
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'view_id': self.env.ref('account.view_move_form').id, # Specific View
            'target': 'new', # Key to open in a dialog
            'flags': {'initial_mode': 'view'}, # Opens in readonly
            'context': {
                'default_move_type': 'out_invoice',
                # Add default values here
            },
        }

    @api.model
    def get_attribute_name(self, appointment_type_id):
        appointment = self.env['appointment.type'].sudo().browse(appointment_type_id)
        return appointment.product_id.product_tmpl_id.attribute_line_ids.display_name

    def _set_event_name(self, values):
        appointment_type = self.env['appointment.type'].browse(values['appointment_type_id'])
        partner = self.env['res.partner'].browse(values['partner_ids'][0][1])
        return f"{partner.name} - {appointment_type.name} Booking"

    def _inverse_resource_ids_or_capacity(self):
        """Update booking lines as inverse of both resource capacity and resource_ids.

        As both values are related to the booking line and resource capacity is dependant
        on resources existing in the first place. They need to both use the same inverse
        field to ensure there is no ordering conflict.
        """
        booking_lines = []
        booking_lines_to_delete = self.env['appointment.booking.line']
        for event in self:
            resources = event.resource_ids
            if resources:
                # Ignore the inverse and keep the previous booking lines when we duplicate an event
                if self.env.context.get('is_appointment_copied'):
                    continue
                if event.appointment_type_manage_capacity and event.resource_total_capacity_reserved:
                    capacity_to_reserve = event.resource_total_capacity_reserved
                else:
                    capacity_to_reserve = sum(event.booking_line_ids.mapped('capacity_reserved')) or sum(resources.mapped('capacity'))
                booking_lines_to_delete |= event.booking_line_ids
                for resource in resources.sorted("shareable"):
                    if event.appointment_type_manage_capacity and capacity_to_reserve <= 0:
                        break
                    booking_lines.append({
                        'product_variant_id': event.product_variant_id.id,
                        'appointment_resource_id': resource.id,
                        'calendar_event_id': event.id,
                        'capacity_reserved': min(resource.capacity, capacity_to_reserve),
                    })
                    capacity_to_reserve -= min(resource.capacity, capacity_to_reserve)
                    capacity_to_reserve = max(0, capacity_to_reserve)
            else:
                booking_lines_to_delete |= event.booking_line_ids
        booking_lines_to_delete.unlink()
        self.env['appointment.booking.line'].sudo().create(booking_lines)