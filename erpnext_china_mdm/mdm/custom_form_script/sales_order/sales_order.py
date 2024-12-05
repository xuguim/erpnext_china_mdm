import frappe

def validate_sales_team(doc,method=None):
	user = frappe.session.user
	if user == 'Administrator':
		return
	if doc.doctype == 'Sales Order' and not doc.sales_team:
		employee = frappe.db.get_value('Employee',{'user_id':user})
		if not employee:
			if user == 'Administrator':
				return
			else:
				frappe.throw("当前用户没有员工信息，请完善配置！")
		sales_person = frappe.db.get_value('Sales Person',{'employee':employee,})

		if not sales_person:
			frappe.throw("当前用户没有销售团队配置，请联系管理员！")
		else:
			sales_person = frappe.get_doc('Sales Person',sales_person)
			sales_team = {
				'parenttype':'Sales Order',
				'parentfield':'sales_team',
				'parent':doc.name,
				'sales_person':sales_person.name,
				'allocated_percentage':100,
				'department':sales_person.department,
				'reports_to':sales_person.reports_to
			}
			doc.append('sales_team',sales_team)