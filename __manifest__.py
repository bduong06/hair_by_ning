# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hair By Ning Appointments',
    'version': '1.0',
    'category': 'Services/Appointment',
    'summary': 'Allow people to book services',
    'description': """
Allow clients to Schedule Appointments through the Portal
    """,
    'depends': ['base', 'calendar', 'web', 'resource', 'web_gantt', 'appointment', 'mail','account_payment', 
    'sale', 'sale_loyalty','account', 'point_of_sale'],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'hair_by_ning/static/src/**/*',
            ('remove', 'hair_by_ning/static/src/views/gantt/**'),
        ],
        'web.assets_backend_lazy': [
            'hair_by_ning/static/src/views/gantt/**',
        ],
    },
    'data': [
        'views/calendar_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
}
