import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { patch } from "@web/core/utils/patch";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

patch(CalendarCommonPopover.prototype, {

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    },
    onEditEvent(){
        const record = this.props.record;
            const resId = record.id;
            const resModel = this.props.model.resModel;
            const canDelete = this.props.model.canDelete;
            const canEdit = this.props.model.canEdit;
            const title = this.props.title || (resId ? _t("Open") : _t("Create"));

            let removeRecord;
            if (canDelete && resId) {
                removeRecord = () => {
                    return new Promise((resolve) => {
                        this.dialogService.add(ConfirmationDialog, {
                            body: _t("Are you sure to delete this record?"),
                            confirm: async () => {
                                await this.orm.unlink(resModel, [resId]);
                                resolve();
                            },
                            cancel: () => {},
                        });
                    });
                };
            }
            this.props.model.meta.context.form_view_ref = "hair_by_ning.calendar_event_view_form_gantt_booking_inherit_hair_by_ning";

            this.closeDialog = this.dialogService.add(
                FormViewDialog,
                {
                    title,
                    resModel,
//                    viewId,
                    resId,
                    size: this.props.size,
                    mode: canEdit ? "edit" : "readonly",
                    context: this.props.model.meta.context,
                    removeRecord,
                },
                {
//                    ...options,
                    onClose: () => {
                        this.closeDialog = null;
                        this.props.model.load();
                    },
                }
            );
        }
});
