# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import pytz
import re
import requests
from babel.dates import format_datetime, format_date, format_time
from dateutil.relativedelta import relativedelta
from odoo import http, Command, fields
from odoo.http import request, Response
import logging
from odoo.addons.appointment.controllers.appointment import AppointmentController
from werkzeug.exceptions import Forbidden, NotFound
from urllib.parse import unquote_plus
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.addons.base.models.ir_qweb import keep_query
from datetime import datetime, date
from odoo.tools import config
from odoo.addons.phone_validation.tools import phone_validation
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf, email_normalize

from collections import defaultdict

_logger = logging.getLogger(__name__)


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


    @http.route(['/hbn/appointment', '/hbn/appointment/page/<int:page>'],
           type='json', auth="public", website=False, sitemap=True)
    def appointment_type_list(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        new_context = request.env.context.copy()
        new_context.update({'lang': kwargs['context'].get('lang')})
        request.env.context = new_context

        kwargs['domain'] = self._appointment_website_domain()

        appointment_type_ids = request.env['appointment.type'].sudo().search(kwargs['domain']).ids

        appointment_types = request.env['appointment.type'].sudo().browse(appointment_type_ids).exists()

        appointment_types = appointment_types.filtered_domain(kwargs['domain'])

        result = defaultdict(list)
        for appointment in appointment_types:
            data = {
                'id': appointment.id,
                'name': appointment.name,
                'max_capacity': appointment.resource_count
            }
            result[appointment.location].append(data)
        

        return {
            'appointment_types' : result,
            'csrf_token' : request.csrf_token()
        }

    @http.route(['/hbn/appointment/appointment_type'],
           type='json', auth="public", website=False, sitemap=True)
    def appointment_type_time_slots(self, **kwargs):
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

        new_context = request.env.context.copy()
        new_context.update({'lang': kwargs['context'].get('lang')})
        request.env.context = new_context

        appointment_type_id = kwargs.get('appointment_type_id', False)
        staff_user_id = kwargs.get('staff_user_id')
        resource_selected_id = kwargs.get('resource_selected_id')
        state = kwargs.get('state')

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
        appointment_type = available_appointments.filtered(lambda appointment_type: appointment_type.id == int(appointment_type_id))

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

        product_tmpl_id = appointment_type.product_id.product_tmpl_id

        product_variants = []
        for product_variant in product_tmpl_id.product_variant_ids:
            product_variants.append({
                'name': product_variant.product_template_attribute_value_ids.name,
                'id': product_variant.id,
                'price_extra': product_variant.price_extra
            })

        appointment = {
            "appointment_type_id": appointment_type.id, 
            "name": appointment_type.name, 
            "location_str": appointment_type.location, 
            "duration_str": int(appointment_type.appointment_duration), 
            "appointment_tz": appointment_type.appointment_tz, 
            "assign_method": appointment_type.assign_method, 
            "asked_capacity": page_values["asked_capacity"], 
            "slots": slots,
            "service_name": product_tmpl_id.display_name,
            "list_price": product_tmpl_id.list_price,
            "product_variants": json.dumps(product_variants),
            "attribute_name": product_tmpl_id.attribute_line_ids.display_name,
        }
        return {'appointment': appointment}

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
        
        if request.env is not None:
            locale = get_lang(request.env).code
        else:
            locale = 'th_TH'

        formated_days = _formated_weekdays(locale)

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

        reference_date = datetime.strptime(kwargs.get('date', ""), "%Y-%m-%d")

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

    @http.route(['/hbn/appointment/info'],
            type='json', auth="public", website=False, sitemap=False)
    def appointment_type_form(self, **kwargs):
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
        new_context = request.env.context.copy()
        new_context.update({'lang': kwargs['context'].get('lang')})
        request.env.context = new_context

        if request.env is not None:
            locale = get_lang(request.env).code
        else:
            locale = 'th_TH'

        product_variant_id = kwargs.get('product_variant_id', 0)
        appointment_type_id = unquote_plus(kwargs.get('appointment_type_id', ""))
        date_time = unquote_plus(kwargs.get('date_time', ""))
        duration = unquote_plus(kwargs.get('duration', ""))
        staff_user_id = unquote_plus(kwargs.get('staff_user_id', ""))
        resource_selected_id = unquote_plus(kwargs.get('resource_selected_id', ""))
        available_resource_ids = unquote_plus(kwargs.get('available_resource_ids', ""))
        asked_capacity = unquote_plus(kwargs.get('asked_capacity', 1))
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

        products = []
        variants = request.env['product.product'].sudo().browse(list(map(int, product_variant_id)))
        for variant in variants:
            products.append({
                'name': variant.product_template_attribute_value_ids.name,
                'id': variant.id,
                'lst_price': variant.lst_price
            })

        partner = self._get_customer_partner()
        partner_data = partner.read(fields=['name', 'phone', 'email'])[0] if partner else {}
        date_time = unquote_plus(date_time)
        date_time_object = datetime.strptime(date_time, dtf)
        day_name = format_datetime(date_time_object, 'EEE', locale=locale)
        date_formated = format_date(date_time_object.date(), locale=locale)
        time_locale = format_time(date_time_object.time(), locale=locale, format='short')

        return { 'partner_data': partner_data,
            'products': json.dumps(products),
            'service_name': appointment_type.name,
            'appointment_type_id': appointment_type.id,
            'location': appointment_type.location,
            'datetime': date_time,
            'date_locale': f'{day_name} {date_formated}',
            'time_locale': time_locale,
            'datetime_str': date_time,
            'duration_str': duration,
            'duration': float(duration),
            'asked_capacity': int(asked_capacity),
            'timezone': request.session.get('timezone') or appointment_type.appointment_tz,  # bw compatibility
            'available_resource_ids': available_resource_ids,
        }

    @http.route(['/hbn/appointment/submit'],
                type='json', auth="public", website=False)
    def json_appointment_form_submit(self, **kwargs):
        """
        Create the event for the appointment and redirect on the validation page with a summary of the appointment.

        :param appointment_type_id: the appointment type id related
        :param datetime_str: the string representing the datetime
        :param duration_str: the string representing the duration
        :param name: the name of the user sets in the form
        :param phone: the phone of the user sets in the form
        :param email: the email of the user sets in the form
        :param staff_user_id: the user selected for the appointment
        :param available_resource_ids: the resources ids available for the appointment
        :param asked_capacity: asked capacity for the appointment
        :param str guest_emails: optional line-separated guest emails. It will
          fetch or create partners to add them as event attendees;
        """

        token = kwargs.get('cf-turnstile-response')
        remoteip = request.httprequest.headers.get('CF-Connecting-IP') or \
               request.httprequest.headers.get('X-Forwarded-For') or \
               request.httprequest.remote_addr

        validation = self._validate_turnstile(token, remoteip)

        if not validation['success']:
            # Invalid token - reject submission
            return {
                'status': 'error',
                'message': 'Verification failed',
                'errors': validation['error-codes']
            }

        new_context = request.env.context.copy()
        new_context.update({'lang': kwargs['context'].get('lang')})
        request.env.context = new_context

        appointment_type_id = kwargs.get('appointment_type_id', 0)
        product_variant_id = kwargs.get('product_variant_id', 0)
        datetime_str = kwargs.get('datetime_str', datetime.now())
        duration_str = kwargs.get('duration_str', 0)
        name = kwargs.get('name')
        phone = kwargs.get('phone')
        email = kwargs.get('email')
        available_resource_ids= kwargs.get('available_resource_ids')
        asked_capacity = kwargs.get('asked_capacity', 1)
        guest_emails_str= kwargs.get('guest_emails_str')
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
        timezone = request.session.get('timezone') or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        datetime_str = unquote_plus(datetime_str)
        if datetime_str:
            date_start = tz_session.localize(datetime.fromisoformat(datetime_str)).astimezone(pytz.utc).replace(tzinfo=None)
        else:
            date_start = tz_session.localize(datetime.now()).astimezone(pytz.utc).replace(tzinfo=None)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration_str)
        invite_token = kwargs.get('invite_token')

        staff_user = request.env['res.users']
        resources = request.env['appointment.resource']
        resource_ids = None
        asked_capacity = int(asked_capacity)
        resources_remaining_capacity = None
        if appointment_type.schedule_based_on == 'resources':
            resource_ids = json.loads(unquote_plus('available_resource_ids', ''))
            # Check if there is still enough capacity (in case someone else booked with a resource in the meantime)
            resources = request.env['appointment.resource'].sudo().browse(resource_ids).exists()
            if any(resource not in appointment_type.resource_ids for resource in resources):
                raise NotFound()
            resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(resources, date_start, date_end, with_linked_resources=False)
            if resources_remaining_capacity['total_remaining_capacity'] < asked_capacity:
                return request.redirect('/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-resource')))
        else:
            # check availability of the selected user again (in case someone else booked while the client was entering the form)
            staff_user = request.env['res.users'].sudo().search([('id', '=', int(kwargs.get('staff_user_id', 0)))])
            if staff_user not in appointment_type.staff_user_ids:
                raise NotFound()
            if staff_user and not staff_user.partner_id.calendar_verify_availability(date_start, date_end):
                return request.redirect('/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-staff-user')))

        guests = None
        if appointment_type.allow_guests:
            if guest_emails_str:
                guests = request.env['calendar.event'].sudo()._find_or_create_partners(guest_emails_str)

        customer = self._get_customer_partner()

        new_customer = not (customer.exists())

        phone = customer._phone_format(number=phone, country=self._get_customer_country()) or phone
        if new_customer:
            customer = request.env['res.partner'].sudo().search([
                                ('name', '=', name),
                                ('phone', '=', phone)
                        ])
            if not customer.exists():
                customer = customer.create({
                    'name': name,
                    'phone': customer._phone_format(number=phone, country=self._get_customer_country()) or phone,
                    'email': email,
                    'lang': request.lang.code,
                })
        else:
            if not customer.phone:
                customer.write({
                    'phone': customer._phone_format(number=phone, country=self._get_customer_country()) or phone 
                })

        # partner_inputs dictionary structures all answer inputs received on the appointment submission: key is question id, value
        # is answer id (as string) for choice questions, text input for text questions, array of ids for multiple choice questions.
        partner_inputs = {}
        appointment_question_ids = appointment_type.question_ids.ids
        for k_key, k_value in [item for item in kwargs.items() if item[1]]:
            question_id_str = re.match(r"\bquestion_([0-9]+)\b", k_key)
            if question_id_str and int(question_id_str.group(1)) in appointment_question_ids:
                partner_inputs[int(question_id_str.group(1))] = k_value
                continue
            checkbox_ids_str = re.match(r"\bquestion_([0-9]+)_answer_([0-9]+)\b", k_key)
            if checkbox_ids_str:
                question_id, answer_id = [int(checkbox_ids_str.group(1)), int(checkbox_ids_str.group(2))]
                if question_id in appointment_question_ids:
                    partner_inputs[question_id] = partner_inputs.get(question_id, []) + [answer_id]

        # The answer inputs will be created in _prepare_calendar_event_values from the values in answer_input_values
        answer_input_values = []
        base_answer_input_vals = {
            'appointment_type_id': appointment_type.id,
            'partner_id': customer.id,
        }

        for question in appointment_type.question_ids.filtered(lambda question: question.id in partner_inputs.keys()):
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda answer: answer.id in partner_inputs[question.id])
                answer_input_values.extend([
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=answer.id) for answer in answers
                ])
            elif question.question_type in ['select', 'radio']:
                answer_input_values.append(
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=int(partner_inputs[question.id]))
                )
            elif question.question_type in ['char', 'text']:
                answer_input_values.append(
                    dict(base_answer_input_vals, question_id=question.id, value_text_box=partner_inputs[question.id].strip())
                )

        booking_line_values = []
        if appointment_type.schedule_based_on == 'resources':
            capacity_to_assign = asked_capacity
            i = 0
            for resource in resources:
                resource_remaining_capacity =  appointment_type._get_resources_remaining_capacity(resources, date_start, date_end, with_linked_resources=False)
                new_capacity_reserved = min(resource_remaining_capacity, capacity_to_assign, resource.capacity)
                capacity_to_assign -= new_capacity_reserved
                booking_line_values.append({
                    'appointment_resource_id': resource.id,
                    'capacity_reserved': new_capacity_reserved,
                    'capacity_used': new_capacity_reserved if resource.shareable and appointment_type.resource_manage_capacity else resource.capacity,
                    'product_variant_id': int(product_variant_id[i]),
                })
                i += 1

        if invite_token:
            appointment_invite = request.env['appointment.invite'].sudo().search([('access_token', '=', invite_token)])
        else:
            appointment_invite = request.env['appointment.invite']

        return self._json_handle_appointment_form_submission(
            appointment_type, date_start, date_end, duration, answer_input_values, name,
            customer, appointment_invite, guests, staff_user, asked_capacity, booking_line_values
        )

    @http.route(['/hbn/appointment/payment/confirm/<int:partner_id>'],
                type='json', auth="public", website=False)
    def json_payment_confirm(self, partner_id):
        """
        Confirm appointment

        :param partner_id: Customer id
        """
        event_id = request.env['calendar.event'].sudo().search([('partner_ids', 'in', partner_id)], order='create_date desc', limit=1)

        try:
        
            if event_id.appointment_status == 'request':
                event_id.action_make_deposit()

            if event_id.appointment_status == 'attended':
                attendee = request.env['calendar.attendee'].sudo().search([('event_id', '=', event_id.id)])
                #attendee.send_booking_checkout_confirmation() #type: ignore
                attendee.send_after_service_message() #type: ignore

        except requests.RequestException as e:
            _logger.error("json_payment_confirm: Error confirming payment: %s", str(e))

        return Response("OK", status=200, mimetype='text/plain')

    @http.route(['/hbn/appointment/confirm/<int:event_id>'],
                type='http', auth="public", website=False)
    def appointment_confirm(self, event_id, **kwargs):
        """
        Confirm appointment

        :param event_id: Calendar event
        """
        appointment = request.env['calendar.event'].sudo().browse(event_id)
        result = appointment.action_make_deposit()
        if not result:
            _logger.error("json_appointment_confirm: unknown error")

        # 2. Return an HTML script back to the hidden frame.
        # 'window.parent' targets the main Odoo window.
        # In Odoo 18, location.reload() cleanly refreshes the open view data.
        return """
            <script type="text/javascript">
                if (window.parent) {
                    window.parent.location.reload();
                }
            </script>
        """

    @http.route(['/hbn/appointment/checkout/confirm/<int:event_id>'],
                type='http', auth="public", website=False)
    def appointment_checkout_confirm(self, event_id, **kwargs):
        """
        Confirm appointment

        :param event_id: Calendar event
        """
        attendee = request.env['calendar.attendee'].sudo().search([('event_id', '=', event_id)])
        attendee.send_booking_checkout_confirmation() #type: ignore

        # 2. Return an HTML script back to the hidden frame.
        # 'window.parent' targets the main Odoo window.
        # In Odoo 18, location.reload() cleanly refreshes the open view data.
        return """
            <script type="text/javascript">
                if (window.parent) {
                    window.parent.location.reload();
                }
            </script>
        """

    def _json_handle_appointment_form_submission(
        self, appointment_type,
        date_start, date_end, duration,  # appointment boundaries
        answer_input_values, name, customer, appointment_invite, guests=None,  # customer info
        staff_user=None, asked_capacity=1, booking_line_values=None  # appointment staff / resources
    ):
        """ This method takes the output of the processing of appointment's form submission and
            creates the event corresponding to those values. Meant for overrides to set values
            needed to set a specific redirection._id

            :returns: a dict of useful values used in the redirection to next step
        """
        event = request.env['calendar.event'].with_context(
            mail_notify_author=True,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            allowed_company_ids=self._get_allowed_companies(staff_user or appointment_type.create_uid).ids,
        ).sudo().create({
            'appointment_answer_input_ids': [Command.create(vals) for vals in answer_input_values],
            **appointment_type._prepare_calendar_event_values(
                asked_capacity, booking_line_values, duration,
                appointment_invite, guests, name, customer, staff_user, date_start, date_end
            ),
        })
        timezone =pytz.timezone(request.session.get('timezone', 'Asia/Bangkok'))
        data = {
            'total_price': event.total_price,
            'deposit_amount': event.deposit_amount,
            'service_name': event.name,
            'location': event.location,
            'guest_name': event.partner_ids.name,
            'phone': event.partner_ids.phone,
            'date': event.start_date,
            'start_datetime': event.start.astimezone(timezone),
            'stop_datetime': event.stop.astimezone(timezone),
            'guest_count': event.resource_total_capacity_reserved,
            'booking_id': event.booking_id
        }

        return {
            'status': 200,
            'data': data
        }

    def _validate_turnstile(self, token, remoteip=None):

        if request.httprequest.host == 'hairbyning.com':
            secret = config.get('turnstile_secret')
        else:
            secret = '1x0000000000000000000000000000000AA'

        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

        data = {
            'secret': secret,
            'response': token
        }

        if remoteip:
            data['remoteip'] = remoteip

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Turnstile validation error: {e}")
            return {'success': False, 'error-codes': ['internal-error']}