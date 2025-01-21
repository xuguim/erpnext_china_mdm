import frappe
import json
from frappe import _
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote, make_sales_invoice


class CustomDeliveryNote(DeliveryNote):
	def before_validate(self):
		self.sales_order = self.validate_multi_so()
		self.validate_advance_paid_of_so()

	def before_save(self):
		if self.is_new():
			self.set_employee_and_department()
			self.set_final_customer()
			self.set_freight()
			self.set_original_sales_order()
		self.validate_discount_amount()
		self.validate_warehouse()

	def validate_discount_amount(self):
		self.validate_last_dn()
		[so_total,so_discount_amount] = frappe.db.get_value('Sales Order',self.sales_order,['total','discount_amount'])
		# clear discount amount for zero total sales order
		if so_total == 0:
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
		if sales_order:
			original_sales_order = frappe.db.get_value("Sales Order", filters={"name": sales_order}, fieldname="custom_original_sales_order")
			if not original_sales_order:
				original_sales_order = sales_order
			if frappe.db.get_value("Sales Order",original_sales_order,"allow_delivery"):
				return
			advance_paid = frappe.db.get_value("Sales Order", filters={"name": original_sales_order}, fieldname="advance_paid")
			grand_total = frappe.db.get_value("Sales Order", filters={"name": original_sales_order}, fieldname="grand_total")
			if grand_total != advance_paid:
				frappe.throw("收款后才能发货")
	
	def set_employee_and_department(self):
		employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user}, ["name", "department"], as_dict=1)
		if employee:
			self.custom_employee = employee.name
			self.custom_department = employee.department

	def set_final_customer(self):
		if self.sales_order:
			final_customer = frappe.db.get_value("Sales Order", filters={"name": self.sales_order}, fieldname="final_customer")
			if final_customer:
				self.custom_final_customer = final_customer
			else:
				self.custom_final_customer = self.customer
	def set_freight(self):
		if self.sales_order:
			freight = frappe.db.get_value("Sales Order", self.sales_order, "custom_freight")
			if freight:
				self.custom_freight = freight
	
	def set_original_sales_order(self):
		if self.sales_order:
			custom_original_sales_order = frappe.db.get_value("Sales Order", self.sales_order, "custom_original_sales_order")
			if custom_original_sales_order:
				self.custom_original_sales_order = custom_original_sales_order
			else:
				self.custom_original_sales_order = self.sales_order

	def validate_qty_limit(self):
		so_details = [d.so_detail for d in self.items]
		so_details_str = str(tuple(so_details)).replace(',)',')')
		query = f"""
			select
				soi.item_code,
				soi.name as so_detail,
				soi.parent as so,
				soi.stock_qty as so_qty,
				dni.stock_qty as dn_qty,
				dni.dn_names
			from
				(
					select
						name,
						parent,
						item_code,
						stock_qty
					from
						`tabSales Order Item`
					where
						docstatus = 1
						and name in {so_details_str}

				) soi
			left join
				(
					select
						item_code,
						so_detail,
						sum(stock_qty) as stock_qty,
						group_concat(distinct parent) as dn_names
					from
						`tabDelivery Note Item`
					where
						docstatus < 2
						and so_detail in {so_details_str}
					group by
						item_code,so_detail

				) dni on soi.item_code = dni.item_code and soi.name = dni.so_detail
			where
				dni.stock_qty > soi.stock_qty
		"""
		items = frappe.db.sql(query, as_dict=1)
		if items:
			frappe.throw(
				_(
					"The sales order qty of item {0} in {1} {2} is {3}, but total delivery qty is {4} in {5} {6}, please check again."
				).format(
					frappe.bold(items[0].item_code),
					frappe.bold(_('Sales Order')),
					frappe.bold(items[0].so),
					frappe.bold(items[0].so_qty),
					frappe.bold(items[0].dn_qty),
					frappe.bold(_('Delivery Note')),
					frappe.bold(items[0].dn_names)
				),
				title=_("Limit Crossed"),
			)
	@frappe.whitelist()
	def get_important_reminders(self):
		if self.custom_original_sales_order:
			soname = [self.custom_original_sales_order]
		else:
			soname = list(set([d.against_sales_order for d in self.items if d.against_sales_order]))

		msg = ''
		if not frappe.has_permission('Sales Order', ptype='read'):
			return msg
		res = frappe.get_all('Sales Order',filters={'name':['in',soname],'custom_important_reminders':['!=','']},pluck='custom_important_reminders')

		for d in res:
			msg += f'<p class="text-danger bold h3">{d}</p>'

		return msg

	def validate_warehouse(self):
		from erpnext.stock.dashboard.item_dashboard import get_data
		for item in self.items:
			if frappe.db.get_value('Warehouse',item.warehouse,'for_sample') == 1:
				return
			stock_info = get_data(item.item_code,item.warehouse)
			if len(stock_info) > 0 and item.qty > stock_info[0].actual_qty:
				try:
					warehouse_found = False
					stock_avilable = get_data(item.item_code)
					for d in stock_avilable:
						if d.actual_qty >= item.stock_qty:
							item.warehouse = d.warehouse
							warehouse_found = True
							frappe.msgprint(_('Due to insufficient stock balance, the warehouse of {0} has been updated to {1}').format(item.item_code,item.warehouse))
							break
				except Exception as e:
					frappe.throw(_('Insufficient Stock'))

				if not warehouse_found:
					msg = _("#:{0} item {1} {2} is out of stock").format(item.idx,item.item_code,item.item_name)
					if self.docstatus == 0:
						frappe.msgprint(msg,alert=True)
					elif self.docstatus == 1:
						frappe.throw(_(msg),title=_('Error'))

