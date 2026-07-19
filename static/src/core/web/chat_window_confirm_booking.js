/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

// Listen globally for clicks on our custom payment button inside the chatter log
document.addEventListener("click", async (event) => {
    const button = event.target.closest(".js_confirm_booking_btn");
    if (!button) return;

    event.preventDefault();
    
    // Extract the record ID from the HTML data attribute we set earlier
    const recordId = button.dataset.id;
    if (!recordId) return;

    // Optional: Disable button visually during processing to avoid double-clicks
    button.disabled = true;
    button.innerText = "Verifying...";

    try {
        // Send background JSON-RPC call to our new controller route
        const result = await rpc(`/hbn/appointment/confirm/{recordId}`);

        if (result.status === "success") {
            // Trigger Odoo's internal messaging bus system to fetch updates 
            // for the record the user is currently staring at.
            // This pulls field updates and refreshes the chatter box seamlessly in place.
            window.location.reload(); 
            // Note: If you have access to the main Form View controller instance here,
            // you can trigger: env.services.action.doAction({ type: "ir.actions.client", tag: "reload" });
        } else {
            alert("Error: " + result.message);
            button.disabled = false;
            button.innerText = "Verify Payment Slip";
        }
    } catch (error) {
        console.error("Payment verification failed:", error);
        button.disabled = false;
        button.innerText = "Verify Payment Slip";
    }
});
