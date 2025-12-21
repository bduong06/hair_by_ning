import { _t } from "@web/core/l10n/translation";
import { CalendarModel } from "@web/views/calendar/calendar_model"
import { patch } from "@web/core/utils/patch";

patch( CalendarModel.prototype, {

    setup(params, services) {   
        super.setup(params, services);
    },

    /**
     * @protected
     */
    makeFilterAll(previousAllFilter, isUserOrPartner, sectionLabel) {
        return {
            type: "all",
            recordId: null,
            value: "all",
            label: isUserOrPartner ? _t("Everybody's calendars") : _t("Everything"),
            active: previousAllFilter
                ? previousAllFilter.active
                : this.meta.allFilter[sectionLabel] || true,
            canRemove: false,
            colorIndex: null,
            hasAvatar: false,
        };
    }
});
