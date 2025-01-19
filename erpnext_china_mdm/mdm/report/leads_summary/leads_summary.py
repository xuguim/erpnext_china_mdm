# Copyright (c) 2025, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import get_timespan_date_range
from frappe.utils import flt, get_date_str

def execute(filters=None):
	columns, data = [], []
	fields,meta = get_fields()
	data = get_data(filters,fields)
	columns = get_columns(filters,fields,meta)
	chart = get_chart_data(data,filters)
	return columns, data, None, chart

def get_fields():
	meta = frappe.get_meta('Lead')
	required_fields = ['name', 'creation', 'modified']
	fields = [f.fieldname for f in meta.fields if (f.in_list_view or f.reqd or f.fieldname == 'name') and f.fieldtype not in ('Table')]
	for field in required_fields:
		if field not in fields:
			fields.append(field)
	return fields,meta

def get_data(filters,fields):
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if '董事长' not in roles:
		return []
	if filters.get('timespan'):
		daterange = filters.get('timespan').lower()
	else:
		daterange = 'this month'
	from_date, to_date = get_timespan_date_range(daterange)
	fields.extend(['count(name) as qty','Date(creation) as create_date'])
	group_by = 'create_date'
	if filters.get('more_details'):
		group_by = 'name'
	data = frappe.get_list('Lead',
		filters={
			'creation': ['between', [from_date, to_date]],
		},
		fields=fields,
		group_by=group_by,
		order_by='create_date desc',
	)
	
	expenses = get_lead_expenses(daterange)
	date_list = list(set([get_date_str(d.get('create_date')) for d in data]))
	qty_dict = {}
	for date in date_list:
		qty_dict[date] = len([x for x in data if get_date_str(x.get('create_date'))==date])

	for d in data:
		d['create_date'] = get_date_str(d['create_date'])
		total_amount = flt(expenses.get(d.get('create_date')))
		amount = total_amount / qty_dict[d['create_date']]

		d.update({
			'amount': amount,
			'cost': flt(amount) / d.get('qty')
		})
	return data

def get_chart_data(data,filters):
	if not data:
		return
	labels = list(set([d.create_date for d in data]))
	lead_qty_list = []
	expenses_list = []
	datasets = []
	for date in labels:
		lead_qty = 0
		lead_expense_amount = 0
		for row in data:
			if row.get('create_date') == date:
				lead_qty += row.get('qty')
				lead_expense_amount += row.get('amount')
		lead_qty_list.append(lead_qty)
		expenses_list.append(flt(lead_expense_amount,2))
	if filters.get('chart_value') == 'Qty':
		datasets = [{"name": _('Lead Qty'), "values": lead_qty_list,"fieldtype":"Int", "chartType": "bar",}]
	elif filters.get('chart_value') == 'Expenses':
		datasets = [{"name": _('Lead Expenses'), "values": expenses_list, "fieldtype": "Currency", "chartType": "line",}]
	else:
		datasets = [
			{"name": _('Lead Qty'), "values": lead_qty_list,"fieldtype":"Int","chartType": "bar",},
			{"name": _('Lead Expenses'), "values": expenses_list, "fieldtype": "Currency", "chartType": "line",}
		]
	return {
			"data": {
				"labels": [d[-8:] for d in labels],
				"datasets": datasets,
			},
			"type": "bar",
		}

def get_lead_expenses(daterange):
	from_date, to_date = get_timespan_date_range(daterange)
	lead_expenses = frappe.get_all('Lead Expenses',
		filters={'docstatus':1,'posting_date': ['between', [from_date, to_date]]},
		fields = ['posting_date','sum(amount) as amount'],
		group_by='posting_date',
	)
	return frappe._dict({get_date_str(d['posting_date']): d['amount'] for d in lead_expenses})

def get_columns(filters,fields,meta):
	columns = [
		{
			"label": _("Creation"),
			"fieldname": "create_date",
			"fieldtype": "Date",
			"width": "120px"
		},
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Data",
			"width": "80px",
		}
	]
	if filters.get('more_details'):
		columns.extend([
			{
				"label": _("Name"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Lead",
				"width": "240px"
			},
			
		])
		for field in meta.fields:
			if field.fieldname in fields:
				columns.append({
					"label": _(field.label),
					"fieldname": field.fieldname,
					"fieldtype": field.fieldtype,
					"options": field.options,
					"width": field.width or '120px'
				})
	columns.extend([
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": "120px"
		},
		{
			"label": _("Cost"),
			"fieldname": "cost",
			"fieldtype": "Currency",
			"width": "120px"
		}
	])
	return columns