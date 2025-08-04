# Part of Odoo. See LICENSE file for full copyright and licensing details.
 
from babel.dates import format_datetime, format_date, format_time
from odoo.http import request, route
from odoo.addons.appointment.controllers.appointment import AppointmentController
from werkzeug.exceptions import Forbidden, NotFound
from urllib.parse import unquote_plus
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import babel_locale_parse, get_lang
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf, email_normalize

import json
from collections import defaultdict

def _formated_weekdays(locale):
    """ Return the weekdays' name for the current locale
        from Mon to Sun.
        :param locale: locale
    """
    formated_days = [
        format_date(date(2021, 3, day), 'EEE', locale=locale)
        for day in range(1, 8)
    ]
    # Get the first weekday based on the lang used on the website
    first_weekday_index = babel_locale_parse(locale).first_week_day
    # Reorder the list of days to match with the first weekday
    formated_days = list(formated_days[first_weekday_index:] + formated_days)[:7]
    return formated_days

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
                'max_capacity': appointment.resource_count
            }
            result[appointment.location].append(data)

        return result

    @route(['/hbn/appointment/<int:appointment_type_id>'],
           type='json', auth="public", website=True, sitemap=True)
    def appointment_type_time_slots(self, appointment_type_id, state=False, staff_user_id=False, resource_selected_id=False, **kwargs):
        """
        This route renders the appointment page: It first computes a dict of values useful for all potential
        views and to choose between them in _get_appointment_type_page_view, that renders the chosen one.

        :param appointment_type_id: the appointment_type_id of the appointment type that we want to access
        :param state: the type of message that will be displayed in case of an error/info. Possible values:
            - cancel: Info message to confirm that an appointment has been canceled
            - failed-staff-user: Error message displayed when the slot has been taken while doing the registration
        :param staff_user_id: id of the selected user, from upstream or coming back from an error.
        :param resource_selected_id: id of the selected resource, from upstream or coming back from an error.
        """


        kwargs['domain'] = self._appointments_base_domain(
            filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'),
            search=kwargs.get('search'),
            invite_token=kwargs.get('invite_token'),
            additional_domain=kwargs.get('domain')
        )
        available_appointments = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('filter_resource_ids'),
            kwargs.get('invite_token'),
            domain=kwargs['domain']
        )
        appointment_type = available_appointments.filtered(lambda appt: appt.id == int(appointment_type_id))

        kwargs['available_appointments'] = available_appointments
        if not appointment_type:
            raise NotFound()

        page_values = self._prepare_appointment_type_page_values(appointment_type, staff_user_id, resource_selected_id, **kwargs)
        time_slots = self._get_appointment_type_time_slots(appointment_type, page_values, state, **kwargs)
        slots = []
        for slot in time_slots["slots"]:
            for week in slot["weeks"]:
                for day in week:
                    if(len(day['slots']) > 0):
                        slots.append(day)

        appointment = {"appointment_type_id": appointment_type.id, "name": appointment_type.name, "location": appointment_type.location, 
            "appointment_tz": appointment_type.appointment_tz, "assign_method": appointment_type.assign_method, 
            "asked_capacity": page_values["asked_capacity"], "slots": slots
        }
        return appointment

    def _get_appointment_type_time_slots(self, appointment_type, page_values, state=False, **kwargs):
        """
        Renders the appointment information alongside the calendar for the slot selection, after computation of
        the slots and preparation of other values, depending on the arguments values. This is the method to override
        in order to select another view for the appointment page.

        :param appointment_type: the appointment type that we want to access.
        :param page_values: dict containing common appointment page values. See _prepare_appointment_type_page_values for details.
        :param state: the type of message that will be displayed in case of an error/info. See appointment_type_page.
        """
        request.session.timezone = self._get_default_timezone(appointment_type)
        asked_capacity = int(kwargs.get('asked_capacity', 1))
        filter_prefix = 'user' if appointment_type.schedule_based_on == "users" else 'resource'
        slots_values = self._get_slots_values(appointment_type,
            selected_filter_record=page_values[f'{filter_prefix}_selected'],
            default_filter_record=page_values[f'{filter_prefix}_default'],
            possible_filter_records=page_values[f'{filter_prefix}s_possible'],
            asked_capacity=asked_capacity)
        formated_days = _formated_weekdays(get_lang(request.env).code)

        return {
            'appointment_type': appointment_type,
            'is_html_empty': is_html_empty,
            'formated_days': formated_days,
            'main_object': appointment_type,
            'month_kept_from_update': False,
            'state': state,
            'timezone': request.session['timezone'],  # bw compatibility
            **page_values,
            **slots_values,
        }

    def _get_slots_from_filter(self, appointment_type, filter_records, asked_capacity=1, **kwargs):
        """
        Compute the slots and the first month that has available slots from the given filter.

        :param appointment_type: the appointment type that we want to access.
        :param filter_records: users/resources that are used to compute the slots
        :param asked_capacity: the capacity asked by the user
        :return: a dict containing:
            - slots: the available slots
            - month_first_available: the first month that has available slots or False if there is none
        """

        if kwargs.get('date'):
            reference_date = datetime.strptime(kwargs.get('date'), "%Y-%m-%d")
        else:
            reference_date = None

        slots = appointment_type._get_appointment_slots(
            request.session['timezone'],
            filter_users=filter_records if appointment_type.schedule_based_on == "users" else None,
            filter_resources=filter_records if appointment_type.schedule_based_on == "resources" else None,
            asked_capacity=asked_capacity,
            reference_date=reference_date,
        )
        return {
            'slots': slots,
            'month_first_available': next((month['id'] for month in slots if month['has_availabilities']), False),
        }

    @route(['/hbn/appointment/<int:appointment_type_id>/info'],
            type='json', auth="public", website=True, sitemap=False)
    def appointment_type_form(self, appointment_type_id, **kwargs):
        """
        Render the form to get information about the user for the appointment

        :param appointment_type_id: the appointment type id related
        :param date_time: the slot datetime selected for the appointment
        :param duration: the duration of the slot
        :param staff_user_id: the user selected for the appointment
        :param resource_selected_id: the resource selected for the appointment
        :param available_resource_ids: the resources info we want to propagate that are linked to the slot time
        :param asked_capacity: the asked capacity for the appointment
        :param filter_appointment_type_ids: see ``Appointment.appointments()`` route
        """
        date_time = unquote_plus(kwargs.get('date_time'))
        duration = unquote_plus(kwargs.get('duration'))
        staff_user_id = None if kwargs.get('staff_user_id') is None else unquote_plus(kwargs.get('staff_user_id'))
        resource_selected_id = None if kwargs.get('resource_selected_id') is None else unquote_plus(kwargs.get('resource_selected_id'))
        available_resource_ids = None if kwargs.get('available_resource_ids') is None else unquote_plus(kwargs.get('available_resource_ids'))
        asked_capacity = 1 if kwargs.get('asked_capacity') is None else unquote_plus(kwargs.get('asked_capacity'))
        kwargs = {}

        domain = self._appointments_base_domain(
            filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'),
            search=kwargs.get('search'),
            invite_token=kwargs.get('invite_token')
        )
        available_appointments = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('filter_resource_ids'),
            kwargs.get('invite_token'),
            domain=domain,
        )
        appointment_type = available_appointments.filtered(lambda appt: appt.id == int(appointment_type_id))

        if not appointment_type:
            raise NotFound()

        if not self._check_appointment_is_valid_slot(appointment_type, staff_user_id, resource_selected_id, available_resource_ids, date_time, duration, asked_capacity, **kwargs):
            raise NotFound()

        partner = self._get_customer_partner()
        partner_data = partner.read(fields=['name', 'phone', 'email'])[0] if partner else {}
        date_time = unquote_plus(date_time)
        date_time_object = datetime.strptime(date_time, dtf)
        day_name = format_datetime(date_time_object, 'EEE', locale=get_lang(request.env).code)
        date_formated = format_date(date_time_object.date(), locale=get_lang(request.env).code)
        time_locale = format_time(date_time_object.time(), locale=get_lang(request.env).code, format='short')
        resource = request.env['appointment.resource'].sudo().browse(int(resource_selected_id)) if resource_selected_id else request.env['appointment.resource']
        staff_user = request.env['res.users'].browse(int(staff_user_id)) if staff_user_id else request.env['res.users']
        users_possible = self._get_possible_staff_users(
            appointment_type,
            json.loads(unquote_plus(kwargs.get('filter_staff_user_ids') or '[]')),
        )
        resources_possible = self._get_possible_resources(
            appointment_type,
            json.loads(unquote_plus(kwargs.get('filter_resource_ids') or '[]')),
        )
        return { 'partner_data': partner_data,
            'appointment_type': appointment_type,
            'available_appointments': available_appointments,
            'main_object': appointment_type,
            'datetime': date_time,
            'date_locale': f'{day_name} {date_formated}',
            'time_locale': time_locale,
            'datetime_str': date_time,
            'duration_str': duration,
            'duration': float(duration),
            'staff_user': staff_user,
            'resource': resource,
            'asked_capacity': int(asked_capacity),
            'timezone': request.session.get('timezone') or appointment_type.appointment_tz,  # bw compatibility
            'users_possible': users_possible,
            'resources_possible': resources_possible,
            'available_resource_ids': available_resource_ids,
        }