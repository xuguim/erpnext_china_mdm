// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Item Price Summary"] = {
	"filters": [
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "MultiSelectList",
			options: "Item Group",
			get_data: function (txt) {
				return new Promise((resolve) => {
					frappe.call({
						method: "erpnext_china_mdm.mdm.report.item_price_summary.item_price_summary.get_finished_good_item_group_with_children",
						args: {},
						callback: function(r) {
							const validItemGroups = r.message;
							frappe.db.get_link_options("Item Group", txt, {
								is_group:0
							}).then(filteredOptions => {
								const filteredAndValidOptions = filteredOptions.filter(option => validItemGroups.includes(option.value));
								resolve(filteredAndValidOptions);
							}).catch(error => {
								resolve([]);
							});
						}
					});
				});
			},
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "consolidate_items",
			label: __("Consolidate Items"),
			fieldtype: "Check",
			default: 1,
			depends_on: "eval: !doc.item_code",
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		consolidate_items = frappe.query_report.get_filter_value('consolidate_items');
		if(!consolidate_items) {
			return value
		} else {
			if (in_list(['min_qty','rate','standard_selling_rate','uom'],column.id) && data && !data['item_name']) {
				value = `<span class="hidden">` + value +`</span>`;
			} 
			else if(column.id =='stock_available' && data && !data['item_name']) {
				if(data['stock_available'] == 0) {
					value = `<span class="hidden">` + value +`</span>`;
				} else {
					value = `<span class="bold">` + value +`</span>`;
				}
				
			}
			else if (column.id == 'item_code' && data ) {
				if(data['item_name']) {
					value = `<span class="hidden">` + value +`</span>`;
				} else {
					value = `<span class="bold">` + value +`</span>`;
				}
				
			}
			return value
		}
	}
};
