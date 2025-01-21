frappe.ui.form.on('Customer', {
    refresh(frm){
        frm.set_query("lead_name", function(doc) {
            return {
                filters: [
                    ["Lead", "lead_owner", "=", frappe.user.name],
                ]
            };
        });

        if (!frm.is_new()) {
            frm.add_custom_button(
                __("领取累计满赠优惠券"),
                () => frm.events.make_coupon_code(frm),
            );
            if([frm.doc.owner, frm.doc.custom_customer_owner_user, 'Administrator'].includes(frappe.session.user)) {
                frm.add_custom_button(
                    __("客户转移"),
                    () => frm.events.transfer_to_user(frm),
                    __("Actions")
                );
            }
        }
    },

    get_discount_by_accumulated_qty_of_multiple_so(frm, item) {
        
        frappe.call("erpnext_china_mdm.mdm.custom_form_script.sales_order.sales_order.get_discount_by_accumulated_qty_of_multiple_so", 
            {"customer": frm.doc.name, "customer_name": frm.doc.customer_name, "item": item}
        ).then(r=>{
            if (r.message && r.message.coupon_code) {
                frappe.msgprint(`已领优惠券: ${r.message.coupon_code}`);
            } else {
                frappe.msgprint("无可用优惠");
            }
        })
    },

    set_customer_owner(frm, employee) {
        frappe.call("erpnext_china_mdm.mdm.custom_form_script.customer.customer.transfer_to_user", 
            {"employee": employee, "doc": frm.doc.name}).then(r=>{
                const msg = `客户及关联线索已转移给:  ${r.message.employee_name} 请刷新页面！`
                frappe.msgprint(msg)
        })
    },

    make_coupon_code(frm) {
        const dialog = new frappe.ui.Dialog({
			title: __("领取累计满赠优惠券"),
			size: "extra-small",
			fields: [
                {
					fieldname: "item",
					fieldtype: "Link",
					label: __("Item"),
					options: "Item",
                    reqd: 1,
                    get_query: ()=> {
                        return {
                            filters: [
                                ["disabled", "=", 0],
                                ["has_variants", "=", 0],
                                ["is_sales_item", "=", 1],
                                ["item_group", "descendants of (inclusive)", "成品"]
                            ]
                        };
                    }
				}
			],
            primary_action_label: __("领取"),
			primary_action: () => {
                const item = dialog.get_value("item");
                frm.events.get_discount_by_accumulated_qty_of_multiple_so(frm, item);
                dialog.hide();
			},
        });
		dialog.show();
    },
    transfer_to_user(frm) {
        const dialog = new frappe.ui.Dialog({
			title: __("选择您要将此客户转移给的员工，注意：客户关联的线索将同步转移！"),
			size: "extra-small",
			fields: [
                {
					fieldname: "employee",
					fieldtype: "Link",
					label: __("Employee"),
					options: "Employee",
                    reqd: 1,
                    get_query: ()=> {
                        return {
                            filters: [
                                ["status", "=", "Active"]
                            ]
                        };
                    }
				}
			],
            primary_action_label: __("确认"),
			primary_action: () => {
                const employee = dialog.get_value("employee");
                frm.events.set_customer_owner(frm, employee);
                dialog.hide();
			},
        });
		dialog.show();
    }
});