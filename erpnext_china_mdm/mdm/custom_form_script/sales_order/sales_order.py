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