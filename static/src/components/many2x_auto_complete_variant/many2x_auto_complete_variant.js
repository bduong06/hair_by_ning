import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";

patch(Many2XAutocomplete.prototype, {

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        let newOptions = [];
        options.forEach((option) => {
            let newOption = option;
            newOption.label = option.label.replace(/.*\(|\).*/g, '');
            if(option.displayName){
                newOption.displayName = option.displayName.replace(/.*\(|\).*/g, '');
            }
            newOptions.push(newOption);
        })
        return newOptions;
    }
});
