import logging
import paramiko, base64
import re

from process_controller.common.config import CONF

logger = logging.getLogger(__name__)

CERT_DIC = "/home/elc/Project/process_controller/process_controller/cert/"

GEN_CERT = "cd "+ CERT_DIC+ "&& python getcert.py -d %s"
READ_CERT = "cat " + CERT_DIC+ "%s"

class CertGenClient:
	def __init__(self):
		self.host = CONF.get("Default", "orchestrator_ip")
		self.username = CONF.get("Default", "username")
		self.password = CONF.get("Default", "password")
		self.client = paramiko.SSHClient()
		self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		logger.info('*** Connecting...')
		logger.info("Host: %s Username: %s Password: %s", self.host, self.username, self.password)
		self.client.connect(str(self.host), 22, self.username, self.password)

	def gen_cert(self, cf_domain):
		output = self._execute(GEN_CERT, "*."+cf_domain)
		return output

	def read_cert(self, cert_name):
		output = self._execute(READ_CERT, cert_name)
		return output

	def _execute(self, cmd_template, *value):
		cmd = cmd_template%(value)
		logger.info('***CMD: %s',cmd)
		stdin, stdout, stderr = self.client.exec_command(cmd, timeout=100)
		stdin.flush()
		stdin.channel.shutdown_write()
		return str(stdout.readline())

	def close(self):
		self.client.close