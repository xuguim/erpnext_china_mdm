# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt

from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
import frappe.utils
import pandas as pd
import frappe
from datetime import datetime
from frappe.model.document import Document


def strip_whitespace(x):
	if isinstance(x, str):
		return x.strip()
	return x

def get_paid_to(company, bank_account, mode_of_payment):
	bank = get_default_bank_cash_account(
		company, "Bank", mode_of_payment=mode_of_payment, account=bank_account
	)

	if not bank:
		bank = get_default_bank_cash_account(
			company, "Cash", mode_of_payment=mode_of_payment, account=bank_account
	)
	return bank

def add_import_payment_entry_log(import_payment_entry, payment_entry, bank_transaction, original_code, success:bool, error):
	if success:
		error = ''
	doc = frappe.new_doc('Import Payment Entry Log')
	doc.import_payment_entry = import_payment_entry
	if payment_entry:
		doc.payment_entry = payment_entry
	if original_code:
		doc.original_code = original_code
	if bank_transaction:
		doc.bank_transaction = bank_transaction
	doc.success = success
	doc.error = error
	doc.insert(ignore_permissions=True)

def clean_file_field(row:dict, mapping_row):
	item = {}
	keys = [strip_whitespace(k) for k in row.keys()]
	for mapping in mapping_row:
		if mapping.file_field not in keys:
			frappe.throw(f'导入的文件数据缺失：{mapping.file_field}，请检查交易明细文件数据是否正确')
			
		for k, v in row.items():
			key = strip_whitespace(k)
			if key == mapping.file_field:
				if pd.isna(v):
					v = ''
				value = strip_whitespace(v)
				field_type = mapping.field_type
				if not field_type:
					field_type = '字符串'
				try:
					if field_type == '字符串':
						value = str(value)
					elif field_type == '整数':
						value = int(value)
					elif field_type == '浮点数':
						value = float(value)
					elif field_type == '日期':
						value = datetime.strptime(value, mapping.file_field_format)
					elif field_type == '日期时间':
						value = datetime.strptime(value, mapping.file_field_format)
					item[mapping.code_field] = value
					break
				except:
					frappe.throw(f'导入的文件中存在错误的数据格式：{value}转化为{field_type}，请检查交易明细文件数据是否正确')
	return item

def create_mode_of_payment():
	doc = frappe.new_doc('Mode of Payment')
	doc.mode_of_payment = '转账'
	doc.enabled = 1
	doc.type = 'Bank'
	doc.insert(ignore_permissions=True)
	return doc.name

def create_supplier():
	doc = frappe.new_doc('Supplier')
	doc.supplier_name = '临时供应商'
	doc.supplier_type = 'Individual'
	doc.insert(ignore_permissions=True)
	return doc.name

def check_default_party(deposit):
	if deposit > 0:
		party = '临时客户'
		name = frappe.db.get_value('Customer', filters={'customer_name': party})
		if not name:
			frappe.throw('请先创建 临时客户')
		party_type = 'Customer'
		payment_type = 'Receive'
	else:
		party = '临时供应商'
		name = frappe.db.get_value('Supplier', filters={'supplier_name': party})
		if not name:
			create_supplier()
		party_type = 'Supplier'
		payment_type = 'Pay'
	return party_type, payment_type, party

def get_payment_entry_data(result, company, bank_account, payment_record_from):
	amount = result.get('deposit')
	party_type, payment_type, party = check_default_party(amount)
	original_code = result.get('reference_number')

	reference_date = result.get('date')
	reference_date = reference_date.strftime(r"%Y-%m-%d")
	
	mode_of_payment = frappe.db.get_value('Mode of Payment', filters={'name': '转账'})
	if not mode_of_payment:
		mode_of_payment = create_mode_of_payment()
	account = frappe.db.get_value('Bank Account', filters={'name': bank_account}, fieldname='account')
	if not account:
		bank = get_paid_to(company, bank_account, mode_of_payment)
		account = bank.account

	data = {
		'company': company,
		'mode_of_payment': mode_of_payment,
		'bank_account': bank_account,
		'paid_to': account,
		'paid_to_account_currency': 'CNY',
		'source_exchange_rate': 1,
		'target_exchange_rate': 1,
		'payment_type': payment_type,
		'custom_original_code': original_code,
		'custom_payment_note': result.get('custom_payment_note', ''),
		'custom_payment_record_from': payment_record_from,
		'paid_amount': amount,
		'party_type': party_type,
		'party': party,
		'received_amount': amount,
		'reference_date': reference_date,
		'reference_no': original_code,
	}
	if payment_type == 'Pay':
		data['paid_amount'] = result.get('withdrawal')
		data['paid_from'] = account
		data['paid_from_account_currency'] = 'CNY'
		data['received_amount'] = account
		data.pop('paid_to')
		data.pop('paid_to_account_currency')
	customer = frappe.db.get_value('Customer', filters={'name': result.get('account_name')}, fieldname='name')
	if customer:
		data['party'] = customer
	return data

