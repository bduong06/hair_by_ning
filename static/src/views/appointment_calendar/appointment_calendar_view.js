import { registry } from "@web/core/registry";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { calendarView } from "@web/views/calendar/calendar_view";

export const AppointmentBookingAttendeeCalendarView = {
    ...calendarView,
    Controller: AttendeeCalendarController,
    Model: AttendeeCalendarModel,
    Renderer: AttendeeCalendarRenderer,
};

registry.category("views").add("appointment_booking_form", AppointmentBookingAttendeeCalendarView);
