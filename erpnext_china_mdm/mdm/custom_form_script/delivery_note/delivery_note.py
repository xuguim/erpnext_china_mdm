import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote, make_sales_invoice


class CustomDeliveryNote(DeliveryNote):
	def before_validate(self):
		self.sales_order = self.validate_multi_so()
		frappe.log(self.sales_order)
		self.validate_discount_amount()

	def validate_discount_amount(self):
		self.validate_last_dn()
		[so_total,so_discount_amount] = frappe.db.get_value('Sales Order',self.sales_order,['total','discount_amount'])
		# clear discount amount for zero total sales order
		if so_total == 0:
			frappe.log("so_total is zero")
			self.additional_discount_percentage = 0
			self.discount_amount = 0
			return
		if not self.last_dn:
			# calculate discount amount base on per_delivered
			per_delivered = self.total / so_total
			self.additional_discount_percentage = 0
			self.discount_amount = flt(so_discount_amount * per_delivered,self.precision('discount_amount'))
		else:
			# calculate discount amount base on balance, adjust the precision error to grand total
			submitted_dn = frappe.get_all('Delivery Note',
				filters={
					"name": ["in", self.dn_names],
					"docstatus": 1
				},
				fields=['total','grand_total','discount_amount'],
			)
			submitted_dn_grand_total = sum([dn.grand_total for dn in submitted_dn])
			submitted_dn_total = sum([dn.total for dn in submitted_dn])

			self.additional_discount_percentage = 0
			self.discount_amount = flt(submitted_dn_grand_total + so_discount_amount - submitted_dn_total,self.precision('discount_amount'))
		

	def validate_last_dn(self):
		self.last_dn = True
		so_items = frappe.get_all("Sales Order Item", 
			filters={"parent": self.sales_order}, 
			fields=["name", "stock_qty","rate","amount"]
		)
		submitted_dn_items = frappe.get_all("Delivery Note Item", 
			filters={"against_sales_order": self.sales_order,"docstatus":1}, 
			fields=["name","parent","so_detail", "stock_qty","rate","amount"]
		)
		self.dn_names = [d.parent for d in submitted_dn_items]
		for so_item in so_items:
			submitted_dn_qty = sum([dni.stock_qty for dni in submitted_dn_items if dni.so_detail == so_item.name])
			# stock_qty maybe not correct now, use qty * conversion_factor
			current_qty = sum([dni.qty * dni.conversion_factor for dni in self.items if dni.so_detail == so_item.name])
			if so_item.stock_qty > submitted_dn_qty + current_qty:
				self.last_dn = False
				return

	def validate_multi_so(self):
		sales_orders = list(set([d.against_sales_order for d in self.items]))
		if not sales_orders:
			# Ignore Delivery Note Without Linked Sales Order
			return False
		if len(sales_orders) > 1:
			msg = f"""<h5>{_("Linking To Multiple Sales Order Is Not Allowed")}<h5>"""
			for sales_order in sales_orders:
				msg += f"""
						<div><a href="/app/sales-order/{sales_order}" target="_blank">{sales_order}</a></div>
					"""
			frappe.throw(msg)
		return sales_orders[0]


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