# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AppointmentBookingLine(models.Model):
    _inherit = "appointment.booking.line"

    product_variant_id = fields.Many2one(
        'product.product', 
        string="Service",
        ondelete="cascade", 
        required=True
    )
