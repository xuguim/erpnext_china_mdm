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
            && frm.doc.grand_total == frm.doc.advance_paid
        ){
            frm.add_custom_button(__('Allow Delivery'),function(){
                frm.trigger('mark_allow_delivery')
            },__('Action'))
        }
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