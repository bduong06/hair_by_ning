import { _t } from "@web/core/l10n/translation";
import {GanttController} from "@web_gantt/gantt_controller";
import { patch } from "@web/core/utils/patch";

patch(GanttController.prototype, {
    setup(){
        super.setup(...arguments);
        if(this.props.context === undefined){
            this.props.context = {};
        }
        this.props.context.no_mail_to_attendees = true;
    },
    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props FormViewDialog props
     * @param {Record<string, any>} [options={}]
     */
    openDialog(props, options = {}) {
        const mcontext = this.actionService.currentController.props.context;
        if(props.context === undefined){
            props.context = {};
        }
        if(mcontext.booked_resource !== undefined){
            props.context.booked_resource = this.actionService.currentController.props.context.booked_resource;

        }
        super.openDialog(props, options);
    },
});