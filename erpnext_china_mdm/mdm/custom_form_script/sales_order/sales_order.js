frappe.ui.form.on('Sales Order', {
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

        if (has_common(frappe.user_roles, ["销售会计"])) {
            // 地址及联系方式对销售会计隐藏
            frm.set_df_property('col_break46', 'hidden', 1)
        }

		frm.toggle_display(
			"final_customer_name",
			frm.doc.final_customer_name && frm.doc.final_customer_name !== frm.doc.final_customer
		);

		setTimeout(() => {
            frm.fields_dict.items.grid.toggle_reqd('delivery_date',1)
        }, 100);
    },
});