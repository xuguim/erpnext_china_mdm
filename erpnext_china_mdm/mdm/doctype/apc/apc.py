# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt
import requests
import time
import hashlib
import json
import math
import frappe
from frappe.model.document import Document

class APC(Document):
	pass

def get_token():
	timespan = str(int(time.time()))
	doc = frappe.get_single("QCC Settings")
	appkey = doc.app_key
	secretkey = doc.secret_key
	token = appkey + timespan + secretkey
	hl = hashlib.md5()
	hl.update(token.encode(encoding='utf-8'))
	token = hl.hexdigest().upper()
	return timespan, appkey, token

def creat_apc(result):
	doc = frappe.new_doc('APC')
	doc.apc_id = result['Id']
	doc.apc_name = result['Name']
	doc.apc_type = result['Type']
	doc.apc_startdate = result['StartDate']
	doc.apc_enddate = result['EndDate']
	doc.apc_no = result['No']
	doc.apc_typedesc = result['TypeDesc']
	doc.apc_institutionlist = str(result['InstitutionList'])[2:-2]
	doc.apc_status = result['Status']
	doc.insert(ignore_permissions=True)

def creat_apc_type(result):
	doc = frappe.new_doc('Administrative Permits of Companies Type')
	doc.administrative_permits_of_companies_type_name = result['TypeDesc']
	doc.insert(ignore_permissions=True)

def get_certification(page_index):
	timespan, appkey, token = get_token()
	url = "http://api.qichacha.com/ECICertification/SearchCertification"
	params = {
		"key": appkey,
		"searchKey": "山东朱氏药业集团有限公司",
		"PageIndex": page_index,
		"PageSize": 20

	}
	headers={'Token': token,'Timespan':timespan}
	response = requests.get(url, params=params, headers=headers)
	result_json = response.json()
	return result_json

def get_certification_detail(cert_id):
	timespan, appkey, token = get_token()
	url = "https://api.qichacha.com/ECICertification/GetCertificationDetailById"
	params = {
		"key": appkey,
		"certId": cert_id,
	}
	headers={'Token': token,'Timespan':timespan}
	response = requests.get(url, params=params, headers=headers)
	result_json = response.json()
	return result_json

@frappe.whitelist(allow_guest=True)
def update_apc():
	# 第一次请求获取总条数
	result_json = get_certification(1)
	db_total = frappe.db.count('APC')
	page = math.ceil(result_json['Paging']['TotalRecords']/20)
	# page = 1
	if result_json['Paging']['TotalRecords'] > db_total:
		# 分页请求数据信息
		for page_index in range(1,page+1):
			results = get_certification(page_index)['Result']
			for result in results:
				if not frappe.db.exists('APC',result['No']):
					if not frappe.db.exists('Administrative Permits of Companies Type', result['TypeDesc']):
						creat_apc_type(result)
					creat_apc(result)
					cert_id = result['Id']
					# 根据Id获取详细信息
					result_a = get_certification_detail(cert_id)['Result']
					doc = frappe.get_doc('APC', result['No'])
					doc.apc_detailed_information = json.dumps(result_a['Data'], ensure_ascii=False)
					doc.save(ignore_permissions=True)

