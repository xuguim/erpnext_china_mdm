import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree

def get_customers_from_sales_orders(user):
	try:
		customers = []
		if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['销售']]}):
			customers = frappe.get_list('Sales Order', pluck='customer')
		return customers
	except:
		return []
	
def get_customer_from_delivery_note(user):
	if not user:
		user = frappe.session.user
	query = f"""
		select
			distinct dn.customer
		from
			`tabDelivery Note` dn
		left join
			`tabDelivery Note Item` dni on dni.parent = dn.name
		join
			(
				select
					wh.name as warehouse_name
				from
					`tabWarehouse` wh, `tabWarehouse User` whu
				where
					wh.name = whu.parent
					and whu.warehouse_user = '{user}'
			) warehouse on warehouse.warehouse_name = dni.warehouse
	"""
	try:
		res = frappe.db.sql(query,as_dict=1)
		return [d.customer for d in res]
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
		conditions = f"tabCustomer.`owner` in {users_str}"

		# 如果当前用户是客户关联线索的负责人，也可以看到
		# 这里要找 已转化的线索
		leads = frappe.db.get_all("Lead", filters=[["lead_owner", '=', user]], pluck='name')
		if len(leads) > 0:
			leads_str = str(tuple(leads)).replace(',)',')')
			conditions += f" or tabCustomer.`lead_name` in {leads_str}"
		
		# 当前user能看到的销售订单，则能看到销售订单对应的客户
		customers = get_customers_from_sales_orders(user)
		if len(customers) > 0:
			customers_str = str(tuple(customers)).replace(',)',')')
			conditions += f" or tabCustomer.`name` in {customers_str}" 
		if 'Stock User' in frappe.get_roles(user):
			dn_customers = get_customer_from_delivery_note(user)
			dn_customers_str = str(tuple(dn_customers)).replace(',)',')')
			conditions += f" or tabCustomer.`name` in {dn_customers_str}" 
	
	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role': ['in',['System Manager','销售会计','销售支持']]}):
		# 如果角色包含管理员，则看到全量
		return True
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)

		# 如果当前客户的线索的线索负责人是当前user，也可以看到
		lead_owner = frappe.db.get_value("Lead", doc.lead_name, fieldname="lead_owner")

		# 当前user销售订单权限，则能看到销售订单对应的客户
		customers = get_customers_from_sales_orders(user)
		dn_customers = get_customer_from_delivery_note(user)

		if doc.owner in users or lead_owner == user or doc.name in customers or doc.name in dn_customers:
			return True
		else:
			return False