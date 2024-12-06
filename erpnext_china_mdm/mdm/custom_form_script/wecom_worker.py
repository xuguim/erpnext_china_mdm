import frappe.utils
import requests
import time
import datetime
import hashlib
import json
import math
import frappe
from frappe.model.document import Document
def get_access_token():
	url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=wwb5d592cbfd08e9b1&corpsecret=GqAKODDscruoUUpyhfNqBJLk-vf6J_XfeOmkGKD8w0Y"
	response = requests.get(url)
	result_json = response.json()
	return result_json['access_token']

# def get_access_token():
# 	setting = frappe.get_cached_doc("WeCom Setting")
# 	return setting.access_token

@frappe.whitelist(allow_guest=True)
#获取上级领导的userid
def get_leader_id(access_token, user_id):
	url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
	params = {
		"access_token": access_token,
		"userid": user_id,
	}
	response = requests.get(url, params=params)
	result_json = response.json()
	if result_json['direct_leader']:
		return result_json['direct_leader'][0]

@frappe.whitelist(allow_guest=True)
#更新员工的上级主管
def update_employee():
	access_token = get_access_token()
	employees = frappe.db.get_all('Employee', pluck = 'name')
	for name in employees:
		doc = frappe.get_doc('Employee', name)
		user_status = frappe.db.get_value('User', doc.user_id, 'enabled')
		if doc.status == 'Active' and user_status == 1:			
			leader_id = get_leader_id(access_token, doc.user_id)
			if leader_id and leader_id != doc.user_id:
				direct_leader = frappe.db.get_value('Employee', {'user_id': leader_id})
				if direct_leader:
					if doc.reports_to != direct_leader:
						doc.reports_to = direct_leader
						doc.save(ignore_permissions=True)