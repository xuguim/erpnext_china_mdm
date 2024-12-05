frappe.ui.form.on("Department", {
    refresh: function (frm) {
        frm.set_query("employee", "shipper", function (doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.employee_query",
				filters: {
					company: frm.doc.company,
				},
			};
		});
    }
});

frappe.ui.form.on("Shipper", {
    is_default: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		// 勾选默认发货员后其他发货员取消默认
		frm.doc.shipper.forEach(element => {
			if(element.name != row.name){
				frappe.model.set_value(element.doctype, element.name, "is_default", !row.is_default);
			}
		});
	},
	employee: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		// 新建第一个发货员时默认勾选
		if(row.employee && frm.doc.shipper?.length == 1) {
			frappe.model.set_value(row.doctype, row.name, "is_default", 1);
		}
	},
});