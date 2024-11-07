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
@frappe.whitelist(allow_guest=True)
def update_apc():
	appKey = "5dc272c4475d4f98bcaae16f3964f24f"
	secretKey = "A397F06CECE490C4AD30F0A1290D2393"
	encode = 'utf-8'
	# 第一次请求获取总条数
	timespan = str(int(time.time()))
	token = appKey + timespan + secretKey;
	hl = hashlib.md5()
	hl.update(token.encode(encoding=encode))
	token = hl.hexdigest().upper();
	reqInterNme = "http://api.qichacha.com/ECICertification/SearchCertification"
	paramStr = "searchKey=山东朱氏药业集团有限公司"
	url = reqInterNme + "?key=" + appKey + "&" + paramStr;
	headers={'Token': token,'Timespan':timespan}
	response = requests.get(url, headers=headers)
	resultJson = json.dumps(str(response.content, encoding = encode))
	resultJson = resultJson.encode(encode).decode("unicode-escape")
	resultJson = json.loads(resultJson[1:-1])
	db_total = frappe.db.count('APC')
	Page = math.ceil(resultJson['Paging']['TotalRecords']/20)
	if resultJson['Paging']['TotalRecords'] > db_total:
		# 分页请求数据信息
		for PageIndex in range(1,Page+1):
			timespan = str(int(time.time()))
			token = appKey + timespan + secretKey;
			hl = hashlib.md5()
			hl.update(token.encode(encoding=encode))
			token = hl.hexdigest().upper();
			reqInterNme = "http://api.qichacha.com/ECICertification/SearchCertification"
			paramStr = "searchKey=山东朱氏药业集团有限公司"+"&PageIndex="+str(PageIndex)+"&PageSize=20"
			url = reqInterNme + "?key=" + appKey + "&" + paramStr;
			headers={'Token': token,'Timespan':timespan}
			response = requests.get(url, headers=headers)
			resultJson = json.dumps(str(response.content, encoding = encode))
			resultJson = resultJson.encode(encode).decode("unicode-escape")
			resultJson = json.loads(resultJson[1:-1])
			for i in range(len(resultJson['Result'])):
				if not frappe.db.exists('APC',resultJson['Result'][i]['No']):
					if not frappe.db.exists('Administrative Permits of Companies Type',resultJson['Result'][i]['TypeDesc']):
						doc = frappe.new_doc('Administrative Permits of Companies Type')
						doc.administrative_permits_of_companies_type_name = resultJson['Result'][i]['TypeDesc']
						doc.insert(ignore_permissions=True)
					doc = frappe.new_doc('APC')
					doc.apc_id = resultJson['Result'][i]['Id']
					doc.apc_name = resultJson['Result'][i]['Name']
					doc.apc_type = resultJson['Result'][i]['Type']
					doc.apc_startdate = resultJson['Result'][i]['StartDate']
					doc.apc_enddate = resultJson['Result'][i]['EndDate']
					doc.apc_no = resultJson['Result'][i]['No']
					doc.apc_typedesc = resultJson['Result'][i]['TypeDesc']
					doc.apc_institutionlist = str(resultJson['Result'][i]['InstitutionList'])[2:-2]
					doc.apc_status = resultJson['Result'][i]['Status']
					certId = resultJson['Result'][i]['Id']
					# 根据Id获取详细信息
					timespan = str(int(time.time()))
					token = appKey + timespan + secretKey;
					hl = hashlib.md5()
					hl.update(token.encode(encoding=encode))
					token = hl.hexdigest().upper();
					reqInterNme = "https://api.qichacha.com/ECICertification/GetCertificationDetailById"
					paramStr = "certId="+certId
					url = reqInterNme + "?key=" + appKey + "&" + paramStr;
					headers={'Token': token,'Timespan':timespan}
					response = requests.get(url, headers=headers)
					resultJson_a = json.dumps(str(response.content, encoding = encode))
					resultJson_a = resultJson_a.encode(encode).decode("unicode-escape")
					resultJson_a = json.loads(resultJson_a[1:-1])
					doc.apc_detailed_information = json.dumps(resultJson_a['Result']['Data'], ensure_ascii=False)
					doc.insert(ignore_permissions=True)
	else:
		pass
