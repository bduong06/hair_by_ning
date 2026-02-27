import { onWillStart, onRendered } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";


export class HBNAppointmentTypeSyncDuration extends Many2OneField {

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
                    this.props.record.update({'duration': appointmentDuration[0].appointment_duration});
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
                        this.clearVariant();
                    }
                }
            }
        });
    }
    clearVariant(){
        var el = document.querySelector('[name="product_variant_id"]')?.querySelector('input');
        el.value = "";

    }
};

registry.category("fields").add("hbn_appointment_type_sync_duration", {
    ...many2OneField,
    component: HBNAppointmentTypeSyncDuration,
});
