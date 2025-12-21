import { _t } from "@web/core/l10n/translation";
import {
    diffColumn,
    getRangeFromDate,
    localStartOf,
    datePlus,   
} from "./gantt_helpers";
import { GanttRendererControls } from "@web_gantt/gantt_renderer_controls";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

const KEYS = ["startDate", "stopDate", "rangeId", "focusDate"];

patch( GanttRendererControls.prototype, {
    setup(){
        super.setup();
        this.metaData  = this.model.metaData;
    },
    isSelected(rangeId) {
        if (rangeId === "custom") {
            return (
                this.state.rangeId === rangeId ||
                !localStartOf(this.state.focusDate, this.state.rangeId, this.metaData).equals(
                    localStartOf(DateTime.now(), this.state.rangeId, this.metaData)
                )
            );
        }
        return (
            this.state.rangeId === rangeId &&
            localStartOf(this.state.focusDate, rangeId, this.metaData).equals(
                localStartOf(DateTime.now(), rangeId, this.metaData)
            )
        );
    },

    onTodayClicked() {
        const success = this.props.focusToday();
        if (success) {
            return;
        }
        this.state.focusDate = DateTime.local().startOf("day");
        if (this.state.rangeId === "custom") {
            const diff = diffColumn(this.state.startDate, this.state.stopDate, "day", this.metaData);
            const n = Math.floor(diff / 2);
            const m = diff - n;
            this.state.startDate = this.state.focusDate.minus({ day: n });
            this.state.stopDate = datePlus(this.state.focusDate, m - 1, "day", this.metaData);
        } else {
            this.state.startDate = this.state.focusDate.startOf(this.state.rangeId);
            this.state.stopDate = this.state.focusDate.endOf(this.state.rangeId).startOf("day");
        }
        this.updatePickerValues();
        this.updateMetaData();
    },

    selectRange(direction) {
        const sign = direction === "next" ? 1 : -1;
        const { focusDate, rangeId, startDate, stopDate } = this.state;
        if (rangeId === "custom") {
            const diff = diffColumn(startDate, stopDate, "day", this.metaData) + 1;
            this.state.focusDate = datePlus(focusDate, sign * diff, "day", this.metaData);
            this.state.startDate = datePlus(startDate, sign * diff, "day", this.metaData);
            this.state.stopDate = datePlus(stopDate, sign * diff, "day", this.metaData);
        } else {
            Object.assign(
                this.state,
                getRangeFromDate(rangeId, datePlus(focusDate, sign, rangeId, this.metaData), this.metaData)
            );
        }
        this.updatePickerValues();
        this.updateMetaData();
    },

});
