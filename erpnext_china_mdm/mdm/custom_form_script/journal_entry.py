import frappe

from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry

class CustomJournalEntry(JournalEntry):

    def before_save(self):
        name = frappe.db.exists("Payment Entry", {"custom_original_code": self.custom_bank_serial_number})
        if name:
            docstatus = frappe.db.get_value('Payment Entry', name, 'docstatus')
            if docstatus == 0:
                frappe.db.delete('Payment Entry', name)
            elif docstatus == 1:
                frappe.throw('无法创建，存在相同银行流水号的收付款凭证！')
