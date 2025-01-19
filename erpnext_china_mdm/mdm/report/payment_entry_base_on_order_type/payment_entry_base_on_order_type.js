// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Entry Base On Order Type"] = {
	"filters": [
		{
			fieldname: "charts_based_on",
			label: __("Charts Based On"),
			fieldtype: "Select",
			options: ["Order Type", "Item Group"],
			default: "Order Type"
		}
	]
};
