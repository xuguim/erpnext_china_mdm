# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import get_timespan_date_range
from frappe.utils.dateutils import get_from_date_from_timespan, get_period_ending

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	chart_data = get_chart_data(data,filters)
	return columns, data, None, chart_data

def get_data(filters):
	from_date, to_date = get_timespan_date_range('this month')
	pe_filters = {
		'docstatus': 1,
		'payment_type': 'Receive',
		'posting_date': ["between", [from_date, to_date]]
	}
	# use get_list to apply permission for payment entry
	pe_list = frappe.get_list("Payment Entry", filters=pe_filters,fields=['name','party','posting_date','paid_amount'],debug=1)
	# if not pe_list:
	# 	return []
	pe_names = list(set([d.name for d in pe_list]))
	pe_name_string = str(tuple(pe_names)).replace(',)',')')

	query = f"""
		select
			pe.name as payment_entry,
			pe.posting_date,
			per.reference_name,
			per.reference_doctype,
			so.order_type,
			case when per.reference_doctype = 'Sales Order' then per.reference_name else null end as sales_order,
			ifnull(pe.paid_amount,0) as paid_amount,
			ifnull(per.allocated_amount,0) as allocated_amount
		from
			`tabPayment Entry` pe
		left join
			`tabPayment Entry Reference` per on per.parent = pe.name
		left join
			(
				select
					name as sales_order,
					order_type
				from
					`tabSales Order`
				where
					docstatus = 1
			)so on so.sales_order = per.reference_name and per.reference_doctype = 'Sales Order'
		left join
			(
				select
					name as sales_invoice
				from
					`tabSales Invoice`
				where
					docstatus = 1
			)si on si.sales_invoice = per.reference_name and per.reference_doctype = 'Sales Invoice'
		where
			per.docstatus = 1
			and per.parent in {pe_name_string}
		order by
			pe.posting_date desc
	"""
	data = frappe.db.sql(query, as_dict=1)
	si_names = list(set([d.reference_name for d in data if d.reference_doctype == 'Sales Invoice']))
	if si_names:
		si_query = f"""
			select
				si.name as sales_invoice,
				sii.sales_order,
				so.order_type
			from
				`tabSales Invoice` si
			left join
				`tabSales Invoice Item` sii on sii.parent = si.name
			left join
				`tabSales Order` so on so.name = sii.sales_order
			where
				si.docstatus = 1
				and si.name in {str(tuple(si_names)).replace(',)',')')}
		"""
		res = frappe.db.sql(si_query, as_dict=1)
		si_so_dict = {}

		for row in res:
			sales_invoice = row['sales_invoice']
			sales_order = row['sales_order']
			if sales_invoice in si_so_dict:
				si_so_dict[sales_invoice].append({'sales_order':sales_order,'order_type':row['order_type']})
			else:
				si_so_dict[sales_invoice] = [{'sales_order':sales_order,'order_type':row['order_type']}]
		for d in data:
			if d.reference_doctype == 'Sales Invoice':
				d.sales_order = si_so_dict.get(d.reference_name)[0].get('sales_order')
				d.order_type = si_so_dict.get(d.reference_name)[0].get('order_type')
	if filters.get('charts_based_on') == 'Order Type':
		for d in data:
			if d.order_type == 'Sales':
				d['sales_amount'] = d.allocated_amount
			elif d.order_type == 'Custom':
				d['custom_amount'] = d.allocated_amount
	
	return data

def get_chart_data(data,filters):
	if filters.get('charts_based_on') == 'Order Type':
		labels = list(set([d.order_type for d in data]))
		datapoints = []
		for order_type in labels:
			amount = 0
			for d in data:
				if d.order_type == order_type:
					amount += d.allocated_amount
			datapoints.append(amount)

		return {
			"data": {
				"labels": [_(d) for d in labels],
				"datasets": [{"name": _('Order Type'), "values": datapoints}],
			},
			"type": "bar",
			# "lineOptions": {"regionFill": 1},
			"fieldtype": "Currency",
		}
	elif filters.get('charts_based_on') == 'Item Group':
		# get item groups category
		item_groups = frappe.get_all('Item Group',
			filters={'parent_item_group':'成品'},
			fields=['name as item_group','lft','rgt'],
			order_by = 'lft'
		)
		item_group_dict = frappe._dict({'成品': '其他'})
		for item_group in item_groups:
			nodes = frappe.get_all('Item Group',
				filters={
					'lft': ['>=', item_group.lft],
					'rgt': ['<=', item_group.rgt],
				},pluck='name')
			for node in nodes:
				item_group_dict[node] = item_group.item_group
		items = frappe.get_all('Sales Order Item',
			filters={
				'docstatus':1,
				'parent':['in',[d.sales_order for d in data]]
			},
			fields=['item_group','sum(amount) as amount','sum(custom_after_distinct__amount_request) as real_amount'],
			group_by="item_group"
		)
		for item in items:
			item['product_line'] = item_group_dict.get(item.item_group)
			# in case of custom_after_distinct__amount_request not applyed in test data
			if frappe.conf.developer_mode:
				item['real_amount'] = item.real_amount if item.real_amount else item.amount
		labels = list(set([d.product_line for d in items]))
		datapoints = []
		for product_line in labels:
			amount = 0
			for d in items:
				if d.product_line == product_line:
					amount += d.real_amount
			datapoints.append(amount)

		return {
			"data": {
				"labels": [_(d) for d in labels],
				"datasets": [{"name": _('Order Type'), "values": datapoints}],
			},
			"type": "bar",
			# "lineOptions": {"regionFill": 1},
			"fieldtype": "Currency",
		}


def get_columns(filters):
	columns = [
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 240,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Reference Doctype"),
			"fieldname": "reference_doctype",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Reference Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 240,
		},
		{
			"label": _('Source') +_("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 240,
		},
		{
			"label": _("Order Type"),
			"fieldname": "order_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Allocated Amount"),
			"fieldname": "allocated_amount",
			"fieldtype": "Currency",
			"width": 120,
		}
	]

	if filters.get('charts_based_on') == 'Order Type':
		columns.extend(
			[
				{
					"label": _("Sales") + _("Amount"),
					"fieldname": "sales_amount",
					"fieldtype": "Currency",
					"width": 120,
				},
				{
					"label": _("Custom") + _("Amount"),
					"fieldname": "custom_amount",
					"fieldtype": "Currency",
					"width": 120,
				}
			]
		)


	return columns