# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    color = fields.Integer(
        string='Color Index',
        compute='_compute_color'
    )

    _inherit = ['account.move']

    def _invoice_paid_hook(self):
        # OVERRIDE
        res = super()._invoice_paid_hook()
        for move in self:
            for line in move.invoice_line_ids:
                if not line.is_downpayment:
                    for sale_line in line.sale_line_ids:
                        if sale_line.order_id.amount_unpaid == 0.0:
                            event = self.env['calendar.event'].sudo().search([('sale_order_id', '=', sale_line.order_id.id)])
                            event.write({'appointment_status': 'attended'})
        return res

    @api.depends('name')
    def _compute_color(self):
        for record in self:
            if record.display_name == 'Paid':
                record.color = 10
            else:
                record.color = 5


    @api.depends('name', 'status_in_payment')
    def _compute_display_name(self):
        for record in self:
            if record.status_in_payment == 'paid':
                record.display_name = 'Paid'
            else:
                record.display_name = 'Not Paid'

