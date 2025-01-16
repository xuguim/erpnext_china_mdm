# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	message = '<b>说明：本报表只显示有效的销售价格，过期定价、没有公司信息的定价不显示在内</b>'
	return columns, data, message

def get_data(filters):
	conditions = get_conditions(filters)
	query = f"""
		select
			it.item_code,
			it.item_name,
			it.brand,
			it.stock_uom as uom,
			pr.min_qty,
			pr.rate,
			pr.valid_from,
			pr.valid_upto,
			pr.company,
			pr.name as pricing_rule,
			sle.stock_available,
			pr.title,
			case when pr.min_qty = 1 then rate else '' end as standard_selling_rate
		from
			`tabItem` it
		left join
			`tabPricing Rule Item Code` pri on pri.item_code = it.item_code
		left join
			`tabPricing Rule` pr on pr.name = pri.parent
		left join
			`tabItem Customer Detail` icd on icd.parent = it.name
		left join
			(
				select
					company,
					item_code,
					sum(actual_qty) stock_available
				from
					`tabStock Ledger Entry`
				where	
					is_cancelled = 0
				group by
					company,item_code
			) sle on sle.company = pr.company and sle.item_code = it.item_code
		where
			it.disabled = 0
			and icd.name is null
			and pr.disable = 0
			and pr.selling = 1
			and pr.rate_or_discount = 'Rate'
			and pr.apply_on = 'Item Code'
			and ( pr.title like '%分销价%' or pr.title like '%经销价%')
			{conditions}
		order by
			it.item_code, pr.min_qty
	"""
	res = frappe.db.sql(query, as_dict=1)
	if not filters.get('consolidate_items'):
		return res
	item_codes = list(set([d.item_code for d in res]))
	data = []
	for item_code in item_codes:
		idx = len(data)
		stock_available = 0
		standard_selling_rate = None
		data.append({'item_code': item_code})
		stock_uom = None
		for d in res:
			if d.item_code == item_code:
				stock_available += d.stock_available or 0
				if d.standard_selling_rate:
					standard_selling_rate = d.standard_selling_rate
				stock_uom = d.uom
				data.append({
					"item_code": d.item_code,
					"item_name": d.item_name,
					"brand": d.brand,
					"stock_available": d.stock_available,
					"min_qty": d.min_qty,
					"uom": d.uom,
					"rate": d.rate,
					"indent":1,
					"company": d.company,
					"pricing_rule": d.pricing_rule,
					"valid_from": d.valid_from,
					"valid_upto": d.valid_upto,
					"title": d.title,
					"standard_selling_rate": standard_selling_rate
				})
		data[idx]['stock_available'] = stock_available
		# data[idx]['standard_selling_rate'] = standard_selling_rate
		# data[idx]['uom'] = stock_uom
	return data

def get_columns(filters):
	return [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 240
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 240
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Link",
			"options": "Brand",
			"width": 120
		},
		# {
		# 	"label": _("Stock Available"),
		# 	"fieldname": "stock_available",
		# 	"fieldtype": "Float",
		# 	"width": 120
		# },
		{
			"label": _("Min Qty"),
			"fieldname": "min_qty",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"label": _("Standard Selling Rate"),
			"fieldname": "standard_selling_rate",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 240,
		},
		{
			"label": _("Pricing Rule"),
			"fieldname": "pricing_rule",
			"fieldtype": "Link",
			"options": "Pricing Rule",
			"width": 120
		},
		{
			"label": _("Title"),
			"fieldname": "title",
			"fieldtype": "Data",
			"width": 240
		},
		{
			"label": _("Valid From"),
			"fieldname": "valid_from",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Valid Upto"),
			"fieldname": "valid_upto",
			"fieldtype": "Date",
			"width": 120,
		},
	]


def get_conditions(filters):
	today = frappe.utils.nowdate()
	conditions = " and (it.end_of_life is null or it.end_of_life > '{0}')".format(today)
	if filters.get('item_group'):
		item_group_str = str(tuple(filters.get('item_group'))).replace(',)',')')
		conditions += " and it.item_group in {0}".format(item_group_str)
	if filters.get('item_code'):
		conditions += " and it.item_code = '{0}'".format(filters.get('item_code'))

	return conditions
@frappe.whitelist()
def get_finished_good_item_group_with_children():
	parent = '成品'

	if frappe.db.exists("Item Group", parent):
		lft, rgt = frappe.db.get_value("Item Group", parent, ["lft", "rgt"])
		children = frappe.get_all("Item Group", filters={"lft": [">=", lft], "rgt": ["<=", rgt]},order_by="lft")
		all_item_groups = [ig.name for ig in children]
	else:
		frappe.throw(_("Item Group: {0} does not exist").format(parent))

	return list(set(all_item_groups))