// Copyright (c) 2024, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Shipper Config for Departments"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_default("company"),
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.id == 'employee_name' && data) {
			if (!data['employee_name']) {
				value = `<span class="text-light">` + __('Not Set') + `</span>`;
			} else {
				// highlight default shipper
				let names = value.split(',');
				value = names.map(name => {
					if (name === data['default_shipper']) {
						return `<span style="color: blue;font-weight:bold;">${name}</span>`;
					} else {
						return name;
					}
				}).join(', ');
			}
		};
		return value
	},
};
