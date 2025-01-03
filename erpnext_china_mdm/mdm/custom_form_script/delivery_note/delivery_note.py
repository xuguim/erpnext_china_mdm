import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote, make_sales_invoice


class CustomDeliveryNote(DeliveryNote):
	def before_validate(self):
		self.sales_order = self.validate_multi_so()
		frappe.log(self.sales_order)
		self.validate_discount_amount()
		self.validate_advance_paid_of_so()

	def before_save(self):
		if self.is_new():
			self.set_employee_and_department()
			self.set_final_customer()

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

	def validate_advance_paid_of_so(self):
		sales_order = self.sales_order
		# 找到原始销售订单
		original_sales_order = frappe.db.get_value("Sales Order", filters={"name": sales_order}, fieldname="custom_original_sales_order")
		if original_sales_order:
			advance_paid = frappe.db.get_value("Sales Order", filters={"name": original_sales_order}, fieldname="advance_paid")
			frappe.log(f"{self.grand_total}, {advance_paid}")
			if self.grand_total != advance_paid:
				frappe.throw("收款后才能发货")
	
	def set_employee_and_department(self):
		employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user}, ["name", "department"], as_dict=1)
		if employee:
			self.custom_employee = employee.name
			self.custom_department = employee.department

	def set_final_customer(self):
		if self.sales_order:
			final_customer = frappe.db.get_value("Sales Order", filters={"name": self.sales_order}, fieldname="final_customer")
			self.custom_final_customer = final_customer

def validate_shipper(doc, method=None):
	user = doc.owner
	employee = frappe.db.get_value("Employee", {"user_id": user},["name","employee_name","department","reports_to","company"],as_dict=1)

	# 获取发货员工号
	shipper = frappe.db.get_value('Delivery Note Settings for Shipping Employee', employee.name,'shipping_employee')
	level = 0
	employee_reports_to = frappe.db.get_value('Employee',employee.name,'reports_to')
	while shipper == None and level < 5:
		level = level+1
		if employee_reports_to:
			shipper = frappe.db.get_value('Delivery Note Settings for Shipping Employee',employee_reports_to,'shipping_employee')
			employee_reports_to = frappe.db.get_value('Employee',employee_reports_to,'reports_to')
	
	# 发货单读取仓库，如果仓库的库管中，包含赵陪陪，发货人直接指定成王秋侠
	warehouses = [item.warehouse for item in doc.items]
	warehouse_employees = frappe.get_all("Warehouse User", filters={"parent": ["in", warehouses]}, pluck='warehouse_employee')
	if "HR-EMP-02708" in warehouse_employees:
		shipper = "HR-EMP-00828"
	
	if shipper:
		doc.shipper = shipper
		doc.shipping_user = frappe.db.get_value('Employee',shipper,'user_id')
		# assign_to_shipper(doc,doc.shipping_user)

		msg = f"""
			<h5>已设置发货人为{doc.shipper}</h5>
		"""
		frappe.msgprint(f"""<div>{msg}<div>""",alert=1)
	else:
		frappe.throw("未找到发货人")

	
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