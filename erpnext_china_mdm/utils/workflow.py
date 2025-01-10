import frappe

@frappe.whitelist()
def add_reason(doctype,docname,reason,user,user_name):
	comment = frappe.new_doc("Comment")
	comment.update(
		{
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": docname,
			"comment_email": user,
			"comment_by": user_name,
			"content": reason,
		}
	)
	frappe.log(comment.as_dict())
	comment.insert(ignore_permissions=True)