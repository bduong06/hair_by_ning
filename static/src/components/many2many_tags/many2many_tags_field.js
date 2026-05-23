/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsFieldColorEditable } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
patch(Many2ManyTagsFieldColorEditable.prototype, {
   setup() {
       super.setup();
       this.action = useService("action");
       this.dialogService = useService("dialog");
   },
   onTagClick(ev, record) {
        let removeRecord;
        const props = this.props;
        const title = props.title || (record.resId ? _t("Open") : _t("Create"));
        const resModel = this.relation;
        if (props.canDelete && record.resId) {
            removeRecord = () => {
                return new Promise((resolve) => {
                    this.displayDialog(ConfirmationDialog, {
                        body: _t("Are you sure to delete this record?"),
                        confirm: async () => {
                            await this.orm.unlink(resModel, [record.resId]);
                            resolve();
                        },
                        cancel: () => {},
                    }); 
                });
            };
        }

       this.dialogService.add(
            FormViewDialog, 
            {
                title,
                resModel,
                mode: props.canEdit ? "edit" : "readonly",
                resId: record.resId,
                context: this.props.context,
                preventCreate: true,
                preventEdit: true,
                removeRecord,
            },
            {
                onClose: () => {
                    this.closeDialog = null;
                    this.env.model.load();
                },
            }
        )
   }
})