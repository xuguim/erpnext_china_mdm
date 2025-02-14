import json
import frappe
import frappe.utils
import pandas as pd, openpyxl
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_access_token():
	setting = frappe.get_cached_doc("WeCom Setting")
	return setting.access_token

def get_checkin_groups(access_token)->list[dict]:
	url = 'https://qyapi.weixin.qq.com/cgi-bin/checkin/getcorpcheckinoption'

	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	if result.get('errcode') != 0:
		raise Exception('get groups error: ' + result.get('errmsg', ''))
	return result.get('group')


def get_tag_users(access_token, tag_id)->list[dict]:
	url = 'https://qyapi.weixin.qq.com/cgi-bin/tag/get'
	params = {
		'access_token': access_token,
		'tagid': tag_id
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	if result.get('errcode') != 0:
		raise Exception('get userids from tag error: ' + result.get('errmsg', ''))
	return result.get('userlist')


def get_departments(access_token):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/department/list'
	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	if result.get('errcode') != 0:
		raise Exception('get departments error: ' + result.get('errmsg', ''))
	return result.get('department')


def get_user_detail(access_token, user_id):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/user/get'
	params = {
		'access_token': access_token,
		'userid': user_id
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	if result.get('errcode') != 0:
		raise Exception('get user detail error: ' + result.get('errmsg', ''))
	return {
		"name": result.get('name'),
		"department": result.get('department', [])
	}


def get_tags(access_token):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/tag/list'
	params = {
		'access_token': access_token
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	if result.get('errcode') != 0:
		raise Exception('get tags error: ' + result.get('errmsg', ''))
	return result.get('taglist')


def build_user_detail(access_token, user_id, departments_dict):
	user_detail = get_user_detail(access_token, user_id)
	user_department = user_detail.get('department', [])
	detail = {
		"name": user_detail.get('name', ''),
		"department": '；'.join([departments_dict.get(dept) for dept in user_department])
	}
	return user_id, detail

def build_user_detail_list(access_token, users, departments_dict):
	user_details = {}
	with ThreadPoolExecutor(max_workers=6) as t:
		obj_list = []
		for user_id in users:
			obj = t.submit(build_user_detail, access_token, user_id, departments_dict)
			obj_list.append(obj)

		for future in as_completed(obj_list):
			try:
				user_id, data = future.result()
				user_details[user_id] = data
			except:
				pass
	return user_details

def get_will_change_users(access_token, group_users_set, tag_users_set, departments_dict):
	
	# 标签中有，规则中没有则新增
	add_users = tag_users_set - group_users_set
	add_users = build_user_detail_list(access_token, add_users, departments_dict)
	# 标签中没有，规则中有则删除
	del_users = group_users_set - tag_users_set
	del_users = build_user_detail_list(access_token, del_users, departments_dict)
	return add_users, del_users

@frappe.whitelist()
def get_checkin_group_users(**kwargs):
	access_token = get_access_token()
	groups = get_checkin_groups(access_token)
	departments = get_departments(access_token)
	# {1: "xxxx"}
	departments_dict = {dept['id']: dept['name'] for dept in departments}

	tags = get_tags(access_token)
	# {"xxxx": 1}
	tags_dict = {tag['tagname']: tag['tagid'] for tag in tags}
	
	will_add = []
	will_del = []
	for group in groups:
		group_id = group.get('groupid')
		group_create_userid = group.get('create_userid')
		group_name = group.get('groupname')
		
		group_user_id_list = group.get('range').get('userid')
		group_user_id_set = set(group_user_id_list)

		# 如果规则名和标签名没有匹配，则跳过
		tag_id = tags_dict.get('考勤-' + group_name)
		if not tag_id:
			continue
		tag_user_list = get_tag_users(access_token, int(tag_id))
		tag_user_id_set = set([user.get('userid') for user in tag_user_list])

		add_users, del_users = get_will_change_users(access_token, group_user_id_set, tag_user_id_set, departments_dict)
		if len(add_users) > 0:
			data = {
				"group_id": group_id,
				"group_name": group_name,
				"group_create_userid": group_create_userid,
				"users": add_users
			}
			will_add.append(data)
		if len(del_users) > 0:
			data = {
				"group_id": group_id,
				"group_name": group_name,
				"group_create_userid": group_create_userid,
				"users": del_users
			}
			will_del.append(data)

	return {
		"add": will_add,
		"del": will_del
	}

def get_content(users: list):
	content = ''
	for info in users:
		group_name = info['group_name']
		user_str_list = []
		for _, user in info['users'].items():
			department = user['department']
			name = '【' + user['name'] + '】'
			user_info = '-'.join([name, department])
			user_str_list.append(user_info)
		content += '【' + group_name + '】' + '\n' + '\n'.join(user_str_list) + '\n\n'
	return content

@frappe.whitelist(allow_guest=True)
def send_modified_checkin_to_wecom():
	
	result = get_checkin_group_users()
	add_users = result.get('add', [])
	del_users = result.get('del', [])
	
	content = ''
	if len(del_users) > 0:
		content += '需移除员工\n' + get_content(del_users)
	if len(add_users) > 0:
		content += '需添加员工\n' + get_content(add_users)
	if content:
		access_token = get_access_token()
		url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + access_token
		
		# lilingyu@zhushigroup.cn|liuchao@zhushigroup.cn|wangmiao@zhushigroup.cn
		data = {
			"touser": "lilingyu@zhushigroup.cn|liuchao@zhushigroup.cn|wangmiao@zhushigroup.cn",
			"msgtype": "text",
			"agentid": 1000008,
			"text": {
				"content": "考勤规则变更通知\n\n" + content
			},
			"safe": 0,
			"enable_id_trans": 0,
			"enable_duplicate_check": 0
		}
		resp = requests.post(url, json=data)


def get_user_info(access_token, user_id):
	url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
	params = {
		"access_token": access_token,
		"userid": user_id,
	}
	response = requests.get(url, params=params)
	result_json = response.json()
	# if result_json['direct_leader']:
	# 	return result_json['direct_leader']
	return result_json

def get_user_from_department(access_token, department_id):
	url = 'https://qyapi.weixin.qq.com/cgi-bin/user/list'
	params = {
		'access_token': access_token,
		'department_id': department_id
	}
	resp = requests.get(url, params=params)
	result = resp.json()
	return result.get('userlist')

def handle_update_employee_reports_to():
	access_token = get_access_token()
	employees = frappe.db.get_all('Employee', filters={'status': 'Active'}, pluck = 'name')
	for name in employees:
		doc = frappe.get_cached_doc('Employee', name)
		if doc.user_id:
			user = frappe.get_cached_doc('User', doc.user_id)
			# 当前员工对应的用户账户关闭则员工状态改为离职或停用
			if not user.enabled:
				count = frappe.db.count('Employee', filters={'reports_to': doc.name})
				if count == 0:
					doc.status = 'Left'
				else:
					doc.status = 'Inactive'
				doc.relieving_date = frappe.utils.now()
				doc.save(ignore_permissions=True)
			else:
				wecom_uid = user.custom_wecom_uid or user.name
				result_json = get_user_info(access_token, wecom_uid)

				# 更新员工上级
				leader_ids = result_json.get('direct_leader')
				if not leader_ids or len(leader_ids) == 0:
					continue
				leader_id = leader_ids[0]
				if leader_id != wecom_uid:
					leader_users = frappe.get_all('User', or_filters={'name': leader_id, 'custom_wecom_uid': leader_id}, pluck='name')
					if leader_users and len(leader_users) > 0:
						leader_user_id = leader_users[0]
						direct_leader = frappe.db.get_value('Employee', filters={'user_id': leader_user_id})
						if direct_leader and doc.reports_to != direct_leader:
							doc.reports_to = direct_leader
							doc.save(ignore_permissions=True)
	frappe.db.commit()


# 更新员工的上级主管
@frappe.whitelist(allow_guest=True)
def update_employee_reports_to():
	frappe.enqueue(method=handle_update_employee_reports_to, queue="long", timeout=3600, job_name="handle_update_employee_reports_to")
	

# 同步部门及部门下的员工
@frappe.whitelist()
def update_department():
	access_token = get_access_token()
	departments = get_departments(access_token)
	doctype = 'Department'
	# 先创建或修改所有部门
	for dept in departments:
		wecom_id = dept.get('id')
		name = dept.get('name')

		dept_name = frappe.db.get_value(doctype, filters={'department_name': name})
		if dept_name:
			doc = frappe.get_doc(doctype, dept_name)
			if doc.custom_wecom_id != wecom_id:
				doc.custom_wecom_id = wecom_id
				doc.save(ignore_permissions=True)
		else:
			new_doc = frappe.new_doc(doctype)
			new_doc.department_name = name
			new_doc.custom_wecom_id = wecom_id
			new_doc.is_group = 1
			new_doc.insert(ignore_permissions=True)
	
	# 设置部门关系
	for dept in departments:
		wecom_id = dept.get('id')
		parent_id = dept.get('parentid')
		name = frappe.db.get_value(doctype, filters={'custom_wecom_id': wecom_id})
		if name:
			doc = frappe.get_doc(doctype, name)
			parent_department_name = frappe.db.get_value(doctype, filters={'custom_wecom_id': parent_id})
			if parent_department_name and doc.parent_department != parent_department_name:
				parent = frappe.get_doc(doctype, parent_department_name)
				doc.parent_department = parent.name
				doc.save(ignore_permissions=True)
	frappe.db.commit()

def handle_update_employee_department():
	try:
		access_token = get_access_token()
		departments = frappe.get_all(
			'Department', 
			filters={'custom_wecom_id': ['!=', '']},
			fields=['name', 'custom_wecom_id']
		)

		all_users_info = {}
		for deparment in departments:
			department_wecom_id = deparment.get('custom_wecom_id')
			user_list = get_user_from_department(access_token, department_wecom_id)
			for info in user_list:
				user_wecom_id = info.get('userid')
				main_department_wecom_id = info.get('main_department')
				all_users_info[user_wecom_id] = main_department_wecom_id

		user_map = frappe.db.get_all(
			'User',
			or_filters=[
				['custom_wecom_uid', 'in', list(all_users_info.keys())],
				['name', 'in', list(all_users_info.keys())]
			],
			filters={'enabled': 1},
			fields=['name', 'custom_wecom_uid']
		)
		user_dict = {user.get('custom_wecom_uid') or user.get('name'): user.get('name') for user in user_map}

		employee_map = frappe.db.get_all(
			'Employee',
			filters={'user_id': ['in', list(user_dict.values())],'status': 'Active'},
			fields=['name', 'user_id', 'department']
		)
		employee_dict = {emp.get('user_id'): emp for emp in employee_map}

		main_deparment_dict = {md.get('name'): md.get('custom_wecom_id') for md in departments}
		reverse_main_deparment_dict = {md.get('custom_wecom_id'): md.get('name') for md in departments}
		# 更新员工的部门
		for user_wecom_id, main_department_wecom_id in all_users_info.items():
			user_name = user_dict.get(user_wecom_id)
			if user_name:
				employee = employee_dict.get(user_name)
				if employee:
					if main_deparment_dict.get(employee.get('department')) != str(main_department_wecom_id):
						dept_name = reverse_main_deparment_dict.get(str(main_department_wecom_id))
						if dept_name:
							employee_doc = frappe.get_cached_doc('Employee', employee.get('name'))
							employee_doc.department = dept_name
							employee_doc.save(ignore_permissions=True)

		frappe.db.commit()
	except Exception as e:
		frappe.log_error(title="Error updating employee departments", message=frappe.get_traceback())
		raise


@frappe.whitelist(allow_guest=True)
def update_employee_department():
	frappe.enqueue(method=handle_update_employee_department, queue="long", timeout=3600, job_name="handle_update_employee_department")


@frappe.whitelist(allow_guest=True)
def send_message_to_wecom(**kwargs):
	users = kwargs.get('users', [])
	access_token = get_access_token()
	url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + access_token
	
	if len(users) == 0:
		employees = frappe.get_all("Employee", 
			fields = ["name", "first_name", "user_id", "department", "reports_to", "bank_name", "custom_chinese_id_number", "bank_ac_no"], 
			filters = {'status': 'Active'}
		)
	else:
		employees = frappe.get_all("Employee", 
			fields = ["name", "first_name", "user_id", "department", "reports_to", "bank_name", "custom_chinese_id_number", "bank_ac_no"], 
			filters = {'status': 'Active', 'user_id': ['in', users]}
		)
	
	for emp in employees:
		user = frappe.get_doc("User", emp.get('user_id'))
		to_user = user.custom_wecom_uid
		leader_name = emp.get('reports_to')
		leader_first_name = ''
		if leader_name:
			leader_first_name = frappe.db.get_value("Employee", filters={'name': leader_name}, fieldname='first_name')
		data = {
			"touser" : str(to_user).replace('.00',''),
			"msgtype" : "template_card",
			"agentid" : 1000008,
			"template_card" : {
				"card_type" : "button_interaction",
				"main_title" : {
					"title" : "关于核实公司数据化建设相关信息的通知",
					"desc" : ""
				},
				"sub_title_text": "为推进公司数据化建设并提升各环节流程效率，我们计划通过身份证号等关键信息实现各系统的互联互通。为确保信息准确无误，请核实以下内容。如发现信息存在错误，请及时反馈，并联系人力资源部柴春燕同事进行修改。\n\n感谢大家的配合与支持！",
				"horizontal_content_list" : [
					{
						"keyname": "姓名",
						"value": emp.get('first_name', '')
					},
					{
						"keyname": "部门",
						"value": emp.get('department', '')
					},
					{
						"keyname": "直属上级",
						"value": leader_first_name
					},
					{
						"keyname": "身份证号",
						"value": emp.get('custom_chinese_id_number', '')
					},
					# {
					# 	"keyname": "银行名称",
					# 	"value": emp.get('bank_name', '')
					# },
					# {
					# 	"keyname": "银行卡号",
					# 	"value": emp.get('bank_ac_no', '')
					# }
				],
				"task_id": str(int(datetime.now().timestamp()*1000)),
				"button_list": [
					{
						"text": "正确",
						"style": 1,
						"key": emp.get('name') + '_1',
					},
					{
						"text": "错误",
						"style": 2,
						"key": emp.get('name') + '_2',
					}
				]
			},
			"enable_id_trans": 0,
			"enable_duplicate_check": 0,
			"duplicate_check_interval": 1800
		}
		resp = requests.post(url, json=data)

