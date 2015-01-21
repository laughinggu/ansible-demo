import logging
import paramiko, base64
import re

from process_controller.db.connection import Connection
from process_controller.common.config import CONF, STATIC_FILE_PATH

logger = logging.getLogger(__name__)

RUNONCE_PUPPET = "mco puppet runonce -I /^%s/"
START_SERVICE = "mco rpc service start service=%s -I /^%s/"
STOP_SERVICE = "mco rpc service stop service=%s -I /^%s/"
RESTART_SERVICE = "mco rpc service restart service=%s -I /^%s/"
CHECK_REGISTER_SERVERS = "mco ping -I /^%s/"
GET_FACTS = "mco inventory facts -I /%s/ --script %s/facts_inventory.mc"
GET_OS_FACTS = "mco inventory facts -I /%s/ --script %s/os_facts_inventory.mc"
CHECK_RUNNING_STATUS = "mco puppet status -I %s"

class McoSshClient:
    def __init__(self, id = None):
        if id is not None:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': id})
                mco_client_ip = cf_deployment['mco_client_ip']
                mco_client_username = cf_deployment['mco_client_username']
                mco_client_password = cf_deployment['mco_client_password']

        if (id is None) or (mco_client_ip =='') or (mco_client_username =='') or (mco_client_password==''):
            self.host = CONF.get("MCollective", "MCO_CLIENT")
            self.username = CONF.get("MCollective", "MCO_CLIENT_USERNAME")
            self.password = CONF.get("MCollective", "MCO_CLIENT_PWD")
        else:
            self.host = mco_client_ip
            self.username = mco_client_username
            self.password = mco_client_password
         
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info('*** Connecting...')
        logger.info("Host: %s Username: %s Password: %s", self.host, self.username, self.password)
        self.client.connect(str(self.host), 22, self.username, self.password) 

    def runonce_puppet(self, id):
        output = self._execute(RUNONCE_PUPPET, id)
        return output

    def start_service(self, service_name, id):
        output = self._execute(START_SERVICE, service_name, id)
        return output

    def restart_service(self, service_name, id):
        output = self._execute(RESTART_SERVICE, service_name, id)
        return output

    def stop_service(self, service_name, id):
        output = self._execute(STOP_SERVICE, service_name, id)
        return output

    def check_register_servers(self, id):
        output, err = self._execute(CHECK_REGISTER_SERVERS, id)
        return self._parse_check_register_servers(output)

    def get_facts(self, id):
        logger.debug("Getting facts for %s" % id)
        output, err = self._execute(GET_FACTS, id, STATIC_FILE_PATH)

        return self._parse_facts_output(output)
    
    def get_os_facts(self, id):
        logger.debug("Getting facts for %s" % id)
        output, err = self._execute(GET_OS_FACTS, id, STATIC_FILE_PATH)
        return self._parse_os_facts_output(output)

    def check_running_status(self, id):
        output, err = self._execute(CHECK_RUNNING_STATUS, id)

        return self._parse_check_running_status(id, output)
        
    def _execute(self, cmd_template, *value):
        cmd = cmd_template%(value)
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=100)
        stdin.flush()
        stdin.channel.shutdown_write()

        return stdout.read(), stderr.read()

    def _parse_facts_output(self, output):
        output = output.strip('\n')
        logger.debug("Parsing facts: %s" % output)
        fields = output.split(",")
        logger.debug("Fields: %s" % str(fields))
        facts_dict_return = {
            "id": fields[0],
            "hostname": fields[1],
            "ipaddress": fields[2],
            "cf_domain": fields[3],
            "cf_uaa_urislogin": fields[4],
            "cf_uaa_urisuaa": fields[5],
            "fqdn": fields[6],
            "operatingsystemrelease ": fields[7]
        }

        return facts_dict_return
    
    def _parse_os_facts_output(self, output):
        output = output.strip('\n')
        logger.debug("Parsing facts: %s" % output)
        fields = output.split(",")
        logger.debug("Fields: %s" % str(fields))
        if fields[0] == 'No request sent':
            facts_dict_return = {
                "ip_address": 'Unknown',
            }
        else:
            facts_dict_return = {
                "ip_address": fields[0],
            }
        return facts_dict_return

    def _parse_check_register_servers(self, output):
        servers = []
        count = 0
        lines = output.splitlines(False)
        for line in lines:
            line_dessemble = line.split()
            if len(line_dessemble) > 0:

                if line_dessemble[0].startswith("cloud-"):
                    servers.append(line_dessemble[0])

                if re.match(r"\d+$", line_dessemble[0]):
                    count = line_dessemble[0]

        return servers, int(count)

    def _parse_check_running_status(self, id, output):
        lines = output.splitlines(False)

        is_running = True
        running_status = []
        for line in lines:
            if re.match(r".*Currently applying a catalog;.*", line):
                running_status.append("True")

            if re.match(r".*Currently stopped;.*", line):
                running_status.append("False")

        if_not_running = True
        for status in running_status:
            if_not_running = if_not_running and (not eval(status))
        
        is_running = (not if_not_running) and len(running_status) > 0

        logger.info("**id %s , running_status_len: %s",id,len(running_status))

        return is_running, running_status


    def runonce_puppet_batch(self, ids):
        outputs = []
        errors = []
        for id in ids:
            output,error = self._execute(RUNONCE_PUPPET, id)
            # logger.info("**id %s , error: %s",id,error)
            outputs.append(output)
            errors.append(error)
        return outputs,errors


    def check_running_status_batch(self, ids):
        layer_is_running = True
        layer_status = []
        node_num = len(ids)
        not_running_node_num = 0

        for id in ids:
            output, err = self._execute(CHECK_RUNNING_STATUS, id)
            is_running, status = self._parse_check_running_status(id, output)
            logger.info("**id %s , is_running: %s",id,is_running)
            layer_status = layer_status + status
            if not is_running:
                not_running_node_num = not_running_node_num + 1

        if not_running_node_num == node_num:
            layer_is_running = False

        return layer_is_running, layer_status  

        
    def close(self):
        self.client.close




