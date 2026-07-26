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
    'depends': ['base', 'calendar', 'web', 'resource', 'web_enterprise', 'web_gantt', 'appointment', 'mail','account_payment', 'portal', 
    'sale', 'sale_loyalty','account' ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'hair_by_ning/static/src/**/*',
            'hair_by_ning/static/src/css/custom.css',
            ('remove', 'hair_by_ning/static/src/views/gantt/**'),
        ],
        'web.assets_backend_lazy': [
            'hair_by_ning/static/src/views/gantt/**',
        ],
    },
    'data': [
        'data/hair_by_ning_sequence.xml',
        'views/calendar_views.xml',
        'views/res_partner_views.xml',
    ],
    'license': 'LGPL-3',
}