@frappe.whitelist()
def create_payment_entry(result: dict, company, bank_account, name):
	payment_entry_data = get_payment_entry_data(result, company, bank_account, name)
	payment_entry_data.update({
		'doctype': 'Payment Entry'
	})
	doc = frappe.get_doc(payment_entry_data)
	doc.insert(ignore_permissions=True)
	return doc

@frappe.whitelist()
def create_bank_transaction(result: dict, company, bank_account):
	# party_type, _, party = check_default_party(result.get('deposit'))
	bank_transaction_data = {
		'date': result.get('date'),
		'company': company,
		'bank_account': bank_account,
		'deposit': result.get('deposit'),
		'withdrawal': result.get('withdrawal'),
		'reference_number': result.get('reference_number'),
		'bank_party_name': result.get('account_name'),
		'bank_party_account_number': result.get('bank_account_no'),
		'custom_party_bank_name': result.get('bank_name')
		# 'party_type': party_type,
		# 'party': party
	}
	bank_transaction_data.update({
		'doctype': 'Bank Transaction'
	})
	doc = frappe.get_doc(bank_transaction_data)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc

@frappe.whitelist()
def create_records(results, company, bank_account, from_name):
	payment_entry_exists_count = 0
	bank_transaction_exists_count = 0
	bank_transaction_count = 0
	payment_entry_count = 0
	for result in results:
		original_code = result.get('reference_number')
		name = frappe.db.exists('Bank Transaction', {'reference_number': original_code})
		if name:
			add_import_payment_entry_log(from_name, '', name, original_code, False, '银行交易已经存在')
			bank_transaction_exists_count += 1
		else:
			doc = create_bank_transaction(result, company, bank_account)
			add_import_payment_entry_log(from_name, '', doc.name, original_code, True, '')
			bank_transaction_count += 1
		
		name = frappe.db.exists('Payment Entry', {'custom_original_code': original_code})
		if name:
			add_import_payment_entry_log(from_name, name, '', original_code, False, '收付款凭证已经存在')
			payment_entry_exists_count += 1
		else:
			doc = create_payment_entry(result, company, bank_account, from_name)
			add_import_payment_entry_log(from_name, doc.name, '', original_code, True, '')
			payment_entry_count += 1
	return bank_transaction_count, payment_entry_count, payment_entry_exists_count, bank_transaction_exists_count

class ImportPaymentEntry(Document):
	
	def read_bank_file(self, ignore_rows):
		path = frappe.utils.get_site_path() + self.bank_file
		df = pd.read_excel(io=path, dtype=str, skiprows=ignore_rows)
		df = df.dropna(how='all')
		rows = df.to_dict(orient='records')
		return rows
	
	def get_clean_file_data(self):
		bank = frappe.get_doc('Bank', self.bank)
		rows = self.read_bank_file(bank.custom_ignore_rows)
		results = []
		for row in rows:
			item = clean_file_field(row, bank.custom_bank_fields_mapping)
			results.append(item)
		return results

	def validate_bank_transaction_data(self, data):
		deposit = data.get('deposit')
		withdrawal = data.get('withdrawal')
		if (deposit > 0 and withdrawal != 0) or (withdrawal > 0 and deposit != 0):
			frappe.throw(f'银行交易中存款和取款金额其中一方必须为0，请检查交易明细文件数据是否正确')

	def validate_payment_entry_data(self, data):
		pass
	
	def check(self):
		results = self.get_clean_file_data()
		for result in results:
			self.validate_bank_transaction_data(result)
			self.validate_payment_entry_data(result)
		return results
		
	def before_save(self):
		if self.bank_file and self.has_value_changed('bank_file'):
			results = self.check()
			self.result = '\n'.join([
				f'{datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")}',
				f'校验完成，本次共{len(results)}条数据，可以开始导入'
			])

	def before_submit(self):
		if not self.bank_file:
			frappe.throw(f'请先选择交易明细文件')
		results = self.check()
		bt_count, pe_count, pe_exists_count, bt_exists_count = create_records(results, self.company, self.bank_account, self.name)

		self.result = '\n'.join([
			f'{datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")}',
			f'共{len(results)}条数据',
			f'本次导入银行交易{bt_count}条',
			f'本次导入收款凭证{pe_count}条',
			f'忽略流水号已经存在的银行交易{bt_exists_count}条',
			f'忽略流水号已经存在的收付款凭证{pe_exists_count}条'
		])
		frappe.msgprint(self.result)
		self.db_update()
