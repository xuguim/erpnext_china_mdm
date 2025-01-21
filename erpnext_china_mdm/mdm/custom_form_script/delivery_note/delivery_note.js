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

		$('.grid-static-col').css({ "height": "auto", "display": "flex", "align-items": "center" })
		$('.row-check').css({ "height": "auto", "display": "flex", "align-items": "center", "justify-content": "center" })
		$('.row-index').css({ "height": "auto", "display": "flex", "align-items": "center", "justify-content": "center" })
		$('.btn-open-row').css({ "height": "auto", "display": "flex", "align-items": "center", "justify-content": "center" })
		$('.grid-static-col[data-fieldtype="Text Editor"]').css({ "align-items": "flex-start" })
		$('.grid-static-col[data-fieldtype="Check"]').css({ "justify-content": "center" })
		$('.grid-body .grid-static-col .static-area').css({	"white-space": "normal","word-break": "break-all","align-items": "center" });

		if(frm.doc.docstatus == 0 && in_list(['仓库审核','发货员确认出货'],frm.doc.workflow_state)) {
			frm.trigger('check_qty');
		}
	},

	check_qty(frm) {
		let raw_data = JSON.parse(frm.doc.raw_data);
		let diff_items = [];
		let delete_items = []
		raw_data.items.forEach(item => {
			diff_status = ''
			frm.doc.items.forEach(row => {
				if (item.so_detail == row.so_detail) {
					if(item.qty == row.qty) {
						diff_status = 'Matched';
					} else {
						diff_status = 'Unmatched';
						diff_item = row;
						diff_item.qty = item.qty - row.qty;
						diff_item.amount = diff_item.qty * item.rate;
						diff_items.push(diff_item);
					}
				}
			});
			if(!diff_status) {
				delete_items.push(item);
			}
		});
		if(delete_items?.length > 0 || diff_items?.length > 0) {
			let item_html = `<table class="text-center border w-100">
					<thead>
						<tr class="bg-light">
							<th class="p-2">${__('Item Code')}</th>
							<th class="p-2">${__('Item Name')}</th>
							<th class="p-2">${__('Qty')}</th>
							<th class="p-2">${__('UOM')}</th>
							<th class="p-2">${__('Rate')}</th>
							<th class="p-2">${__('Amount')}</th>
						</tr>
					</thead>
				<tbody>`;
			delete_items.forEach((item, index) => {
				item_html += `<tr>
					<td class="p-2">${item.item_code}</td>
					<td class="p-2">${item.item_name}</td>
					<td class="p-2 text-danger bold">${item.qty}</td>
					<td class="p-2">${item.uom}</td>
					<td class="p-2">${item.rate}</td>
					<td class="p-2">${item.amount}</td>
					</tr>`;
			});
			diff_items.forEach((item, index) => {
				item_html += `<tr>
					<td class="p-2">${item.item_code}</td>
					<td class="p-2">${item.item_name}</td>
					<td class="p-2 text-danger bold">${item.qty}</td>
					<td class="p-2">${item.uom}</td>
					<td class="p-2">${item.rate}</td>
					<td class="p-2">${item.amount}</td>
					</tr>`;
			});
			item_html += `</tbody></table>`;

			let msg = `
			<p>以下物料为销售提交的原始单据和当前单据的偏差，单据提交后将<b>自动创建新的差额销售出货单</b></p>
			${item_html}
			`

			frm.dashboard.clear_comment();
			frm.dashboard.add_comment(msg, "blue", true);
		}

	}
});