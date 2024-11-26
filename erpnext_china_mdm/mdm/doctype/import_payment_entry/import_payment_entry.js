// Copyright (c) 2024, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Import Payment Entry", {
    // bank(frm){
    //     frm.call('get_bank_account').then((r)=>{
    //         const account = r.message.account;
    //         console.log(account)
    //         if (account) {
    //             frm.doc.bank_account = account;
    //             frm.refresh_field('bank_account');
    //         }
    //     });
    // },
	refresh(frm) {
        frm.add_custom_button(__('开始导入'), () => {
            frm.call('import_payment_entry').then((r)=>{

            })
        });
        frm.set_query("bank_account", function(doc) {
            return {
                filters: [
                    ["Bank Account", "is_company_account", "=", 1],
                    ["Bank Account", "company", "=", doc.company],
                    // ["Bank Account", "bank", "=", doc.bank]
                ]
            };
        });
        frm.call('get_temporary_customer').then((r)=>{
            const customer = r.message.customer;
            if (customer) {
                frm.doc.temporary_customer = customer;
                frm.refresh_field('temporary_customer');
            }
        })
	},
});
