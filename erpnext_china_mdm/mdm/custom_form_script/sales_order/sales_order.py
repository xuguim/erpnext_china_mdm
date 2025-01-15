import copy
import json
import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cstr, flt
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.share import add_docshare
from frappe.permissions import get_role_permissions
from erpnext.selling.doctype.sales_order.sales_order import WarehouseRequired
from erpnext_china.erpnext_china.custom_form_script.sales_order.sales_order import CustomSalesOrder
from frappe.utils import cint, cstr, flt
import frappe.utils

def validate_sales_team(doc,method=None):
	user = frappe.session.user
	if user == 'Administrator':
		return
	if doc.doctype == 'Sales Order' and not doc.sales_team:
		employee = frappe.db.get_value('Employee',{'user_id':user})
		if not employee:
			if user == 'Administrator':
				return
			else:
				frappe.throw("当前用户没有员工信息，请完善配置！")
		sales_person = frappe.db.get_value('Sales Person',{'employee':employee,})

		if not sales_person:
			frappe.throw("当前用户没有销售团队配置，请联系管理员！")
		else:
			sales_person = frappe.get_doc('Sales Person',sales_person)
			sales_team = {
				'parenttype':'Sales Order',
				'parentfield':'sales_team',
				'parent':doc.name,
				'sales_person':sales_person.name,
				'allocated_percentage':100,
				'department':sales_person.department,
				'reports_to':sales_person.reports_to
			}
			doc.append('sales_team',sales_team)


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
	from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
	from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
		get_sre_details_for_voucher,
		get_sre_reserved_qty_details_for_voucher,
		get_ssb_bundle_for_voucher,
	)

	source_name = validate_inter_company_sales_order(source_name)

	if not kwargs:
		kwargs = {
			"for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
			"skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
		}

	kwargs = frappe._dict(kwargs)

	sre_details = {}
	if kwargs.for_reserved_stock:
		sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

	mapper = {
		"Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
		"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
		"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
	}

	def set_missing_values(source, target):
		if kwargs.get("ignore_pricing_rule"):
			# Skip pricing rule when the dn is creating from the pick list
			target.ignore_pricing_rule = 1

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		# if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
		if frappe.flags.bulk_transaction:
			# set target items names to ensure proper linking with packed_items
			target.set_new_name()

		make_packing_list(target)

	def condition(doc):
		if doc.name in sre_details:
			del sre_details[doc.name]
			return False

		# make_mapped_doc sets js `args` into `frappe.flags.args`
		if frappe.flags.args and frappe.flags.args.delivery_dates:
			if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
				return False

		return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	if not kwargs.skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"condition": condition,
			"postprocess": update_item,
		}

	so = frappe.get_doc("Sales Order", source_name)

	# set user to Administrator for ignoring permissions
	if so.is_internal_customer:
		current_user = frappe.session.user
		frappe.set_user("Administrator")

	target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

	if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
		sre_list = get_sre_details_for_voucher("Sales Order", source_name)

		if sre_list:

			def update_dn_item(source, target, source_parent):
				update_item(source, target, so)

			so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

			for sre in sre_list:
				if not condition(so_items[sre.voucher_detail_no]):
					continue

				dn_item = get_mapped_doc(
					"Sales Order Item",
					sre.voucher_detail_no,
					{
						"Sales Order Item": {
							"doctype": "Delivery Note Item",
							"field_map": {
								"rate": "rate",
								"name": "so_detail",
								"parent": "against_sales_order",
							},
							"postprocess": update_dn_item,
						}
					},
					ignore_permissions=True,
				)

				dn_item.qty = flt(sre.reserved_qty) * flt(dn_item.get("conversion_factor", 1))

				if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
					dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

				target_doc.append("items", dn_item)
			else:
				# Correct rows index.
				for idx, item in enumerate(target_doc.items):
					item.idx = idx + 1

	# Should be called after mapping items.
	set_missing_values(so, target_doc)

	# set user back to current user
	if so.is_internal_customer:
		frappe.set_user(current_user)

		target_doc.insert(ignore_permissions=True)
		role_permissions = get_role_permissions(frappe.get_meta(target_doc.doctype), current_user)
		add_docshare(
				target_doc.doctype, 
				target_doc.name, 
				target_doc.owner, 
				read=role_permissions.get('read'), 
				write=role_permissions.get('write'), 
				submit=role_permissions.get('submit'), 
				share=1, 
				flags={"ignore_share_permission": True}
			)
	
	return target_doc

