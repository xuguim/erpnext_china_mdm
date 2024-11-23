// Copyright (c) 2024, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Import Payment Entry", {
	refresh(frm) {
        frm.add_custom_button(__('开始导入'), () => {
            frm.call('import_payment_entry').then((r)=>{

            })
        });
        frm.set_query("bank_account", function(doc) {
            return {
                filters: [
                    ["Bank Account", "is_company_account", "=", 1],
                    ["Bank Account", "company", "=", doc.company]
                ]
            };
        });
	},
});