def validate_shipper(doc, method=None):
	if frappe.session.user == 'Administrator':
		doc.shipper = 'HR-EMP-00218'
		doc.shipping_user = 'Administrator'
	return
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
		# 判断是否高分子
		level = 0
		employee_reports_to = frappe.db.get_value('Employee',employee.name,'reports_to')
		while level < 5 and employee_reports_to != 'HR-EMP-00457':
			level = level+1
			if employee_reports_to:
				employee_reports_to = frappe.db.get_value('Employee',employee_reports_to,'reports_to')
		if employee_reports_to == 'HR-EMP-00457':
			# 判断是东贝，东贝走朱坤芹
			shipper = "HR-EMP-00828"
		else: 
			# 判断是不是东贝，走王秋侠
			shipper = "HR-EMP-02111"

	if "HR-EMP-02157" in warehouse_employees:
		# 样品走王兆丰
		shipper = "HR-EMP-02157"

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
	sales_invoice.update({
		'owner': doc.owner,
		'posting_date': doc.modified,
		'posting_time': doc.modified.time()
	})
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

def validate_qty_limit(doc,method=None):
	doc.validate_qty_limit()

def update_internal_po_status(doc,method=None):
	if doc.is_internal_customer:
		internal_pos = list(set([d.purchase_order for d in doc.items]))
		if len(internal_pos) > 1:
			frappe.throw(_('More than one selection for {0} not allowed').format( _('Purchase Order')))
		if internal_pos:
			po_name = internal_pos[0]
			# check if all items are delivered
			internal_so_qurey = f"""
				select
					soi.item_code,
					sum(soi.qty) as qty,
					sum(soi.delivered_qty) as delivered_qty
				from
					`tabSales Order` so, `tabSales Order Item` soi
				where
					so.name = soi.parent
					and so.docstatus = 1
					and soi.purchase_order = '{po_name}'
				group by
					soi.item_code having sum(soi.qty) > sum(soi.delivered_qty)
			"""
			undelivery_items = frappe.db.sql(internal_so_qurey, as_dict=1)
			if doc.docstatus == 1 and len(undelivery_items) == 0:
				# update purchase order status to delivered if all items are delivered
				po_doc = frappe.get_doc("Purchase Order", po_name)
				po_doc.update_status('Delivered')
				po_doc.update_delivered_qty_in_sales_order()
			elif doc.docstatus == 2:
				# reset purchase order status
				po_doc = frappe.get_doc("Purchase Order", po_name)
				po_doc.update_status('Submitted')
				po_doc.update_delivered_qty_in_sales_order()

def split_delivery_note(doc,method=None):
	if doc.docstatus == 0 and doc.workflow_state in ('仓库审核','发货员确认出货') and not doc.raw_data:
		items = []
		for item in doc.items:
			item_info = item.as_dict()
			item_info.creation = None
			item_info.modified = None
			items.append(item_info)
		doc.raw_data = json.dumps({
			'items': items,
			'workflow_state': doc.workflow_state
		})
	elif doc.docstatus == 1:
		diff_items = []
		raw_data = json.loads(doc.raw_data)
		for row in raw_data['items']:
			row = frappe._dict(row)
			diff_status = None
			for item in doc.items:
				if item.so_detail == row.so_detail:
					diff_status = True
					qty_diff = row.qty - item.qty
					if qty_diff > 0:
						row.qty = qty_diff
						diff_items.append(row)
			if not diff_status:
				diff_items.append(row)

		if len(diff_items) > 0:
			new_dn = frappe.copy_doc(doc)
			new_dn.workflow_state = None
			for item in new_dn.items:
				for row in diff_items:
					if item.so_detail == row.so_detail:
						item.qty = row.qty
			new_dn.raw_data = json.dumps({
				'items': diff_items,
				'workflow_state': raw_data.get('workflow_state')
			})
			frappe.log(new_dn.as_dict())
			new_dn.insert()
			new_dn.db_set('workflow_state', raw_data.get('workflow_state'))
			msg = f"""
			<div>
				<h5>{_('New Delivery Note Created Successfully')}</h5>
				<a href="/app/delivery-note/{new_dn.name}" target="_blank">{new_dn.name}</a>
			</div>
			"""
			frappe.msgprint(msg, alert=1)