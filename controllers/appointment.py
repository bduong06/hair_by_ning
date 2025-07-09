# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.appointment.controllers.appointment import AppointmentController

import json
from collections import defaultdict

class HairByNingAppointmentController(AppointmentController):

    @route(['/hbn/appointment', '/hbn/appointment/page/<int:page>'],
           type='json', auth="public", website=True, sitemap=True)
    def appointment_type_list(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        kwargs['domain'] = self._appointment_website_domain()
        appointment_types = self._prepare_appointments_list_data(**kwargs)
        result = defaultdict(list)
        for appointment in appointment_types['appointment_types']:
            data = {
                'id': appointment.id,
                'name': appointment.name,
            }
            result[appointment.location].append(data)

        return result