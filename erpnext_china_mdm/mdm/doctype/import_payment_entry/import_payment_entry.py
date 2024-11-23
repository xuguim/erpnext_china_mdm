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

def add_import_payment_entry_log(import_payment_entry, payment_entry, original_code, success:bool, error):
	if success:
		error = ''
	doc = frappe.new_doc('Import Payment Entry Log')
	doc.import_payment_entry = import_payment_entry
	if payment_entry:
		doc.payment_entry = payment_entry
	if original_code:
		doc.original_code = original_code
	doc.success = success
	doc.error = error
	doc.insert(ignore_permissions=True)

class ImportPaymentEntry(Document):
	
	def format_data(self, path):
		df = pd.read_excel(path)
		rows = df.to_dict(orient='records')
		result = []
		for row in rows:
			item = {}
			for k, v in row.items():
				if pd.isna(v):
					v = None
				value = strip_whitespace(v)
				item[strip_whitespace(k)] = value
			result.append(item)
		return result

	def check_or_create_other_bank(self):
		if not frappe.db.get_value('Bank', filters={'name': '其他'}):
			doc = frappe.new_doc('Bank')
			doc.bank_name = '其他'
			doc.insert(ignore_permissions=True)

	def create_party_bank_account(self, account_name, bank_name, bank_account_no,  bank=''):
		doctype = 'Bank Account'
		count = frappe.db.count(doctype, filters={"account_name": ['like', f'{account_name}%']})
		if count > 0:
			account_name += f'-{count}'

		self.check_or_create_other_bank()

		doc = frappe.new_doc('Bank Account')
		doc.account_name = account_name
		doc.bank = '其他'
		doc.bank_name = bank_name
		doc.bank_account_no = bank_account_no
		doc.insert(ignore_permissions=True)
		return doc.name

	def validate_amount(self, amount):
		if amount is None or float(amount) < 0:
			frappe.throw(f'导入的文件中存在错误的数据格式：{amount}！')
	
	def get_paid_to(self, company, bank_account, mode_of_payment):
		bank = get_default_bank_cash_account(
			company, "Bank", mode_of_payment=mode_of_payment, account=bank_account
		)

		if not bank:
			bank = get_default_bank_cash_account(
				company, "Cash", mode_of_payment=mode_of_payment, account=bank_account
		)
		return bank
	
	def create_payment_entry(self, data: dict):
		data.update({
			'doctype': 'Payment Entry'
		})
		doc = frappe.get_doc(data)
		doc.insert(ignore_permissions=True)
		return doc

	def get_base_data(self):
		company = self.company
		bank_account = self.bank_account
		mode_of_payment = self.mode_of_payment
		temporary_customer = self.temporary_customer
		party_type = 'Customer'
		account = frappe.db.get_value('Bank Account', filters={'name': bank_account}, fieldname='account')
		if not account:
			bank = self.get_paid_to(company, bank_account, mode_of_payment)
			account = bank.account
		return {
			'payment_type': 'Receive',
			'company': company,
			'mode_of_payment': mode_of_payment,
			'party_type': party_type,
			'bank_account': bank_account,
			'party': temporary_customer,
			'paid_to': account,
			'paid_to_account_currency': 'CNY',
			'source_exchange_rate': 1,
			'target_exchange_rate': 1,
		}

	def validate_bank_records(self):
		bank_file = self.bank_file
		base_path = frappe.utils.get_site_path()
		path = base_path + bank_file
		self.result = ''
		
		if self.has_value_changed('bank_file') and self.bank_file:
			if self.bank == '中国建设银行':
				self.validate_ccb(path)
		

	def before_save(self):
		self.validate_bank_records()

	def validate_ccb(self, path):
		err_record = {}
		raw_data = []
		try:
			raw_data = self.format_data(path)
			for record in raw_data:
				err_record = record
				amount = record.get('贷方发生额/元(收入)')
				self.validate_amount(amount)

				party_account = record.get('对方户名')
				if not party_account:
					frappe.throw('对方户名必须有值')

			self.result = f'共{len(raw_data)}条数据需要验证，验证成功，可以执行导入'
		except Exception as e:
			self.result = f'共{len(raw_data)}条数据需要验证，验证失败：' + str(e) + '\n' + str(err_record)

	def get_reference_no(self, reference_date):
		bank_account = frappe.get_doc('Bank Account', self.bank_account)
		count = frappe.db.count('Payment Entry', filters={'bank_account': self.bank_account})
		bank_sufix_no = bank_account.bank_account_no[-4:] if bank_account.bank_account_no else ''
		date_str = datetime.strptime(reference_date, r"%Y-%m-%d %H:%M:%S").strftime(r"%Y%m%d%H%M%S")
		length = len(str(count))
		count_str = '0'*(4 - length) + str(count) if count < 1000 else count
		return f'ccb-{bank_sufix_no}-{date_str}-{count_str}'

	def ccb(self):
		bank_file = self.bank_file
		base_path = frappe.utils.get_site_path()
		file_path = base_path + bank_file
		raw_data = self.format_data(file_path)
		count = 0
		total = len(raw_data)
		amount_0_count = 0
		exist_count = 0
		for record in raw_data:
			amount = record.get('贷方发生额/元(收入)')
			original_code = record.get('账户明细编号-交易流水号')
			
			if float(amount) == 0:
				amount_0_count += 1
				add_import_payment_entry_log(self.name, None, original_code, False, '收款金额为0')
				continue
			
			name = frappe.db.exists('Payment Entry', {'custom_original_code': original_code})
			if name:
				exist_count += 1
				add_import_payment_entry_log(self.name, name, original_code, False, '流水号已经存在')
				continue

			party_bank_account = self.create_party_bank_account(record.get('对方户名'), record.get('对方开户机构'), record.get('对方账号'), '其他')
			reference_date = record.get('交易时间')
			reference_date = datetime.strptime(reference_date, r'%Y%m%d %H:%M:%S').strftime(r"%Y-%m-%d %H:%M:%S")
			posting_date = record.get('记账日期')
			posting_date = datetime.strptime(str(posting_date), r'%Y%m%d').strftime(r"%Y-%m-%d")
			data = {
				'custom_original_code': original_code,
				'custom_payment_note': record.get('备注'),
				'custom_payment_record_from': self.name,
				'posting_date': posting_date,
				'party_bank_account': party_bank_account,
				'paid_amount': amount,
				'received_amount': amount,
				'reference_date': reference_date,
				'reference_no': self.get_reference_no(reference_date),
			}
			data.update(self.get_base_data())
			customer = frappe.db.get_value('Customer', filters={'name': record.get('对方户名')}, fieldname='name')
			if customer:
				data['party'] = customer
			new_payment_entry_doc = self.create_payment_entry(data)
			add_import_payment_entry_log(self.name, new_payment_entry_doc.name, original_code, True, '')
			count += 1
		return total, count, amount_0_count, exist_count

	@frappe.whitelist()
	def import_payment_entry(self):
		if self.bank_type == '中国建设银行':
			total, count, amount_0_count, exist_count = self.ccb()
			self.result = '\n'.join([
				f'共{total}条数据',
				f'本次导入{count}条',
				f'忽略收款金额为0的{amount_0_count}条',
				f'忽略流水号已经存在的{exist_count}条',
			])
			frappe.msgprint(self.result)
	
	@frappe.whitelist()
	def get_bank_account(self):
		name = frappe.db.get_value('Bank Account', filters={'bank': self.bank}, fieldname='name')
		if name:
			return {'account': name}
	
	@frappe.whitelist()
	def get_temporary_customer(self):
		name = frappe.db.get_value('Customer', filters={'name': '临时客户'}, fieldname='name')
		if name:
			return {'customer': name}