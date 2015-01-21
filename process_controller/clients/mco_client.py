from mcollective import Config, Filter, SimpleRPCAction, Message
from mcollective import rpc
from mcollective import message

from process_controller.common.config import CONF

logger = logging.getLogger(__name__)

class McoClient(object):
    cliet = None

    def __init__(self):
        self.config = Config.from_configfile(CONF.get("MCollective", "CLIENT_CFG"))

    def runonce_puppet(self, id):
        filter = Filter().add_identity(id)
        msg = Message(body='runonce', agent='puppet', config=self.config, filter=filter)
        action = SimpleRPCAction(config=self.config, msg=msg, agent='puppet')
        logger.info(action.call())

    def start_service(self, service_name, id):
        filter = Filter().add_identity(id)
        cmd = "start service=%s"%(service_name)
        msg = Message(body=cmd, agent='service', config=self.config, filter=filter)
        action = SimpleRPCAction(config=self.config, msg=msg, agent='service')
        logger.info(action.call())

    def restart_service(self, service_name, id):
        filter = Filter().add_identity(id)
        cmd = "restart service=%s"%(service_name)
        msg = Message(body=cmd, agent='service', config=self.config, filter=filter)
        action = SimpleRPCAction(config=self.config, msg=msg, agent='service')
        logger.info(action.call())

    def stop_service(self, service_name, id):
        filter = Filter().add_identity(id)
        cmd = "stop service=%s"%(service_name)
        msg = Message(body=cmd, agent='service', config=self.config, filter=filter)
        action = SimpleRPCAction(config=self.config, msg=msg, agent='service')
        logger.info(action.call())