class MdmSalesOrder(CustomSalesOrder):
	def validate_warehouse(self):
		super().validate_warehouse()
		delivered_by_supplier = False
		delivered_by_company = False
		for d in self.get("items"):
			if d.delivered_by_supplier:
				delivered_by_supplier = True
			else:
				delivered_by_company = True
			if (
				(
					frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1
					or (
						self.has_product_bundle(d.item_code)
						and self.product_bundle_has_stock_item(d.item_code)
					)
				)
				and not d.warehouse
				and not cint(d.delivered_by_supplier)
			):
				frappe.throw(
					_("Delivery warehouse required for stock item {0}").format(d.item_code), WarehouseRequired
				)

			if d.stock_qty < 30:
				if '箱' in d.uom and d.qty >= 1:
					return
				else:
					uom_avilable = frappe.db.exists('UOM Conversion Detail',
						{
							'parent': d.item_code,
							'parenttype': 'Item',
							'parentfield': 'uoms',
							'uom':['like',"%箱%"]
						})
					if uom_avilable:
						conversion_factor = frappe.db.get_value('UOM Conversion Detail',uom_avilable,'conversion_factor')
						if d.stock_qty >= conversion_factor:
							return
						else:
							sample_warehouse = frappe.db.exists('Warehouse',
								{
									'company': self.company,
									'for_sample': 1,
									'is_group': 0,
									'disabled': 0
								})
							if sample_warehouse:
								d.warehouse = sample_warehouse
								msg ="""<p>第{}行的物料{}被<b>更新到样品仓库{}</b></p>""".format(
									frappe.bold(d.idx),
									frappe.bold(d.item_code),
									frappe.bold(sample_warehouse),
								)
								frappe.msgprint(msg,alert=True)
							else:
								msg = """
									<p>第{}行的物料{}低于销售要求，且<b style="color:red">未找到样品仓库</b></p>
									<p>单位:{}</p>
									<p>销售数量:{}</p>
									<p>库存单位数量:{}{}</p>
									<p>请联系管理员检查配置</p>
								""".format(
									frappe.bold(d.idx),
									frappe.bold(d.item_code),
									frappe.bold(d.uom),
									frappe.bold(d.qty),
									frappe.bold(d.stock_qty),
									frappe.bold(d.stock_uom),
								)
								frappe.throw(msg)
					else:
						msg = """
							<p>第{}行的物料{}低于销售要求，且<b style="color:red">没有设置箱的转换系数</b></p>
							<p>单位:{}</p>
							<p>销售数量:{}</p>
							<p>库存单位数量:{}</p>
							<p>请联系管理员检查配置</p>
						""".format(
							frappe.bold(d.idx),
							frappe.bold(d.item_code),
							frappe.bold(d.uom),
							frappe.bold(d.qty),
							frappe.bold(d.stock_qty),
						)
						frappe.throw(msg,title=_('Error'))
		if delivered_by_supplier and delivered_by_company:
			frappe.throw(_("Cannot deliver both by supplier and company in same sales order"))

@frappe.whitelist()
def allow_delivery(docname):
	doc = frappe.get_doc('Sales Order', docname)
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if '销售会计' in roles and doc.docstatus == 1 and doc.per_delivered < 100:
		doc.flags.ignore_validate_update_after_submit = True
		doc.allow_delivery = 1
		doc.add_comment("Comment", _("User: {0} set allow delivery as ture").format(user))
		doc.save()
		frappe.msgprint(_('Allow Delivery')+_('Complete'),alert=True)
		return True

def validate_inter_company_sales_order(docname):
	so = frappe.get_doc('Sales Order', docname)
	has_internal_so = len([d for d in so.items if d.delivered_by_supplier]) > 0
	if has_internal_so:
		po_query = f"""
			select
				distinct po.name
			from
				`tabPurchase Order` po, `tabPurchase Order Item` poi
			where
				po.docstatus = 1
				and po.name = poi.parent
				and poi.sales_order = '{so.name}'
		"""
		po_list = frappe.db.sql_list(po_query,as_dict=1)
		if len(po_list) > 0:
			po_name = po_list[0]
			so_query = f"""
				select
					distinct so.name
				from
					`tabSales Order` so, `tabSales Order Item` soi
				where
					so.docstatus = 1
					and so.name = soi.parent
					and soi.purchase_order = '{po_name}'
			"""
			so_list = frappe.db.sql_list(so_query,as_dict=1)
			return so_list[0]
	else:
		return docname
				
