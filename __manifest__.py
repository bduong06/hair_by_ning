# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hair By Ning Appointments',
    'version': '1.0',
    'category': 'Services/Appointment',
    'sequence': 6,
    'summary': 'Allow people to book services',
    'description': """
Allow clients to Schedule Appointments through the Portal
    """,
    'depends': ['appointment'],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'hair_by_ning/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
