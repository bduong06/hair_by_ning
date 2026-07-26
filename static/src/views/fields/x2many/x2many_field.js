/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

patch(X2ManyField.prototype, {
    async openRecord(record) {
        if (this.canOpenRecord) {
            let mode = this.props.readonly ? "readonly" : "edit";
            
            if (this.props.context?.quickEditMode === "on") {
                mode = "edit"; 
            }

            return this._openRecord({
                record,
                context: this.props.context,
                mode: mode,
            });
        }
    }
});