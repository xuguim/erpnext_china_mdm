import frappe
from frappe import _
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

def validate_shipper(doc, method=None):
	user = doc.owner
	employee = frappe.db.get_value("Employee", {"user_id": user},["name","department","reports_to"],as_dict=1)
	if not employee:
		if user == 'Administrator':
			if frappe.conf.developer_mode:
				# 开发环境管理员操作默认选择第一个员工
				employee_list = frappe.get_all('Employee',filters={'status':'Active'},fields=["name","department","reports_to"])
				if len(employee_list) > 0:
					employee = employee_list[0]
					frappe.msgprint('管理员操作默认选择第一个员工{}'.format(employee.name),alert=1)
				else:
					frappe.throw("系统中没有有效员工信息，无法自动分配单据")
			else:
				return
		else:
			frappe.throw("当前用户没有员工信息，请完善配置！")

	employee_list = frappe.get_all('Employee',filters={'status':'Active'},fields=['name','department','reports_to','user_id'])
	shipper_list = frappe.get_all('Shipper',filters={'parenttype':'Department','parentfield':'shipper'},fields=['employee','employee_name','is_default','parent as department'])
	department_list = frappe.get_all('Department',filters={'company':doc.company,'disabled':0},fields=['name','department_name','parent_department'])

	if not employee.reports_to:
		if employee.department:
			shipper = find_department_shipper(department,department_list,shipper_list)
		else:
			frappe.throw('员工未配置部门和上级主管，无法找到发货人，请联系管理员')
	else:
		department = [d.department for d in employee_list if d.name==employee.reports_to][0]
		if not department:
			frappe.throw('你的上级主管{}未配置部门，无法找到发货人，请联系管理员'.format(employee.reports_to))
		else:
			shipper = find_department_shipper(department,department_list,shipper_list)

	if shipper:
		doc.shipper = shipper
		doc.shipping_user = [d.user_id for d in employee_list if d.name==shipper][0]
		# assign_to_shipper(doc,doc.shipping_user)

		msg = f"""
			<h5>已设置发货人为{doc.shipper}</h5>
		"""
		frappe.msgprint(f"""<div>{msg}<div>""",alert=1)
	else:
		frappe.throw("未找到发货人")


def find_department_shipper(department,department_list,shipper_list):# -> Any | None:
	department_shippers = [s for s in shipper_list if s.department==department]
	if len(department_shippers) == 0 or not department_shippers[0]:
		parent_department_list = [d.parent_department for d in department_list if d.name==department]
		if len(parent_department_list) > 0:
			return find_department_shipper(parent_department_list[0],department_list,shipper_list)
		else:
			return
	else:
		default_shipper = [s.employee for s in department_shippers if s.is_default==1]
		if len(default_shipper) > 0:
			shipper = default_shipper[0]
		else:
			shipper = department_shippers[0]
		return shipper
	
def auto_make_sales_invoice(doc, method=None):
	if not doc.create_sales_invoice:
		return
	current_user = frappe.session.user
	frappe.set_user("Administrator")
	sales_invoice = make_sales_invoice(doc.name)
	sales_invoice.owner = doc.owner
	sales_invoice.save().submit()
	sales_invoice.add_comment("Comment", 
		_("Automatically Create {0}: {1} Base On {2}: {3}").format(
			_(sales_invoice.doctype),
			sales_invoice.name,
			_(doc.doctype),
			doc.name
		)
	)
	frappe.set_user(current_user)