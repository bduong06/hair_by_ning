import { _t } from "@web/core/l10n/translation";
import { GanttArchParser } from "@web_gantt/gantt_arch_parser";
import { visitXML } from "@web/core/utils/xml";
import { patch } from "@web/core/utils/patch";

patch(GanttArchParser.prototype, {
    parse(arch) {
        const archInfo = super.parse(arch);

        let slot_min_time;
        let slot_max_time;
        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "gantt": {
                    slot_min_time = node.getAttribute('slot_min_time');
                    slot_max_time = node.getAttribute('slot_max_time');
                    break;
                }
            }
        });

        return {
            ...archInfo,
            slotMinTime: slot_min_time,
            slotMaxTime: slot_max_time,
        };
    }
});