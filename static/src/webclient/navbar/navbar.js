/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { EnterpriseNavBar } from "@web_enterprise/webclient/navbar/navbar";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useState, useEffect, useRef } from "@odoo/owl";

patch(EnterpriseNavBar.prototype, {
    setup() {
        super.setup();
        if(!user.isAdmin && user.hasGroup('hair_by_ning.appointment_user')){
            this.menu_toggle = false;
        } else {
            this.menu_toggle = true;
        }
    },
})
