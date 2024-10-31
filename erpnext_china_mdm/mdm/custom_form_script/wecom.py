"""
1、请求企微打卡规则API获取当前企微中存在的规则ID和规则下的员工userid
2、根据1中获取的规则ID获取本地对应规则下的标签ID
3、根据标签ID通过企微标签API获取标签下的所有员工userid
4、判断标签和企微规则中的userid，标签中存在规则中不存则新增，标签中不存在规则中存在则删除
5、返回json格式的响应值
"""
import frappe
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
