import frappe

def auto_validate_lead_status():
	query = f"""
		UPDATE `tabLead`
		SET `status` = 'Converted'
		WHERE `name` IN (
			select
				distinct lead.name
			from
				`tabLead` lead, `tabCustomer` customer, `tabPayment Entry` pe
			where
				lead.name = customer.lead_name
				and customer.name = pe.party
				and pe.docstatus = 1
				and pe.payment_type = 'Receive'
				and pe.paid_amount > 0
				and lead.status != 'Converted'
				and lead.custom_other_source = '业务自录入'
		)
	"""
	frappe.db.sql(query)