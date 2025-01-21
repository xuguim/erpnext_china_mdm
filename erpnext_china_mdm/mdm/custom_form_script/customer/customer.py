# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import re
import frappe
from erpnext.selling.doctype.customer.customer import Customer
from erpnext_china_mdm.utils import qcc

class CustomCustomer(Customer):
	
	def validate(self):
		super().validate()
		self.clean_fields()
		self.check_customer_exists()
		self.qcc_verify()
		self.check_customer_type_changed()

	def clean_fields(self):
		if self.customer_name:
			self.customer_name = str(self.customer_name).replace(' ', '')
	
	def check_customer_exists(self):
		# 同一条线索只能创建一个客户
		if (self.has_value_changed("customer_type") or self.has_value_changed("customer_name")) and self.customer_type == "Company" and frappe.db.exists("Customer", {"customer_type": "Company", "customer_name": self.customer_name}):
			frappe.throw("公司客户不可重复")
		if self.has_value_changed("lead_name") and frappe.db.exists("Customer", {"lead_name": self.lead_name}):
			frappe.throw("当前线索已经创建过客户，不可重复创建！")

	def qcc_verify(self):
		# 如果公司类型的客户 修改了客户名或者个人客户修改为公司客户则必须要通过企查查查询
		if (self.has_value_changed("customer_name") or self.has_value_changed("customer_type")) and self.customer_type == 'Company':
			config = frappe.get_single("QCC Settings")
			q = qcc.QccApiNameSearch(app_key=config.app_key, secret_key=config.secret_key)
			result = q.name_search(self.customer_name)
			if not result:
				frappe.throw("企查查未找到相似企业名称，请检查客户名称后重试")
			if result.code != 200:
				frappe.throw(result, title="企查查查询失败")
			else:
				if self.customer_name not in result.data:
					frappe.throw(result.data, title="客户名称验证失败，复制下列公司名称中的一个作为客户名称，再保存", as_list=True)

	def check_customer_type_changed(self):
		old = self.get_doc_before_save()
		# 个人->公司，公司 x->个人
		if old and old.customer_type == 'Company' and self.customer_type == "Individual":
			frappe.throw("公司客户不可转化为个人客户！")

	def set_primary_address(self):
		# 如果首选地址没填，则设置一个默认首选地址
		if not self.customer_primary_address:
			name = frappe.db.get_value('Dynamic Link', filters={
				'link_name': self.customer_name,
				'parenttype': 'address'
				}, fieldname='parent')
			self.customer_primary_address = name
	
	def set_check(self):
		# 修改被关联主客户的是否主客户勾选款
		if self.custom_parent_customer:
			doc = frappe.get_doc('Customer', self.custom_parent_customer)
			doc.custom_is_parent_customer = 1
			doc.save(ignore_permissions=True)

	def set_default_customer_owner_employee(self):
		if self.is_new():
			employee = frappe.db.get_value("Employee", filters={"user_id": self.owner}, fieldname="name")
			self.custom_customer_owner_employee = employee
			self.custom_customer_owner_user = self.owner

	def before_save(self):
		# 如果客户关联的线索发生变化，同时修改客户联系方式子表
		if self.has_value_changed("lead_name"):
			self.custom_customer_contacts = []
			if self.lead_name:
				lead = frappe.get_doc("Lead", self.lead_name)
				self.add_customer_contact_item(lead)
		self.set_primary_address()
		self.set_check()
		self.set_default_customer_owner_employee()
		
	def add_customer_contact_item(self, lead):
		contact_name = lead.first_name
		lead_name = lead.name
		for info in list(set([lead.custom_wechat, lead.mobile_no, lead.phone])):
			if info:
				self.append("custom_customer_contacts", {
					"contact_name": contact_name,
					"contact_info": info,
					"source": "Lead",
					"lead": lead_name
				})


@frappe.whitelist()
def transfer_to_user(**kwargs):
	employee = kwargs.get('employee')
	doc_name = kwargs.get('doc')
	employee_info = frappe.db.get_value("Employee", filters={"name": employee}, fieldname=["first_name", "user_id"], as_dict=True)
	
	customer = frappe.get_doc("Customer", doc_name)
	customer.custom_customer_owner_employee = employee
	customer.custom_customer_owner_user = employee_info.user_id
	customer.save(ignore_permissions=True)
	customer.add_comment("Comment", f"{frappe.session.user}将{doc_name}转移给{employee}")
	
	lead = frappe.get_doc("Lead", customer.lead_name)
	lead.custom_lead_owner_employee = employee
	lead.lead_owner = employee_info.user_id
	lead.save(ignore_permissions=True)
	lead.add_comment("Comment", f"{frappe.session.user}通过转移{doc_name}同时将{lead.name}转移给{employee}")
	
	return {"employee_name": employee_info.first_name}
