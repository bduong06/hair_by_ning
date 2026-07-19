import { _t } from "@web/core/l10n/translation";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

function useUniqueDialog() {
    const displayDialog = useOwnedDialogs();
    let close = null;
    return (...args) => {
        if (close) {
            close();
        }
        close = displayDialog(...args);
    };
}

patch(ListController.prototype, {
    setup() {
        super.setup();
    },
    async openRecord(record, force = false) {
        const dirty = await record.isDirty();
        if (dirty) {
            await record.save();
        }
        const currentController = this.actionService.currentController;
        if(currentController.action.xml_id == 'appointment.calendar_event_action_view_bookings_resources') {
            const resId = record.resId;
            const resModel = record.resModel;
            const canDelete = this.archInfo.activeActions.delete;
            const canEdit = this.archInfo.activeActions.edit;
            const title = this.props.title || (resId ? _t("Open") : _t("Create"));

            let removeRecord;
            if (canDelete && resId) {
                removeRecord = () => {
                    return new Promise((resolve) => {
                        this.dialogService.add(ConfirmationDialog, {
                            body: _t("Are you sure to delete this record?"),
                            confirm: async () => {
                                await this.props.model.orm.unlink(resModel, [resId]);
                                resolve();
                            },
                            cancel: () => {},
                        });
                    });
                };
            }
            this.props.context.form_view_ref = "hair_by_ning.calendar_event_view_form_gantt_booking_inherit_hair_by_ning";

            this.closeDialog = this.dialogService.add(
                FormViewDialog,
                {
                    title,
                    resModel,
                    resId,
                    size: this.props.size,
                    mode: canEdit ? "edit" : "readonly",
                    context: this.props.context,
                    removeRecord,
                },
                {
                    onClose: () => {
                        this.closeDialog = null;
                        this.model.load();
                    },
                }
            );
        } else {
            if (this.props.allowOpenAction && this.archInfo.openAction) {
                this.actionService.doActionButton({
                    name: this.archInfo.openAction.action,
                    type: this.archInfo.openAction.type,
                    resModel: record.resModel,
                    resId: record.resId,
                    resIds: record.resIds,
                    context: record.context,
                    onClose: async () => {
                        await record.model.root.load();
                    },
                });
            } else {
                    const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
                    this.props.selectRecord(record.resId, { activeIds, force });

            }
        }
    },
});
