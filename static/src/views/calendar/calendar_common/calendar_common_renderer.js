
import { CalendarCommonRenderer} from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { patch } from "@web/core/utils/patch";

patch(CalendarCommonRenderer.prototype, {

    get options() {
        const options =  {...super.options,
            slotMinTime: "11:00:00",
            slotMaxTime: "22:00:00"
        };
        return options;   
    }

});
