/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { rpc } from "@web/core/network/rpc";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useRef, useState, useSubEnv, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { user } from "@web/core/user";
import { CustomAppointmentFormViewDialog } from "@appointment/views/custom_appointment_form_dialog/custom_appointment_form_dialog";
const { DateTime } = luxon;

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        if(this.props.context === undefined){
            this.props.context = {};
        }
        this.props.context.no_mail_to_attendees = true;
        this.actionService = useService('action');
    },

    createRecord(record) {
        if (!this.model.canCreate) {
            return;
        }
        const currentAction = this.actionService.currentController;
        if(currentAction.action.xml_id === 'appointment.calendar_event_action_view_bookings_resources'){
            const context = this._getContext(record.start);
            this.openDialog({ context });
        } else {
            super.createRecord(record);
        }
    },
    /**
     * @override
     * When creating a new booking using the "New" button, round the start datetime to the next
     * half-hour (e.g. 10:12 => 10:30, 11:34 => 12:00).
     * The stop datetime is set by default to start + 1 hour to override the calendar.event's default_stop, which is currently setting the stop based on now instead of start.
     * The stop datetime will be updated in the default_get method on python side to match the appointment type duration.
    */
    onClickAddButton() {
        const currentAction = this.actionService.currentController;
        if(currentAction.action.xml_id === 'appointment.calendar_event_action_view_bookings_resources') {
            const focusDate = DateTime.now();
            const context = this._getContext(focusDate);
            this.openDialog({ context });
        } else {
            super.onClickAddButton();
        }
    },

    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props FormViewDialog props
     * @param {Record<string, any>} [options={}]
     */
    openDialog(props, options = {}) {
        const { canDelete, canEdit, resModel, formViewId: viewId } = this.model.meta;

        const title = props.title || (props.resId ? _t("Open") : _t("Create"));

        let removeRecord;
        if (canDelete && props.resId) {
            removeRecord = () => {
                return new Promise((resolve) => {
                    this.displayDialog(ConfirmationDialog, {
                        body: _t("Are you sure to delete this record?"),
                        confirm: async () => {
                            await this.orm.unlink(resModel, [props.resId]);
                            resolve();
                        },
                        cancel: () => {},
                    }); 
                });
            };
        }

        this.closeDialog = this.displayDialog(
            FormViewDialog,
            {
                title,
                resModel,
                viewId,
                resId: props.resId,
                size: props.size,
                mode: canEdit ? "edit" : "readonly",
                context: props.context,
                removeRecord,
            },
            {
                ...options,
                onClose: () => {
                    this.closeDialog = null;
                    this.model.load();
                },
            }
        );
    },
    _getContext(startDate){
        const context = this.props.context;
        const start =
            startDate.minute > 30
                ? startDate.set({ hour: startDate.hour + 1, minute: 0, second: 0 })
                : startDate.set({ hour: startDate.hour, minute: 30, second: 0 });
        const stop = start.plus({ hour: 1 });
        context.default_appointment_status = 'request';
        context.default_name = 'default_name';
        context.start = serializeDateTime(start);
        context.stop = serializeDateTime(stop);
        context.default_start = serializeDateTime(start);
        context.default_stop = serializeDateTime(stop);
        return context;
    }
});
