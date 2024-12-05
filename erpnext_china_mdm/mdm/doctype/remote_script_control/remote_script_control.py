# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
import os
from datetime import datetime
import frappe.utils
import paramiko
import subprocess
from frappe.model.document import Document
from pathlib import Path

def get_latest_created_file(directory):
	path = Path(directory)
	files = list(path.glob('*.sql.gz'))
	files = [(f, f.stat().st_ctime) for f in files if f.is_file()]
	if not files:
		return None
	latest_file = max(files, key=lambda x: x[1])[0]
	return str(latest_file.absolute())

def get_database_backup_file_path(content: str):
	for line in content.split('\n'):
		if line and 'database.sql.gz' in line:
			for text in line.split(' '):
				if 'database.sql.gz' in text:
					return text

def connect_ssh(name):
	setting = frappe.get_doc("Remote Script Control", name)
	# 创建SSH客户端
	client = paramiko.SSHClient()
	# 自动添加未知的服务器密钥及策略
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	# 连接SSH服务端
	client.connect(setting.host, port=setting.port, username=setting.username, password=setting.password)
	return client


def send_database_file_to_server(client: paramiko.SSHClient, file_path, remote_path):
	# 创建SFTP会话
	sftp = client.open_sftp()
	# 上传文件
	sftp.put(file_path, remote_path)
	sftp.close()

def process_local_script(local_script):
	result_of_execution = []
	result_of_execution.append(f'本地脚本开始执行：{datetime.now()}......')
	local_sys_commands = str(local_script).split('\n')
	for command in local_sys_commands:
		command = command.strip()
		if command and not command.startswith('#'):
			command_args_list = command.split(' ')
			result = subprocess.run(command_args_list, capture_output=True, text=True)
			err = result.stderr
			if err:
				result_of_execution.append(err)
				result_of_execution.append(f'{command} 执行失败......')
				return result_of_execution

			result_of_execution.append(result.stdout)
	result_of_execution.append(f'本地脚本执行完成：{datetime.now()}......\n')
	return result_of_execution

def send_db_file(client, remote_file_path):
	result_of_execution = []
	
	backups_path = frappe.utils.get_bench_relative_path(frappe.utils.get_backups_path())
	db_path = get_latest_created_file(backups_path)
	if not db_path:
		result_of_execution.append(f'没有最新的数据库文件可以传输')
		return
	result_of_execution.append(f'数据库文件开始传输：{datetime.now()}......')
	send_database_file_to_server(client=client, file_path=db_path, remote_path=remote_file_path)
	result_of_execution.append(f'数据库文件传输完成：{datetime.now()}......\n')
	return result_of_execution


def process_remote_script(client: paramiko.SSHClient, remote_script):
	result_of_execution = []
	result_of_execution.append(f'远程脚本开始执行：{datetime.now()}......')
	
	remote_sys_commands = str(remote_script).split('\n')
	for command in remote_sys_commands:
		command = command.strip()
		if command and not command.startswith('#'):
			result_of_execution.append(f'{command} 开始执行......')
	
			stdin, stdout, stderr = client.exec_command(f"bash -ic '{command}'", get_pty=True)
			# stdout = channel.send(f"{command}\n")
			result_of_execution.append(stdout.read().decode())
			result_of_execution.append(stderr.read().decode())
	result_of_execution.append(f'远程脚本执行完成：{datetime.now()}......\n')
	return result_of_execution

def background_job(local_script, name, check_send_file, remote_file_path, remote_script):
	result_of_execution = []
	client = None
	try:
		if local_script:
			result_of_execution += process_local_script(local_script)
		
		client = connect_ssh(name)
		if check_send_file:
			result_of_execution += send_db_file(client, remote_file_path)
		
		if remote_script:
			result_of_execution += process_remote_script(client, remote_script)
	
	except Exception as e:
		result_of_execution.append(str(e))
	finally:
		doc = frappe.get_doc('Remote Script Control', name)
		doc.result = '\n'.join(result_of_execution)
		doc.save()
		if client: 
			client.close()


class RemoteScriptControl(Document):
	@frappe.whitelist()
	def process(self):
		# background_job(self.local_script, self.name, self.send_db_file, self.remote_file_path, self.remote_script)
		frappe.enqueue(
			background_job,
			timeout=3600,
			local_script=self.local_script, 
			name=self.name, 
			check_send_file=self.send_db_file, 
			remote_file_path=self.remote_file_path, 
			remote_script=self.remote_script
		)
		self.update({
			'result': '正在执行中......'
		})
		self.save()
