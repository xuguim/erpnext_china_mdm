frappe.ui.form.on("Payment Entry", {
    
    mode_of_payment(frm) {
        frm.toggle_reqd('bank_account', ["微信","电汇","支付宝"].includes(frm.doc.mode_of_payment));
        if(frm.doc.bank_account) {
            frm.events.bank_account(frm)
        }
    },

    bank_account: function (frm) {
		const field = frm.doc.payment_type == "Pay" ? "paid_from" : "paid_to";
		if (frm.doc.bank_account && ["Pay", "Receive"].includes(frm.doc.payment_type)) {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_account.bank_account.get_bank_account_details",
				args: {
					bank_account: frm.doc.bank_account,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value(field, r.message.account);
						frm.set_value("bank", r.message.bank);
						frm.set_value("bank_account_no", r.message.bank_account_no);
					}
				},
			});
		}
	},
})