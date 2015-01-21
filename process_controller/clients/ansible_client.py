import logging
import paramiko, base64
import re
import time

from process_controller.common.config import CONF

logger = logging.getLogger(__name__)


ANSIBLE_DIC = "/home/elc/Project/process_controller/process_controller/ansible_demo/"
PLAY_ANSIBLE = "cd "+ ANSIBLE_DIC+ "&& ansible-playbook ./playbook.yml -vvvv -e \"deployment_id=%s\""
PING_CMD = "ansible all -a \"/bin/echo hello >/tmp/ansible_test\" -vvvv"
SETUP_ENV = "export ANSIBLE_HOST_KEY_CHECKING=False"
SETUP_HOSTS ="export ANSIBLE_HOSTS="+ANSIBLE_DIC+"ansible_hosts"
CP_HOSTS = "cp "+ANSIBLE_DIC+"ansible_hosts /etc/ansible/hosts"
CD_CMD = "cd "+ ANSIBLE_DIC+ "&& ls"


class AnsibleClient:
	def __init__(self):
		self.host = CONF.get("Default", "orchestrator_ip")
		self.username = CONF.get("Default", "username")
		self.password = CONF.get("Default", "password")
		self.client = paramiko.SSHClient()
		self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		logger.info('*** Connecting Ansible Client...')
		logger.info("Host: %s Username: %s Password: %s", self.host, self.username, self.password)
		self.client.connect(str(self.host), 22, self.username, self.password)

	def setup_ansible(self):
		output = "Fail"

		try:
			channel = self.client.invoke_shell()
			
			channel.send("sudo -s\n")
			while not channel.recv_ready():    
				logger.info("Waiting get ROOT...")  
				time.sleep(2)    
			logger.debug("GET ROOT: " + channel.recv(1024))  
			
			channel.send("%s\n" % self.password)    
			while not channel.recv_ready():    
				logger.info("Authenticating...")
				time.sleep(2)
			logger.debug("GET ROOT: " + channel.recv(1024))  
			
			channel.send(SETUP_ENV+"\n")    
			while not channel.recv_ready():    
				logger.info("Waiting SETUP_ENV...")  
				time.sleep(2)    
			logger.debug("setup: " + channel.recv(1024))  
			
			channel.send(SETUP_HOSTS+"\n")    
			while not channel.recv_ready():    
				logger.info("Waiting SETUP_ANSIBLE_HOSTS...")  
				time.sleep(2)   
			logger.debug("SETUP_HOSTS: " + channel.recv(1024))  
			
			channel.send(CP_HOSTS+"\n")    
			while not channel.recv_ready():    
				logger.info("Waiting CP_HANSIBLE_OSTS...")   
				time.sleep(2)   
			logger.debug("CP_HOSTS: " + channel.recv(1024))  

			output = "Ack"
		except Exception, e:
			logger.info(e)
		finally:
			self.close()
		return output


	def cd_ansible(self):
		cmd = CD_CMD
		output = self._execute(cmd)
		return output

	def play_ansible(self, deployment_id):
		cmd = PLAY_ANSIBLE%(deployment_id)
		output = self._execute(cmd)
		return output

	def ansible_ping(self):
		output = self._execute(PING_CMD)
		logger.info('***OUTPUT: %s',output)
		return output

	def _execute(self, cmd):
		logger.info('***CMD: %s',cmd)
		stdin, stdout, stderr = self.client.exec_command(cmd, timeout=500)
		
		stdin.flush()
		stdin.channel.shutdown_write()
		output = ''
		while True:
			line = str(stdout.readline())
			output += line
			if line =='':
				break
		return output

	# def ansible_ping(self):
	# 	output = "Fail"

	# 	try:
	# 		channel = self.client.invoke_shell()
	# 		channel.send(PING_CMD+"\n")    
	# 		while not channel.recv_ready():    
	# 			logger.info("Waiting ping...")  
	# 			time.sleep(10)    
	# 			logger.debug("ping: " + channel.recv(20))  
	# 		while not channel.recv_ready():
	# 			logger.info("Ready...")
	# 			time.sleep(10)
	# 		output = "Ack"
	# 	except Exception, e:
	# 		logger.info(e)
	# 	finally:
	# 		self.close()
	# 	return output

	def close(self):
		self.client.close