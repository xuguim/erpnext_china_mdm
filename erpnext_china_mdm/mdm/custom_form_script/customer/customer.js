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
    }
});