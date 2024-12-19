import frappe

from erpnext_china.hrms_china.custom_form_script.employee.employee import get_employee_tree


def get_item_group_list(parent):
    def get_subordinates(parent):
        subordinates = []

        filters = {'parent_item_group': parent}
        item_groups = frappe.get_all('Item Group',filters=filters,pluck='item_group_name')

        if item_groups:
            for i in item_groups:
                subordinates.append(i)
                subordinates += get_subordinates(i)
        return subordinates
    subordinates = get_subordinates(parent)
    subordinates.append(parent)
    return subordinates



def has_query_permission(user):

	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager','仓库管理']]}):
		# 如果角色包含管理员，则看到全量
		conditions = ''
	elif frappe.db.get_value('Has Role',{'parent':user,'role':['in',['仓库']]}):
		'''
		如果权限是仓库，则可以看到特定仓库的物料
		'''
		# 用户和用户下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')

		sql_default_warehouse_user_stock = f'''select parent from `tabWarehouse User`
											where warehouse_user in {users_str}'''
		conditions = f'''
			name in (
						select parent as item_name from `tabItem Default` 
						where default_warehouse in (
														select distinct parent from `tabWarehouse User` 
														where warehouse_user in {users_str}
													)
						union (
								select distinct item_code as item_name from `tabStock Ledger Entry`
								where warehouse in (
														select distinct parent from `tabWarehouse User` 
														where warehouse_user in {users_str}
													)
								and docstatus < 2
						)
						union (
								select name as item_name from `tabItem`
								where owner in {users_str}
						)
		)
		'''
	elif frappe.db.get_value('Has Role',{'parent':user,'role':['in',['销售','销售会计','销售支持','网络推广','网络推广管理']]}):
		# 销售和网推可以看到所有成品
		item_groups = get_item_group_list('成品')
		item_groups_str = str(tuple(item_groups)).replace(',)',')')
		conditions = f"(item_group in {item_groups_str}) and (disabled = 0) and (has_variants = 0)" 
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		users_str = str(tuple(users)).replace(',)',')')
		conditions = f"owner in {users_str}" 
	return conditions

def has_permission(doc, user, permission_type=None):
	if frappe.db.get_value('Has Role',{'parent':user,'role':['in',['System Manager','仓库','仓库管理']]}):
		# 如果角色包含管理员，则看到全量
		return True
	elif frappe.db.get_value('Has Role',{'parent':user,'role':['in',['销售','销售会计','销售支持','网络推广','网络推广管理']]}):
		# 销售可以看到所有成品组
		item_groups = get_item_group_list('成品')
		if doc.item_group in item_groups:
			return True
		else:
			return False
	else:
		# 其他情况则只能看到自己,上级可以看到下级
		users = get_employee_tree(parent=user)
		users.append(user)
		if doc.owner in users:
			return True
		else:
			return False