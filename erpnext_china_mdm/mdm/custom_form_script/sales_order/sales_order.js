frappe.ui.form.on('Sales Order', {
    company: function (frm) {
        if (frm.doc.company == '临时') {
            frm.set_value('taxes_and_charges', null)
            frm.clear_table('taxes')
        } else {
            frm.call('get_p13').then((r)=>{
                const name = r.message.name;
                if (name) {
                    frm.set_value('taxes_and_charges', name)
                }
            });
        }
	},
    refresh(frm){
        if(!has_common(frappe.user_roles, ["Administrator", "System Manager","Accounts User","Accounts Manager"])){
			// 销售税费明细子表对除管理员和财务外的其他角色只读，明细中科目和成本中心也只读
			frm.set_df_property('taxes','read_only',1)
			frm.fields_dict["taxes"].grid.toggle_enable("account_head", 0)
			frm.fields_dict["taxes"].grid.toggle_enable("cost_center", 0)
			
		}

		if (has_common(frappe.user_roles, ["Administrator", "System Manager","HR User", "HR Manager"])) {
			// 销售团队、佣金相关字段默认隐藏，高权限用户可见
			frm.set_df_property('sales_team_section_break','hidden',0)
			frm.set_df_property('section_break1','hidden',0)
		}

		if (has_common(frappe.user_roles, ["Administrator", "System Manager"])) {
			// 销售价格只有管理员可编辑
			frm.fields_dict["items"].grid.toggle_enable("rate", 1)
			
		}

        if (frm.is_new()) {
            frm.set_df_property('transaction_date', 'hidden', 1)
            frm.set_df_property('scan_barcode', 'hidden', 1)
        }

		frm.toggle_display(
			"final_customer_name",
			frm.doc.final_customer_name && frm.doc.final_customer_name !== frm.doc.final_customer
		);

		setTimeout(() => {
            frm.fields_dict.items.grid.toggle_reqd('delivery_date',1)
        }, 100);

        if (
            frm.doc.docstatus == 1 
            && frappe.user.has_role('销售会计') 
            && frm.doc.per_delivered < 100
            && !frm.doc.skip_delivery_note
            && frm.doc.allow_delivery == 0
            && frm.doc.is_internal_customer == 0
        ){
            frm.add_custom_button(__('Allow Delivery'),function(){
                frm.trigger('mark_allow_delivery')
            },__('Action'))
        }

        if (
            (frm.doc.allow_delivery == 1 || frm.doc.grand_total == frm.doc.advance_paid) 
            && frm.doc.per_delivered < 100
        ) {
            let has_internal_so =
                frm.doc.items.some(
                    (item) => item.delivered_by_supplier === 1
                ) && !frm.doc.skip_delivery_note;
            if (has_internal_so) {
                frm.add_custom_button(
                    __("Inter Company Delivery Note"),
                    () => {
                        frm.trigger("make_delivery_note_based_on_delivery_date")
                    },
                    __("Create")
                );
            } else {
                // show origin button
            }
        } else {
            setTimeout(() => {
                frm.remove_custom_button(__('Delivery Note'),__('Create'))
            }, 100);
        }

        // recalc discount in case of remove items
        calc_discount(frm)

        $.each(frm.doc.items, function (j, item) {
            if(item.amount != item.custom_after_distinct__amount_request) {
                console.log(item.amount,item.custom_after_distinct__amount_request)
                let $els = $("div[data-fieldname='custom_after_distinct__amount_request']").find('.static-area')
                $els.eq(item.idx).addClass('text-danger bold');
            }
        });
    },

    mark_allow_delivery(frm) {
        frappe.call({
            method:"erpnext_china_mdm.mdm.custom_form_script.sales_order.sales_order.allow_delivery",
            args:{
                docname:frm.doc.name
            },
            callback:(res)=>{
                if(res.message) {
                    frm.reload_doc()
                }
            }
        })
    }
});

frappe.ui.form.on("Sales Order Item", {
    item_code:function (frm,cdt,cdn) {
        sync_item_amount_request(frm,cdt,cdn)
    },

    qty:function (frm,cdt,cdn) {
        sync_item_amount_request(frm,cdt,cdn)
    },

    custom_after_distinct__amount_request:function (frm,cdt,cdn) {
        setTimeout(() => {
            calc_discount(frm)
        }, 100);
    }
});

function sync_item_amount_request(frm,cdt,cdn) {
    var row = locals[cdt][cdn];
    if (row.rate * row.qty != row.custom_after_distinct__amount_request) {
        frappe.model.set_value(cdt, cdn, "custom_after_distinct__amount_request", row.rate * row.qty);
    } 
}

function calc_discount(frm) {
    if(frm.doc.docstatus == 0 && frm.doc.items.length > 0) {
        discount_amount = 0
        frm.doc.items.forEach(item=>{
            discount_amount += item.amount - item.custom_after_distinct__amount_request
        })
        if(flt(frm.doc.discount_amount,2) != flt(discount_amount,2)) {
            frm.set_value('discount_amount', discount_amount)
        }
    }
}