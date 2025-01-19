// Copyright (c) 2025, Digitwise Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Leads Summary"] = {
	"filters": [
		{
			label: "Timespan",
			fieldtype: "Select",
			fieldname: "timespan",
			options: [
				"Last Month",
				"Yesterday",
				"Today",
				"Last Quarter",
				"Last 6 months",
				"Last Year",
				"This Week",
				"This Month",
				"This Quarter",
				"This Year",
			],
		},
		{
			label: __("Chart Value"),
			fieldtype: "Select",
			fieldname: "chart_value",
			options: [
				"Qty",
				"Expenses",
				"Both"
			],
			default: "Both"
		},
		{
			label: __("More Details"),
			fieldtype: "Check",
			fieldname: "more_details",
			default: 0
		},
		
	]
};
