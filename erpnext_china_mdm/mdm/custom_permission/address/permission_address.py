import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree

def get_addresses_from_customers(user):
	try:
		if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['销售']]}):
			customers = frappe.get_list('Customer', pluck='name')
			addresses = frappe.get_all('Dynamic Link', filters={
				'link_doctype': 'Customer', 
				'parenttype': 'Address',
				'link_name': ['in', customers]},
				pluck='parent')
			is_your_company_addresses = frappe.get_all('Address', filters={'is_your_company_address': 1}, pluck='name')
			return list(set(addresses + is_your_company_addresses))
		return []
	except:
		return []

def has_query_permission(user):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','销售会计','销售支持']]}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"tabAddress.`owner` in {users_str}"

		# # 有客户权限，则有详细地址权限
		# addresses = get_addresses_from_customers(user)
		# if len(addresses) > 0:
		# 	addresses_str = str(tuple(addresses)).replace(',)',')')
		# 	conditions += f" or tabAddress.`name` in {addresses_str}"

	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','销售会计','销售支持']]}):
		# 如果角色包含管理员，则看到全量
		return True
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)

		# 有客户权限，则有详细地址权限
		# addresses = get_addresses_from_customers(user)

		if doc.owner in users or doc.name:
			return True
		else:
			return False