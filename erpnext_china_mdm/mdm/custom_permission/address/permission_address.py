import frappe
from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree
from erpnext_china_mdm.mdm.custom_permission.customer.permission_customer import get_customer_from_delivery_note

def get_descendants(name, nodes):
    descendants = []
    for node in nodes:
        if node['parent_warehouse'] == name:
            descendants.append(node)
            descendants.extend(get_descendants(node['name'], nodes))
    return descendants

def get_user_all_warehouses(users):
	user_warehouses = frappe.get_all("Warehouse User", filters={"warehouse_user": ["in", users]}, pluck='parent')
	warehouses = frappe.get_all("Warehouse", filters={
		"name": ["in", list(set(user_warehouses))]
	}, fields=["name", "parent_warehouse"])
	all_warehouses = frappe.get_all("Warehouse", fields=["name", "parent_warehouse"])
	finall_warehouses = []
	for w in warehouses:
		finall_warehouses += get_descendants(w['name'], all_warehouses) + [w]
	return finall_warehouses
	
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

def get_is_your_company_addresses():
	try:
		is_your_company_addresses = frappe.get_all('Address', filters={'is_your_company_address': 1}, pluck='name')
		return is_your_company_addresses
	except:
		return []

def get_addresses_from_delivery_notes(user):
	try:
		if 'Deliver User' in frappe.get_roles(user) or '仓库' in frappe.get_roles(user):
			dn_customers = get_customer_from_delivery_note(user)
			addresses = frappe.get_all('Dynamic Link', filters={
				'link_doctype': 'Customer', 
				'parenttype': 'Address',
				'link_name': ['in', dn_customers]},
				pluck='parent')
			is_your_company_addresses = frappe.get_all('Address', filters={'is_your_company_address': 1}, pluck='name')
			return list(set(addresses + is_your_company_addresses))
		return []
	except:
		return []

def has_query_permission(user):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','销售会计']]}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"tabAddress.`owner` in {users_str}"
		addresses_from_delivery_notes = []
		if 'Deliver User' in frappe.get_roles(user):
			addresses_from_delivery_notes = get_addresses_from_delivery_notes(user)
			addresses_str = str(tuple(addresses_from_delivery_notes)).replace(',)',')')
			conditions += f" or tabAddress.`name` in {addresses_str}"
		# # 有客户权限，则有详细地址权限
		# addresses = get_addresses_from_customers(user)
		# if len(addresses) > 0:
		# 	addresses_str = str(tuple(addresses)).replace(',)',')')
		# 	conditions += f" or tabAddress.`name` in {addresses_str}"
		
		is_your_company_addresses = get_is_your_company_addresses()
		if len(is_your_company_addresses) > 0:
			is_your_company_addresses_str = str(tuple(is_your_company_addresses)).replace(',)',')')
			conditions += f" or tabAddress.`name` in {is_your_company_addresses_str}"
	
	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','销售会计','销售支持']]}):
		# 如果角色包含管理员，则看到全量
		return True

	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		addresses_from_delivery_notes,is_your_company_addresses = []
		delivery_note_address_perm = False
		if '仓库' in frappe.get_roles(user):
			delivery_note_docs = frappe.get_all('Delivery Note', filters={"shipping_address_name": doc.name,'workflow_state':'仓库审核'}, pluck='name')
			delivery_note_warehouses = frappe.get_all("Delivery Note Item", filters={
						"parent": ["in", delivery_note_docs],
						"parenttype": "Delivery Note",
					}, pluck="warehouse")
			user_warehouses = get_user_all_warehouses([user])
			for delivery_note_warehouse in delivery_note_warehouses:
				if delivery_note_warehouse in list(set([w['name'] for w in user_warehouses])):
					delivery_note_address_perm = True
		# 有客户权限，则有详细地址权限
		# addresses = get_addresses_from_customers(user)

		if 'Delivery User' in frappe.get_roles(user):
			shippers = frappe.get_all('Delivery Note', filters={"shipping_address_name": doc.name,'workflow_state':['in',['发货员确认出货','Approved']]}, pluck='shipper')
			emp = frappe.get_all('Employee', filters={"user_id":user}, pluck='name')
			if 'HR-EMP-00828' in shippers or 'HR-EMP-02111' in shippers:
				shippers = ['HR-EMP-00828','HR-EMP-02111']+shippers
			if emp[0] in shippers:
				delivery_note_address_perm = True

		is_your_company_addresses = get_is_your_company_addresses()

		if doc.owner in users or doc.name in addresses_from_delivery_notes or doc.name in is_your_company_addresses or delivery_note_address_perm:
			return True
		else:
			return False