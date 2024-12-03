import frappe

def auto_generate_sales_person():
	roles = ['销售']
	sales_users = frappe.get_all('Has Role',filters={'role':['in', roles]},pluck='parent')
	employees = frappe.get_all('Employee',filters={'user_id':['in', sales_users],'status':'Active'},pluck='name')
	for employee in employees:
		if not frappe.db.exists("Sales Person", {'employee': employee}):
			root_node = frappe.get_all('Sales Person',filters={'is_group':1,'enabled':1},order_by='creation',pluck='name')
			if len(root_node) == 0:
				frappe.log_error("销售团队根节点不存在，未完成销售人员自动创建")
				return
		
			doc = frappe.new_doc("Sales Person")
			doc.update({
				'sales_person_name':employee,
				'parent_sales_person': root_node[0],
				'employee': employee, 
				'sales_team': None
			})
			doc.insert().save()