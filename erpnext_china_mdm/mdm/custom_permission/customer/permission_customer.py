import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree

def has_query_permission(user):
	if frappe.db.get_value('Has Role',{'parent':user,'role':'System Manager'}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		
		# 如果当前用户是客户关联线索的负责人，也可以看到
		# 这里要找 已转化的线索
		leads = frappe.db.get_all("Lead", filters=[["lead_owner", '=', user]], pluck='name')
		leads_str = str(tuple(leads)).replace(',)',')')
		
        # 如果客户是 内部客户，也可以看到
		internal_customers = frappe.db.get_all("Customer", filters={"is_internal_customer": 1}, pluck='name')
		internal_customers_str = str(tuple(internal_customers)).replace(',)',')')
		conditions = f"owner in {users_str} or lead_name in {leads_str} or name in {internal_customers_str}" 
	return conditions

def has_permission(doc, ptype, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager']]}):
		# 如果角色包含管理员，则看到全量
		return True
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)

		# 如果当前客户的线索的线索负责人是当前user，也可以看到
		lead_owner = frappe.db.get_value("Lead", doc.lead_name, fieldname="lead_owner")

        # 如果当前客户是内部客户，并且当前用户包含销售权限，则给只读权限
		if doc.is_internal_customer and ptype == 'read' and frappe.db.get_value('Has Role',{'parent':user,'role':['in',['销售']]}):
			return True

		if doc.owner in users or lead_owner == user:
			return True
		else:
			return False