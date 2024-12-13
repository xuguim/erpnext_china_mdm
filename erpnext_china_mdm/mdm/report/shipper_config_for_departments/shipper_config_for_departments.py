# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def get_data(filters):
	departments = filter_departments(filters)
	out = prepare_data(
		departments,
		filters
	)

	return out
def filter_departments(filters,company=None):
	depth=20
	departments = get_departments(filters,company)
	parent_children_map = {}
	accounts_by_name = {}
	root_department = frappe.db.get_value('Department',filters={'company':['is','not set']})
	for d in departments:
		accounts_by_name[d.name] = d
		parent_children_map.setdefault(d['parent_department'] or root_department, []).append(d)

	filter_departments = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []
			for child in children:
				child.indent = level
				filter_departments.append(child)
				add_to_list(child.name, level + 1)
	add_to_list(root_department, 0)

	return filter_departments

def prepare_data(departments,filters):
	data = []
	def add_child(data,departments):
		for d in departments:
			row = frappe._dict(
				{
					"department": _(d.name),
					"parent_department": _(d.parent_department) if d.parent_department else "",
					"indent": flt(d.indent) + 1,
					"is_group": d.is_group,
					"company": d.company,
					"employee": d.employee,
					"employee_name": d.employee_name,
					"default_shipper": d.default_shipper
				}
			)
			data.append(row)
	
	data.append(
		{
			"department": frappe.db.get_value('Department',filters={'company':['is','not set']}),
			"parent_department": "",
			"indent": 0,
			"is_group": 1,
		}
	)

	if not filters.get('company'):
		companys = frappe.get_list('Company',pluck='name')
		for company in companys:
			company_departments = [d for d in departments if d.company == company]
			data.append(
				{
					"department": company,
					"parent_department": "",
					"indent": 0,
					# "is_group": 1,
				}
			)
			add_child(data,company_departments)
	else:
		add_child(data,departments)

	return data
def get_departments(filters,company):
	conditions = ''
	if filters.get('company'):
		conditions += f" and dept.company = '{filters.get('company')}'"
	query = f"""
		select 
			dept.name, 
			dept.department_name, 
			dept.parent_department, 
			dept.company,
			dept.lft, 
			dept.rgt, 
			dept.is_group,
			group_concat(shipper.employee_name) as employee_name,
			shipper.is_default,
			defaults.employee_name as default_shipper
		from
			`tabDepartment`  dept
		left join
			`tabShipper` shipper on shipper.parent = dept.name
		left join
			(
				select 
					parent, 
					employee_name 
				from
					`tabShipper`
				where
					is_default = 1
			) defaults on defaults.parent = dept.name
		where
			dept.disabled = 0
			and dept.company is not null
			{conditions}
		group by
			dept.name
		order by
			dept.lft
		"""
	return frappe.db.sql(query,as_dict=True,debug=frappe.get_conf().developer_mode)

def get_columns():
	columns = [
		{
			"label": _("Department"),
			"fieldtype": "Link",
			"fieldname": "department",
			"width": 360,
			"options": "Department",
		},
		{
			"label": _("Shipper"),
			"fieldtype": "Data",
			"fieldname": "employee_name",
			"width": 300,
		},
		{
			"label": _("Default"),
			"fieldtype": "Data",
			"fieldname": "default_shipper",
			"width": 100,
		},
	]
	return columns