@frappe.whitelist()
def get_discount_by_accumulated_qty_of_multiple_so(**kwargs):
	customer = kwargs.get('customer')
	customer_name = kwargs.get('customer_name')
	item = kwargs.get("item")
	coupon_code_title = f"{customer_name or customer}-{str(item).split('-')[-1]}-优惠券"
	today = frappe.utils.today()
	valid_from = today
	before = frappe.utils.add_to_date(today, days=-30, as_string=True)
	valid_upto = frappe.utils.add_to_date(today, days=30, as_string=True)
	
	coupon_code = frappe.db.exists("Coupon Code", {
		"name": ["like", f"%{coupon_code_title}%"],
		"used": 0, 
		"valid_from": ["<=", valid_from], 
		"valid_upto": [">=", valid_upto]
	})
	if coupon_code:
		return {"coupon_code": coupon_code}
	
	# 定价规则关联的销售订单的物料行 name
	pricing_rule_so_item = frappe.db.get_all("Pricing Rule Detail", filters={
		"parenttype": "Sales Order",
		"item_code": item,
	}, pluck="child_docname")
	
	# 已经使用过累计满赠的销售订单物料行 name
	used_discount_so_item = frappe.db.get_all("Discount Reference Sales Order Items", filters={
		"item_code": item
	}, pluck="child_docname")

	# 找到当前客户、不是内部订单、没有使用优惠券、日期在最近30天内的销售订单 name
	so_names = frappe.db.get_all("Sales Order", filters={
		"customer": customer, 
		"is_internal_customer": 0,
		"coupon_code": "",
		"transaction_date": ["between", [before, today]]
	}, pluck="name")

	# 找出可参与累计优惠的销售订单物料行：非优惠物料、uom箱
	can_compute_so_items = frappe.db.get_all("Sales Order Item", filters={
		"parenttype": "Sales Order",
		"parent": ["in", so_names],
		"rate": [">", 0],
		"uom": "箱",
		"item_code": item,
		"name": ["not in", list(set(used_discount_so_item+pricing_rule_so_item))]
	}, fields=["name", "parent", "item_code", "qty", "transaction_date"])
	
	# 计算物料的累计数量
	total = sum([item.get('qty') for item in can_compute_so_items])
	if total < 10:
		return
	
	coupon_code_title += f"-{frappe.utils.random_string(1)}"
	new_price_rule_data = {
		"doctype": "Pricing Rule",
		"title": coupon_code_title,
		"apply_on": "Item Code",
		"price_or_product_discount": "Product",
		"selling": 1,
		"coupon_code_based": 1,
		"min_qty": 1,
		"same_item": 1,
		"free_qty": 1,
		"free_item_uom": "箱",
		"company": None,
		"apply_multiple_pricing_rules": 1,
		"has_priority": 1,
		"priority": 1,
		"currency": "CNY",
		"valid_from": today,
		"valid_upto": valid_upto,
		"applicable_for": "Customer",
		"customer": customer
	}
	new_price_rule = frappe.get_doc(new_price_rule_data)
	new_price_rule.append("items", {
		"item_code": item,
		"uom": "箱"
	})
	new_price_rule.company = None
	new_price_rule.insert(ignore_permissions=True)
	
	new_coupon_code_data = {
		"doctype": "Coupon Code",
		"coupon_name": coupon_code_title,
		"coupon_code": coupon_code_title,
		"coupon_type": "Promotional",
		"pricing_rule": new_price_rule.name,
		"maximum_use": 1,
		"valid_from": today,
		"valid_upto": valid_upto
	}
	new_coupon_code = frappe.get_doc(new_coupon_code_data)

	for item in can_compute_so_items:
		new_coupon_code.append("custom_sales_order_item", {
			'child_docname': item.get('name'),
			'sales_order': item.get('parent'),
			'item_code': item.get('item_code'),
			'qty': item.get('qty'),
			'transaction_date': item.get('transaction_date')
		})
	new_coupon_code.insert(ignore_permissions=True)
	
	return {"coupon_code": new_coupon_code.name}

@frappe.whitelist()
def query_coupon_code(doctype, txt, searchfield, start, page_len, filters):
	today = frappe.utils.today()
	sql = f"""
		SELECT cc.`name` FROM `tabCoupon Code` AS cc 
		WHERE cc.maximum_use > cc.used AND cc.valid_from <= "{today}" AND cc.valid_upto >= "{today}"
	"""
	coupon_codes = frappe.db.sql(sql, as_list=1)
	return coupon_codes