# Copyright (c) 2024, Digitwise Ltd. and contributors
# For license information, please see license.txt

import frappe
import os
from datetime import datetime
import paramiko
import subprocess
from frappe.model.document import Document

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


class RemoteScriptControl(Document):
	@frappe.whitelist()
	def process(self):
		result_of_execution = []
		db_backup_file_path = None
		remote_file_path = '/home/frappe/backup.sql.gz'
		try:
			if self.local_script:
				result_of_execution.append(f'本地脚本开始执行：{datetime.now()}......\n')
				local_sys_commands = str(self.local_script).split('\n')
				for command in local_sys_commands:
					command = command.strip()
					if command and not command.startswith('#'):
						command_args_list = command.split(' ')
						result = subprocess.run(command_args_list, capture_output=True, text=True)
						err = result.stderr
						if err:
							result_of_execution.append(err)
							result_of_execution.append(f'{command} 执行失败......')
							return
	
						result_of_execution.append(result.stdout)
						db_backup_file_path = get_database_backup_file_path(result.stdout)
						if db_backup_file_path:
							result_of_execution.append(f'本地数据库备份文件地址：{db_backup_file_path}')

			if self.remote_script:
				result_of_execution.append(f'远程脚本开始执行：{datetime.now()}......\n')
				client = connect_ssh(self.name)
				
				# 传输备份文件
				if db_backup_file_path:
					send_database_file_to_server(client=client, file_path=db_backup_file_path, remote_path=remote_file_path)
					result_of_execution.append(f'备份文件传输完成：{remote_file_path}......')

				remote_sys_commands = str(self.remote_script).split('\n')
				for command in remote_sys_commands:
					command = command.strip()
					if command and not command.startswith('#'):
						result_of_execution.append(f'{command} 开始执行......')
						stdin, stdout, stderr = client.exec_command(command)

						result_of_execution.append(stdout.read().decode())
						result_of_execution.append(stderr.read().decode())
		
		except Exception as e:
			result_of_execution.append(str(e))
		finally:
			self.result = '\n'.join(result_of_execution)
			self.save()
			if client: 
				client.close()
