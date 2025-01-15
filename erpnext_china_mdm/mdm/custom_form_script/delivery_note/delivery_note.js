frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
		if (!has_common(frappe.user_roles, ["Administrator", "System Manager"])) {
			// 删除时间轴信息
			let timeline_item = Array.from(document.getElementsByClassName('timeline-item'));
			timeline_item.forEach(item => {
				let parent = item.parentNode;
				if (parent) {
					parent.removeChild(item);
				}
			});

		}

		if (has_common(frappe.user_roles, ["HR User", "HR Manager"])) {
			// 销售团队、佣金相关字段默认隐藏，HR用户可见
			const hidden_fields = [
				"section_break1",
				"sales_team_section_break",
			];
			hidden_fields.forEach(field => {
				frm.set_df_property(field, 'hidden', 0);
			});
		}

		
		frappe.call({
			doc:frm.doc,
			method:"get_important_reminders",
			args:{},
			callback: function(res){
				if(res.message) {
					frm.dashboard.clear_comment()
					frm.set_intro(res.message)
				}
			}
		})

	},
});