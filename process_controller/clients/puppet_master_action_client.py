import logging
import os
import paramiko, base64

from process_controller.common.config import CONF, PUPPET_HIERA_PATH

logger = logging.getLogger(__name__)

CLEAN_CERT = "/usr/bin/puppet cert clean %s"

CP_CF_SCRIPT = "/usr/bin/curl %s/contrib/CFV2InstallProcess/cf/site.pp > /etc/puppet/manifests/site.pp"

CP_MCO_SCRIPT = "/usr/bin/curl %s/contrib/CFV2InstallProcess/mco/site.pp > /etc/puppet/manifests/site.pp"

CP_CFV2_MONITOR_SCRIPT = "/usr/bin/curl %s/contrib/CFV2InstallProcess/monitor/site.pp > /etc/puppet/manifests/site.pp"

CP_CF_WITH_EXTERNAL_MONITOR_SCRIPT = "/usr/bin/curl %s/contrib/CFV2InstallProcess/cfwithexternalmonitor/site.pp > /etc/puppet/manifests/site.pp"

CP_OS_SCRIPT = "/usr/bin/curl %s/contrib/OpenStackInstallProcess/openstack/site.pp > /etc/puppet/manifests/site.pp"

CP_MONITOR_SCRIPT = "/usr/bin/curl %s/contrib/MonitorInstallProcess/monitor/site.pp > /etc/puppet/manifests/site.pp"


class PuppetMasterActionClient:
    def __init__(self, puppet_master_ip):
        self.host = puppet_master_ip
        self.username = CONF.get("PuppetMaster", "username")
        self.password = CONF.get("PuppetMaster", "password")
        
        port = CONF.get("Default", "port")
        ip = CONF.get("Default", "orchestrator_ip")
        self.service_endpoint = "http://%s:%s" % (ip, port) #Process Controller Endpoint
        
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info('*** Connecting...')
        logger.info("Host: %s Username: %s Password: %s", self.host, self.username, self.password)
        self.client.connect(str(self.host), 22, self.username, self.password)
        
        self.t = paramiko.Transport((self.host, 22))
        self.t.connect(username = self.username, password = self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.t) 

    def cp_cf_script(self):
        output,err = self._execute(CP_CF_SCRIPT, self.service_endpoint)
        self.close()
        return output

    def cp_mco_script(self):
        output,err = self._execute(CP_MCO_SCRIPT, self.service_endpoint)
        self.close()
        return output
    
    def cp_os_script(self):
        output,err = self._execute(CP_OS_SCRIPT, self.service_endpoint)
        self.close()
        return output
    
    def cp_monitor_script(self):
        output,err = self._execute(CP_MONITOR_SCRIPT, self.service_endpoint)
        self.close()
        return output
    
    def inject_hiera_data(self, file_name, data):
        try:
            hiera_data_file = open(os.path.join('/tmp', file_name), 'w')
            hiera_data_file.write(str(data))
            hiera_data_file.close()
            self.sftp.put(os.path.join('/tmp', file_name), os.path.join(PUPPET_HIERA_PATH, file_name))
            return True
        except:
            return False

    def cp_cfv2_monitor_script(self):
        output,err = self._execute(CP_CFV2_MONITOR_SCRIPT, self.service_endpoint)
        self.close()
        return output 

    def cp_cf_with_external_monitor_script(self):
        output,err = self._execute(CP_CF_WITH_EXTERNAL_MONITOR_SCRIPT, self.service_endpoint)
        self.close()
        return output    

    def clean_cert(self, certname):
        output,err = self._execute(CLEAN_CERT, certname)
        self.close()
        return output
        
    def _execute(self, cmd_template, *value):
        cmd = cmd_template%(value)
        logger.debug("CMD: %s" % cmd)
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=100)
        stdin.flush()
        stdin.channel.shutdown_write()

        return stdout.read(), stderr.read()
        
    def close(self):
        self.t.close()
        self.client.close()


