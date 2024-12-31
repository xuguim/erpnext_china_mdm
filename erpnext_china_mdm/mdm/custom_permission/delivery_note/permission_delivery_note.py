import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree

def get_delivery_notes_by_warehouse_user(user):
	try:
		warehouses = frappe.get_all("Warehouse User", filters={"warehouse_user": user}, pluck='parent')
		return frappe.get_all("Delivery Note Item", filters={
			"warehouse": ["in", warehouses],
			"parenttype": "Delivery Note",
		}, pluck="parent")
	except:
		return []


def has_query_permission(user):

	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager', '出货管理']]}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	else:
		# 上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"`tabDelivery Note`.`owner` in {users_str}"
		
		# 发货员
		conditions += f" or `tabDelivery Note`.`shipping_user` = '{user}'"
		
		# 仓库看到和自己管理的仓库相关的
		if '仓库' in frappe.get_roles(user):
			delivery_notes = get_delivery_notes_by_warehouse_user(user)
			if len(delivery_notes) > 0:
				delivery_notes_str = str(tuple(delivery_notes)).replace(',)',')')
				conditions += f" or `tabDelivery Note`.`name` in {delivery_notes_str}"
	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager','出货管理']]}):
		# 如果角色包含管理员，则看到全量
		return True
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		
		delivery_notes = []
		if '仓库' in frappe.get_roles(user):
			delivery_notes = get_delivery_notes_by_warehouse_user(user)
			
		if doc.owner in users or doc.shipping_user == user or doc.name in delivery_notes:
			return True
		else:
			return False