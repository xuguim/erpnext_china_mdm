import frappe
from frappe import _
from  frappe.contacts.doctype.contact.contact import Contact

class CustomContact(Contact):
	
	def set_primary(self, fieldname):
		# Used to set primary mobile and phone no.
		if len(self.phone_nos) == 0:
			setattr(self, fieldname, "")
			return

		field_name = "is_primary_" + fieldname

		is_primary = [phone.phone for phone in self.phone_nos if phone.get(field_name)]

		if len(is_primary) > 1:
			frappe.throw(
				_("Only one {0} can be set as primary.").format(frappe.bold(frappe.unscrub(fieldname)))
			)
		elif len(is_primary) == 0:
			last_phone = self.phone_nos[-1]
			if fieldname == 'mobile_no':
				last_phone.is_primary_mobile_no = 1
		primary_number_exists = False
		for d in self.phone_nos:
			if d.get(field_name) == 1:
				primary_number_exists = True
				setattr(self, fieldname, d.phone)
				break

		if not primary_number_exists:
			setattr(self, fieldname, "")

