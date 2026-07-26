# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.modules.registry import Registry
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import config
from odoo import _

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
                        if sale_line.amount_to_invoice == 0.0: 
                            event_id = self.env['calendar.event'].sudo().search([('sale_order_id', '=', sale_line.order_id.id)])
                            event_id.write({'appointment_status': 'attended'})
                            self._send_conversion_event(event_id)
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

    @api.model
    def _send_conversion_event(self, event_id):

        attendee = self.env['calendar.attendee'].search([('event_id', '=', event_id.id)])
        attendee.send_conversion_api_event() #type: ignore

    def _get_invoice_pdf_proforma(self):
        """ Generate the Proforma of the invoice.
        :return dict: the Proforma's data such as
        {'filename': 'INV_2024_0001_proforma.pdf', 'filetype': 'pdf', 'content': ...}
        """
        self.ensure_one()
        filename = self._get_invoice_proforma_pdf_report_filename()
        content, report_type = self.env['ir.actions.report']._pre_render_qweb_pdf('account.account_invoices', self.ids, data={'proforma': False})
        content_by_id = self.env['ir.actions.report']._get_splitted_report('account.account_invoices', content, report_type)
        return {
            'filename': filename,
            'filetype': 'pdf',
            'content': content_by_id[self.id],
        }
