import { getLocalWeekNumber, is24HourFormat } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { renderToString } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { getColor } from "@web/views/calendar/colors";

import { Component } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

patch(CalendarCommonRenderer.prototype, {
    setup() {
        super.setup();
    }
/*    async getPopoverProps(record) {
        const popoverProps = super.getPopoverProps(record);
        const partner_ids = record.partner_ids || [];
        let contact_partner_id = false;
        if (record.partner_ids) {
            contact_partner_id = record.partner_id
            ? partner_ids.find(partner_id => partner_id != record.partner_id[0])
            : partner_ids.length ? partner_ids[0] : false;
        }
        const popoverValues = contact_partner_id
            ? await this.orm.read(
                'res.partner',
                [contact_partner_id], ['name', 'email', 'phone']
            )
            : [{
                id: false,
                name: '',
                email: '',
                phone: '',
            }];
        Object.assign(popoverProps, {
            buttons: this.getPopoverButtons(record),
            context: {
                ...popoverProps.context,
                can_edit: this.props.model.meta.canEdit,
                gantt_pill_contact_email: popoverValues[0].email,
                gantt_pill_contact_name: popoverValues[0].name,
                gantt_pill_contact_phone: popoverValues[0].phone,
            },
            title: popoverValues[0].name || this.getDisplayName(pill),
        });
        return popoverProps;

    },*/
/*    getPopoverButtons(record) {
        return [{
            class: "o_appointment_booking_confirm_status btn btn-sm btn-primary",
            onClick: () => {
                if (this.props.model.meta.canEdit && record.appointment_status) {
                    const newAppointmentStatus = document.querySelector('.o_appointment_booking_status').selectedOptions[0].value;
                    this.orm.write("calendar.event", [record.id], {
                        active: newAppointmentStatus !== 'cancelled',
                        appointment_status: newAppointmentStatus,
                    }).then(() => this.model.fetchData());
                }
            },
            text: this.props.model.meta.canEdit && record.appointment_status ? _t("Save & Close") : _t('Close'),
        }, {
            class: "btn btn-sm btn-secondary",
            onClick: () => this.model.mutex.exec(() => this.props.openDialog({ resId: record.id })),
            text: this.props.model.meta.canEdit ? _t("Edit") : _t("View"),
        }];
    },*/
})
