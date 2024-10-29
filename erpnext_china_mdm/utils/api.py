import json
import frappe

@frappe.whitelist()
def employee(**kwargs):
    fields = ["name", "user_id","employee_number"]
    filters = kwargs.get('filters')
    filters = json.loads(filters) if filters else []
    return frappe.get_all("Employee", fields=fields, filters=filters)


@frappe.whitelist()
def lead(**kwargs):
    fields = ["name", "owner","custom_lead_owner_employee","lead_owner","source","custom_product_category","creation","first_name"]
    filters = kwargs.get('filters')
    filters = json.loads(filters) if filters else []
    order_by = kwargs.get('order_by', 'creation desc')
    limit_start = int(kwargs.get('limit_start', 0))
    limit = int(kwargs.get('limit', 10))
    return frappe.get_all("Lead", fields=fields, filters=filters, order_by=order_by, limit_start=limit_start, limit_page_length=limit)
