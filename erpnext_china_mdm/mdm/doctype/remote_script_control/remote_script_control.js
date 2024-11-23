// Copyright (c) 2024, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Remote Script Control", {
	refresh(frm) {
        frm.add_custom_button(__('执行'), () => {
            frm.call('process').then((r)=>{

            })
        });
	},
});
