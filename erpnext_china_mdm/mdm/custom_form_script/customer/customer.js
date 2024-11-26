frappe.ui.form.on('Customer', {
    refresh(frm){
        frm.set_query("lead_name", function(doc) {
            return {
                filters: [
                    ["Lead", "lead_owner", "=", frappe.user.name],
                ]
            };
        });
    }
});