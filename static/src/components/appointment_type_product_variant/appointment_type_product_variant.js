import { onWillStart, onMounted, onWillRender } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";

export class AppointmentTypeProductVariant extends Many2OneField {

    setup() {
        super.setup();
        this.appointmentTypeId = this.props.record.data.appointment_type_id[0];
        this.isDefaultDuration = false;
        this.attribute_name = false;

        onWillStart(async () => {
            if (this.appointmentTypeId) {
                this.attribute_name = await this.orm.call(
                    "calendar.event", "get_attribute_name", [this.appointmentTypeId]
                );
            }
        });
        useRecordObserver(async (record) => {
            if (record.data.appointment_type_id[0] !== this.appointmentTypeId) {
                this.appointmentTypeId = record.data.appointment_type_id[0];
                if (this.appointmentTypeId) {
                    this.attribute_name = await this.orm.call(
                        "calendar.event", "get_attribute_name", [this.appointmentTypeId]
                    );
                    this.clearVariant();
                }
            }
        });
        onWillRender(() => {
            const label = document.querySelector(".product_variant_id_label");
            if(label){
                label.firstChild.textContent = this.attribute_name;
            }
        })
        onMounted(() => {
            if(this.displayName) {
                const variant = this.displayName.replace(/.*\(|\).*/g, '');
                this.autocompleteContainerRef.el.querySelector('input').value = variant;
            }
            const label = document.querySelector(".product_variant_id_label");
            if(label){
                label.firstChild.textContent = this.attribute_name;
            }
        });
    }
    clearVariant(){
        var el = document.querySelector('[name="product_variant_id"]')?.querySelector('input');
        el.value = "";

    }
};

registry.category("fields").add("appointment_type_product_variant", {
    ...many2OneField,
    component: AppointmentTypeProductVariant,
});
