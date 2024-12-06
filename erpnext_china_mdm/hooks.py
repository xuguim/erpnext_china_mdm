app_name = "erpnext_china_mdm"
app_title = "ERPNext China MDM"
app_publisher = "Digitwise Ltd."
app_description = "Medical Device Manufacturers（中国本地化的ERPNext医疗器械制造业解决方案）"
app_email = "lingyu_li@foxmail.com"
app_license = "mit"
required_apps = ['saoxia/erpnext_china']

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_china/css/erpnext_china.css"
# app_include_js = "/assets/erpnext_china/js/erpnext_china.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_china/css/erpnext_china.css"
# web_include_js = "/assets/erpnext_china/js/erpnext_china.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpnext_china/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "erpnext_china.utils.jinja_methods",
#	"filters": "erpnext_china.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "erpnext_china.install.before_install"
# after_install = "erpnext_china.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "erpnext_china.uninstall.before_uninstall"
# after_uninstall = "erpnext_china.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "erpnext_china.utils.before_app_install"
# after_app_install = "erpnext_china.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "erpnext_china.utils.before_app_uninstall"
# after_app_uninstall = "erpnext_china.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_china.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"erpnext_china.tasks.all"
#	],
#	"daily": [
#		"erpnext_china.tasks.daily"
#	],
#	"hourly": [
#		"erpnext_china.tasks.hourly"
#	],
#	"weekly": [
#		"erpnext_china.tasks.weekly"
#	],
#	"monthly": [
#		"erpnext_china.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "erpnext_china.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "erpnext_china.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "erpnext_china.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["erpnext_china.utils.before_request"]
# after_request = ["erpnext_china.utils.after_request"]

# Job Events
# ----------
# before_job = ["erpnext_china.utils.before_job"]
# after_job = ["erpnext_china.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"erpnext_china.auth.validate"
# ]
# scheduler_events = {
# 	"cron": { 
#         "0 3 * * *": [
# 			"erpnext_china_mdm.mdm.doctype.apc.apc.update_apc",
# 		],   
# 	},
# }

override_doctype_class = {
    'Item':'erpnext_china_mdm.mdm.custom_form_script.item.item.CustomItem',
    'Customer': 'erpnext_china_mdm.mdm.custom_form_script.customer.customer.CustomCustomer',
    'Address': 'erpnext_china_mdm.mdm.custom_form_script.address.address.CustomAddress',
    #'Stock Entry':'erpnext_china_mdm.mdm.custom_form_script.stock_entry.CustomStockEntry',
    'Supplier': 'erpnext_china_mdm.mdm.custom_form_script.supplier.CustomSupplier',
    'Contact': 'erpnext_china_mdm.mdm.custom_form_script.contact.CustomContact',
    'Journal Entry': 'erpnext_china_mdm.mdm.custom_form_script.journal_entry.CustomJournalEntry'
}
override_whitelisted_methods = {
    "erpnext_china.utils.oauth2_logins.login_via_wecom": "erpnext_china_mdm.utils.oauth2_logins.login_via_wecom",
}
after_install = "erpnext_china_mdm.setup.after_install.operations.install_fixtures.install"

doctype_js = {
    'Address': 'mdm/custom_form_script/address/address.js',
    'Customer': 'mdm/custom_form_script/customer/customer.js',
    'Item': 'mdm/custom_form_script/item/item.js',
	'Sales Order': 'mdm/custom_form_script/sales_order/sales_order.js',
	'Delivery Note': 'mdm/custom_form_script/delivery_note/delivery_note.js',
	'Department': 'mdm/custom_form_script/department/department.js',
}

doc_events = {
	"Sales Order": {
		"validate": "erpnext_china_mdm.mdm.custom_form_script.sales_order.sales_order.validate_sales_team",
	},
	"Delivery Note": {
		"validate": "erpnext_china_mdm.mdm.custom_form_script.delivery_note.delivery_note.validate_shipper",
	}
}

scheduler_events = {
	"cron": { 
        "0 1 * * *": [
			"erpnext_china_mdm.mdm.custom_form_script.scheduler_events.sales_person.auto_generate_sales_person",
		],   
        "0 */1 * * *": [
            "erpnext_china_mdm.mdm.custom_form_script.wecom.send_modified_checkin_to_wecom"
        ],
	},
}


permission_query_conditions = {
    'Customer': "erpnext_china_mdm.mdm.custom_permission.customer.permission_customer.has_query_permission",
    "Lead": "erpnext_china_mdm.mdm.custom_permission.lead.permission_lead.has_query_permission",
    "Quotation": "erpnext_china_mdm.mdm.custom_permission.quotation.permission_quotation.has_query_permission",
    "Opportunity": "erpnext_china_mdm.mdm.custom_permission.opportunity.permission_opportunity.has_query_permission",
    "Sales Order": "erpnext_china_mdm.mdm.custom_permission.sales_order.permission_sales_order.has_query_permission", 
    "Item": "erpnext_china_mdm.mdm.custom_permission.item.permission_item.has_query_permission",
    "Item Group": "erpnext_china_mdm.mdm.custom_permission.item_group.permission_item_group.has_query_permission",
    "Stock Entry": "erpnext_china_mdm.mdm.custom_permission.stock_entry.permission_stock_entry.has_query_permission",
    "Warehouse": "erpnext_china_mdm.mdm.custom_permission.warehouse.permission_warehouse.has_query_permission",
}

has_permission = {
    "Customer": "erpnext_china_mdm.mdm.custom_permission.customer.permission_customer.has_permission",
    "Lead": "erpnext_china_mdm.mdm.custom_permission.lead.permission_lead.has_permission",
    "Quotation": "erpnext_china_mdm.mdm.custom_permission.quotation.permission_quotation.has_permission",
    "Opportunity": "erpnext_china_mdm.mdm.custom_permission.opportunity.permission_opportunity.has_permission",
	"Sales Order": "erpnext_china_mdm.mdm.custom_permission.sales_order.permission_sales_order.has_permission", 
    "Item": "erpnext_china_mdm.mdm.custom_permission.item.permission_item.has_permission",
    "Item Group": "erpnext_china_mdm.mdm.custom_permission.item_group.permission_item_group.has_permission",
    "Warehouse": "erpnext_china_mdm.mdm.custom_permission.warehouse.permission_warehouse.has_permission",
}