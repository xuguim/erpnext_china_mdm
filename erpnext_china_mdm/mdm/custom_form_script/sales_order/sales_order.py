import frappe

def validate_sales_team(doc,method=None):
	if doc.doctype == 'Sales Order' and not doc.sales_team:
		user = frappe.session.user

		employee = frappe.db.get_value('Employee',{'user_id':user})


		if not employee:
			if user == 'Administrator':
				# 管理员操作默认选择第一个员工
				employee_list = frappe.get_all('Employee',pluck='name')
				if len(employee_list) > 0:
					employee = employee_list[0]
					frappe.msgprint('管理员操作默认选择第一个员工',alert=1)
			else:
				frappe.throw("当前用户没有员工信息，请完善配置！")
		frappe.log({'employee':employee})
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
			frappe.log({'sales_team':sales_team,'doc':doc.sales_team})