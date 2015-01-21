'''
Created on July 9th, 2013

@author: Layne
'''

import logging
import time

logger = logging.getLogger(__name__)

try:
    from heatclient.v1 import client as heat_client
except ImportError:
    heat_client = None
    logger.info('HeatClient not available')

try:
    from keystoneclient.v2_0 import client as ksclient
except ImportError:
    ksclient = None
    logger.info('KeyStoneClient not available')

from process_controller.common.config import CONF


class HeatClient(object):
    '''
    Convenience class to create and cache client instances.
    '''

    def __init__(self):
        self._heat = {}

    def heat(self, project_name, username=CONF.get("OpenStack", "username"), password=CONF.get("OpenStack", "password"), auth_url=CONF.get("OpenStack", "heat.auth_url"), service_type='orchestration'):
        if self._check_exist_client(self._heat, project_name):
            logger.debug('using existing _heat')
            return self._heat[project_name]

        token, endpoint = self._get_token_and_endpoint(self._heat, project_name, username, password, auth_url, service_type)

        args = {
            'username': username,
            'password': password,
            'endpoint': endpoint,
            'token': token,
            'timeout': 6000
        }
        
        logger.debug('Heat args %s', args)
        
        self._heat = self._create_new_client(self._heat, heat_client.Client(**args), project_name)

        return self._heat[project_name]


    # Here is a mock functions
    def get_all_resources_in_heat(self):
        return ['cloud-uaa-10-0', 'cloud-mysql-10-0', 'cloud-redis-10-0', 'cloud-collector-10-0', 'cloud-controller-10-0', 'cloud-postgresql-10-0', 'cloud-stager-10-0', 'cloud-rabbitmq-10-0', 'cloud-healthmanager-10-0', 'cloud-nats-10-0', 'cloud-vblob-10-0', 'cloud-dea-10-0', 'cloud-mongodb-10-0', 'cloud-router-10-0']
    
    # Here is a mock functions
    def get_all_resources_in_heat_v2(self):
        return ['cloud-syslog-20-0','cloud-haproxy-20-0','cloud-nats-20-0','cloud-uaadb-20-0','cloud-ccdb-20-0','cloud-nfsserver-20-0',
        'cloud-cloudcontroller-20-0','cloud-dea-20-0','cloud-collector-20-0','cloud-console-20-0',
        'cloud-router-20-0','cloud-healthmanager-20-0','cloud-clockglobal-20-0',
        'cloud-cloudcontrollerworker-20-0','cloud-etcd-20-0','cloud-etcd-20-1','cloud-etcd-20-2','cloud-loggregatorserver-20-0',
        'cloud-loggregatortrafficcontroller-20-0','cloud-login-20-0','cloud-uaa-20-0']
    '''    
        # Here is a mock functions
    def get_all_resources_in_heat_v2_layer1(self):
        return ['cloud-syslog-20-0','cloud-haproxy-20-0','cloud-nats-20-0','cloud-uaadb-20-0','cloud-ccdb-20-0','cloud-nfsserver-20-0']    
        # Here is a mock functions
    def get_all_resources_in_heat_v2_layer2(self):
        return ['cloud-etcd-20-0','cloud-etcd-20-1','cloud-etcd-20-2','cloud-collector-20-0','cloud-console-20-0']    
        # Here is a mock functions
    def get_all_resources_in_heat_v2_layer3(self):
        return ['cloud-loggregatorserver-20-0','cloud-loggregatortrafficcontroller-20-0','cloud-healthmanager-20-0']
        # Here is a mock functions
    def get_all_resources_in_heat_v2_layer4(self):
        return ['cloud-login-20-0','cloud-uaa-20-0','cloud-cloudcontroller-20-0','cloud-cloudcontrollerworker-20-0','cloud-dea-20-0','cloud-router-20-0','cloud-clockglobal-20-0'] 
    '''

    def _check_exist_client(self, clients_dict, project_name):
        logger.debug(clients_dict)
        if project_name not in clients_dict:
            logger.debug("Client not existed yet.")
            return False
        else:
            logger.debug("Client has existed.")
            current_time = time.time()
            client_create_time = clients_dict[project_name + "_create_time"]
            if (current_time - client_create_time > 60*60*12): # half day. The token will be expired in one day, our expired time should less than it.
                logger.debug("Client expired.")
                return False
            
            return True
        
    def _create_new_client(self, clients_dict, client, project_name):
        current_time = time.time()
        clients_dict[project_name + "_create_time"] = current_time
        clients_dict[project_name] = client
        
        return clients_dict

    def _get_token_and_endpoint(self, clients_dict, project_name, username, password, auth_url, service_type):
        if (project_name + "_token") not in clients_dict or (project_name + "_endpoint") not in clients_dict:
            logger.debug("Token and endpoint not existed yet.")
            kc_args = {
                'auth_url': auth_url,
                'tenant_name': project_name,
                'username': username,
                'password': password,
            }

            ks_client = ksclient.Client(**kc_args)

            clients_dict[project_name + "_token"] = ks_client.auth_token

            clients_dict[project_name + "_endpoint"] = ks_client.service_catalog.url_for(service_type=service_type, endpoint_type='publicURL')

        return clients_dict[project_name + "_token"], clients_dict[project_name + "_endpoint"]

client = HeatClient()