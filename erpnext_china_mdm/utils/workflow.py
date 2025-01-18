import frappe

@frappe.whitelist()
def get_workflow_html(name):
	# ignore workflow read permission
	return frappe.db.get_value('Workflow',name,'help_html')