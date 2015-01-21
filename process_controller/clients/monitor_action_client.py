import logging
import paramiko, base64
import time

from process_controller.common.config import CONF

logger = logging.getLogger(__name__)

REGISTER_SCRIPT = "echo %s > /etc/deployment_id\n"
ADD_HOST = "echo '%s                    orchestrator' >> /etc/hosts\n"
ADD_PUPPETSERVER_HOST = "echo '%s                     puppet-master puppet-master.novalocal puppet-master.openstacklocal' >> /etc/hosts\n"
REMOVE_OLD_PUPPETSERVER_HOST = "sed -i '/puppet-master/d' /etc/hosts\n"
REMOVE_OLD_ORCHESTRATOR_HOST = "sed -i '/orchestrator/d' /etc/hosts\n"
CLEAR_SSL = "rm -rf /var/lib/puppet/ssl\n"

class MonitorActionClient:
    def __init__(self, monitor_ip):
        self.host = monitor_ip
        self.username = CONF.get("MonitorNode", "username")
        self.password = CONF.get("MonitorNode", "password")
        
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info('*** Connecting...')
        logger.info("Host: %s Username: %s Password: %s", self.host, self.username, self.password)
        self.client.connect(str(self.host), 22, self.username, self.password) 


    def register(self, deployment_id, orchestrator_ip):
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
            channel.send(REGISTER_SCRIPT % deployment_id)    
            while not channel.recv_ready():
                logger.info("Set deployment_id...")
                time.sleep(10)
            print channel.recv(1024)    
            channel.send(ADD_HOST % orchestrator_ip)    
            while not channel.recv_ready():
                logger.info("Add HOST...")
                time.sleep(10)
            print channel.recv(1024)  

            output = "Ack"
        except Exception, e:
            logger.info(e)
        finally:
            self.close()

        
        return output
        


    def register_V2(self, deployment_id, orchestrator_ip,puppet_master_ip):
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
            
            channel.send(REGISTER_SCRIPT % deployment_id)    
            while not channel.recv_ready():
                logger.info("Set deployment_id...")
                time.sleep(10)
            print channel.recv(1024)  

            channel.send(REMOVE_OLD_PUPPETSERVER_HOST)    
            while not channel.recv_ready():
                logger.info("Remove old PUPPET SERVER HOST...")
                time.sleep(10)
            print channel.recv(1024)

            channel.send(REMOVE_OLD_ORCHESTRATOR_HOST)    
            while not channel.recv_ready():
                logger.info("Remove old ORCHESTRATOR SERVER HOST...")
                time.sleep(10)
            print channel.recv(1024)

            channel.send(ADD_HOST % orchestrator_ip)    

            while not channel.recv_ready():
                logger.info("Add HOST...")
                time.sleep(10)
            print channel.recv(1024)
            
            channel.send(ADD_PUPPETSERVER_HOST % puppet_master_ip)    
            while not channel.recv_ready():
                logger.info("Add PUPPET SERVER HOST...")
                time.sleep(10)
            print channel.recv(1024)

            channel.send(CLEAR_SSL)    
            while not channel.recv_ready():
                logger.info("CLEAR SSL...")
                time.sleep(10)
            print channel.recv(1024)

            output = "Ack"
        except Exception, e:
            logger.info(e)
        finally:
            self.close()

        return output
        
    def close(self):
        self.client.close