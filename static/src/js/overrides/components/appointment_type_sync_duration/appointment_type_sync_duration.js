import { onWillStart } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { AppointmentTypeSyncDuration } from "@appointment/components/appointment_type_sync_duration/appointment_type_sync_duration";
import { patch } from "@web/core/utils/patch";


patch(AppointmentTypeSyncDuration.prototype, {
    setup() {
        super.setup();
        this.appointmentTypeId = this.props.record.data.appointment_type_id[0];
        this.isDefaultDuration = false;

        onWillStart(async () => {
            if (this.appointmentTypeId) {
                const appointmentDuration = await this.orm.read(
                    "appointment.type", [this.appointmentTypeId], ['appointment_duration']
                );
                if(this.props.record.data.duration === appointmentDuration?.[0].appointment_duration) {
                    this.isDefaultDuration = true;
                } else {
                    this.isDefaultDuration = true;
                    this.props.record.data.duration = appointmentDuration?.[0].appointment_duration;
                }
            }
        });

        useRecordObserver(async (record) => {
            if (record.data.appointment_type_id[0] !== this.appointmentTypeId && this.isDefaultDuration) {
                this.appointmentTypeId = record.data.appointment_type_id[0];
                if (this.appointmentTypeId) {
                    const appointmentDuration = await this.orm.read(
                        "appointment.type", [this.appointmentTypeId], ['appointment_duration']
                    );
                    if (appointmentDuration.length !== 0) {
                        record.update({'duration': appointmentDuration[0].appointment_duration});
                    }
                }
            }
        });
    }
});

