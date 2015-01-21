from process_controller.processes import *
import sys
import time

each_check_span = 60
time_out_to_install_os_controller = 1800
time_out_to_install_os_compute_nodes = 1800
puppet_master_ip = CONF.get("PuppetMaster", "host")
        
stage = ['CREATING DEPLOYMENT', 'PREPARING_HOST', 'INSTALLING_CONTROLLER', 'INSTALLING_COMPUTE', 'UPDATING_MONITOR', 'FINISH']

@process_plugin
class OpenStackInstallProcess(object):
    
    '''
    Install OpenStack on bare metal
    '''
    
    @route('/')
    def index():
        return 'The Process Controller APIs.'


    @route('/openstack/deployments')
    def show_deployments():
        deployments_rep = []
        with Connection() as db:
            res = db.os_deployments.find()
        for r in res:
            deployments_rep.append(r)
        return json.dumps(deployments_rep)
    
    
    @route('/openstack/deployments/<deployment_id>')
    def get_deployment(deployment_id):
        with Connection() as db:
            res = db.os_deployments.find_one({'_id': deployment_id})
        return json.dumps(res)
    
    
    @route('/create_os_cluster', methods=['POST'])
    def create_os_cluster():
        logger.info("Create a new OpenStack cluster ...")
        request_obj = json.loads(request.data)
        
        deployment_id = request_obj['parameters']['deployment_id']
        logger.debug("Deployment parameters: " + json.dumps(request_obj))
        
        logger.info("Create an OpenStack deployment ...")
                
        with Connection() as db:
            db.os_deployments.insert({'_id': deployment_id,
                                      'domain_name': request_obj['parameters']['domain_name'],
                                      'controller_ip': request_obj['parameters']['controller_ip'],
                                      'tor_gateway': request_obj['parameters']['tor_gateway'],
                                      'tor_netmask': request_obj['parameters']['tor_netmask'],
                                      'tor_dns': request_obj['parameters']['tor_dns'],
                                      'admin_password': request_obj['parameters']['admin_password'],
                                      'admin_email': request_obj['parameters']['admin_email'],
                                      'monitor_server_ip': request_obj['parameters']['monitor_server_ip'],
                                      'monitor_contacts': request_obj['parameters']['monitor_contacts'],
                                      'ntp_server': request_obj['parameters']['ntp_server'],
                                      'mysql_root_password': request_obj['parameters']['mysql_root_password'],
                                      'rabbitmq_user': request_obj['parameters']['rabbitmq_user'],
                                      'rabbitmq_password': request_obj['parameters']['rabbitmq_password'],
                                      'api_network': request_obj['parameters']['api_network'],
                                      'external_network': request_obj['parameters']['external_network'],
                                      'management_network': request_obj['parameters']['management_network'],
                                      'data_network': request_obj['parameters']['data_network'],
                                      'external_nic': request_obj['parameters']['external_nic'],
                                      'controller_management_address': request_obj['parameters']['controller_management_address'],
                                      'storage_api_address': request_obj['parameters']['storage_api_address'],
                                      'storage_management_address': request_obj['parameters']['storage_management_address'],
                                      'system_disk_partition': request_obj['parameters']['system_disk_partition'],
                                      'status': stage[0]})
            
        #logger.info("Calling kickstart_os_install to install OpenStack ...")
        #call_rule_method("OpenStackInstallProcess", "kickstart_os_install", deployment_id = deployment_id)              
        
        return json.dumps({'deployment_id': deployment_id})
    
    
    @route('/openstack/deployments/<deployment_id>/remove_os_cluster', methods = ['DELETE'])
    def remove_os_cluster(deployment_id):
        logger.info("Remove an OpenStack Deployment")
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
            if deployment is None:
                return json.dumps({'Result': 'Deleted'})
            
            #clear puppet certs
            nodes = deployment.get('nodes_info', [])
            puppet_master = PuppetMasterActionClient(puppet_master_ip)
            for node in nodes:
                puppet_master.clean_cert(node['host_name'])
                
            cluster_name = 'openstack-' + deployment_id
            try:
                #remove monitor cluster
                monitor_servers = db.monitor_servers.find({'monitor_server_ip': deployment['monitor_server_ip']})
                for server in monitor_servers:
                    call_rule_method("MonitorInstallProcess", "remove_openstack_cluster", deployment_id = server['_id'], cluster_name = cluster_name)
            except:
                logger.warning("No monitor server for this openstack cluster")
            finally:
                db.os_deployments.remove({'_id': deployment_id})
                call_rule_method("CommonProcess", "set_process_status", process_class = 'OpenStackInstallProcess', deployment_id = deployment_id, status = 'deleted')
        return json.dumps({'Result': 'Deleted'})
            
    
    @route('/openstack/get-ip/<host_name>', methods = ['POST'])
    def get_ip(host_name):
        deployment_id = host_name.split('-')[-2]
        with Connection() as db:
            deployment = db.os_deployment.find_one({'_id': deployment_id})
        nodes = deployment['nodes_info']
        nodes = filter(lambda x: x['host_name'] == host_name, nodes)
        if len(nodes) == 0:
            return "Host unregistered!"
        elif len(nodes) > 1:
            return "Error, find duplicate hosts!"
        else:
            return nodes[1]['ip_address']

        
    @route('/openstack/puppet_master_ready', methods=['POST'])
    def confirm_puppet_master():
        logger.info("Register Puppet Master node")
        puppet_master_ip = request.form['puppetmaster']
        deployment_id = request.form['deployment_id']
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
            deployment['puppet_master_ip'] = puppet_master_ip

            db.os_deployments.save(deployment)

        return "OK"


    @route('/openstack/register_node/<deployment_id>', methods=['POST'])
    def register_node(deployment_id):
        host_name = request.form['host_name']
        mac = request.form['mac_address']
        logger.info("New nodes registered: "+mac+" "+host_name)
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
            nodes = deployment.get('nodes_info', [])
            nodes.append({'mac_address': mac, 'host_name': host_name})
            deployment['nodes_info'] = nodes
            db.os_deployments.save(deployment)
        return json.dumps(nodes)
        
        
    @route('/openstack/nodes/<deployment_id>')
    def get_nodes_info(deployment_id):
        logger.info("Get registered nodes information...")
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
            nodes = deployment.get('nodes_info', [])
            for node in nodes:
                facts = eval(call_rule_method("OpenStackInstallProcess", "get_facts", certname = node['host_name']))
                node.update(facts)
            deployment['nodes_info'] = nodes
            db.os_deployments.save(deployment)
        return json.dumps(nodes)
    
    
    @route('/openstack/start_install/<deployment_id>/all_status')
    def list_status(deployment_id):
        return json.dumps(stage)
    
    @route('/openstack/start_install/<deployment_id>/status')
    def get_status(deployment_id):
        status = 'UNKNOW'
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
        status = deployment['status']
        return json.dumps({'status': status})
    
    @route('/openstack/start_install/<deployment_id>/status', methods = ['PUT'])
    def set_status(deployment_id, status):
        if status not in stage:
            return str(False)
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
            deployment['status'] = status
            db.os_deployments.save(deployment)
        return json.dumps({'status': status})

    @route('/openstack/check_mco_status')
    def check_mco_status(mco_client, mco_id_rex, registered_nodes):
        logger.info("Loop, check the resources to see if they all connect to MCO")
        total_time = 0
        if_all_install_mco = False
        while not if_all_install_mco:
            logger.info("In loop checking, current total time: %s" % str(total_time))
            node_list, count = mco_client.check_register_servers(mco_id_rex)

            logger.debug("Current service_list: %s" % str(node_list))
            # Check if all the resources connect to MCO
            if node_list.sort() == registered_nodes:
                if_all_install_mco = True

            time.sleep(each_check_span) # Will re-check in 60 seconds.
            total_time += each_check_span
            
        return if_all_install_mco
    
    @route('/openstack/start_install/<deployment_id>', methods=['POST'])
    def kickstart_os_install(deployment_id):
        res = call_rule_method("CommonProcess", "launch_process", process_class = 'OpenStackInstallProcess', deployment_id = deployment_id)
        if res is False:
            logger.error("Another process is running. Installation aborted.")
            return json.dumps({"result": "Aborted"})
        logger.info("Start to install OpenStack ...")
        
        nodes_info = eval(call_rule_method("OpenStackInstallProcess", "get_nodes_info", deployment_id = deployment_id))
        registered_nodes = map(lambda x: x['host_name'], nodes_info).sort()
        
        mco_client = McoSshClient()
        mco_id_rex = "/^openstack-.*-%s-\d*/"%(deployment_id)

        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[1])
        if_all_install_mco = call_rule_method('OpenStackInstallProcess', 'check_mco_status', mco_client = mco_client, mco_id_rex = mco_id_rex, registered_nodes = registered_nodes)
        
        logger.info('Call Puppet to start to install OpenStack components')
        try:
            call_rule_method('OpenStackInstallProcess', 'install_os_controller', deployment_id=deployment_id)
            call_rule_method('OpenStackInstallProcess', 'install_os_computer', deployment_id=deployment_id)
            call_rule_method("OpenStackInstallProcess", "update_monitor", deployment_id = deployment_id)
        finally:
            mco_client.close()
            call_rule_method("CommonProcess", "set_process_status", process_class = 'OpenStackInstallProcess', deployment_id = deployment_id, status = 'complete')
        
        return json.dumps({"result": "Finished"})

    @route('/openstack/add_computers/<deployment_id>', methods=['POST'])
    def add_computers(deployment_id):
        res = call_rule_method("CommonProcess", "launch_process", process_class = 'OpenStackInstallProcess', deployment_id = deployment_id)
        if res is False:
            logger.error("Another process is running. Installation aborted.")
            return json.dumps({"result": "Aborted"})
        logger.info("Start to add new compute nodes ...")
        
        nodes_info = eval(call_rule_method("OpenStackInstallProcess", "get_nodes_info", deployment_id = deployment_id))
        nodes_info = filter(lambda x: x['host_name'].startswith('openstack-compute'), nodes_info)
        registered_nodes = map(lambda x: x['host_name'], nodes_info).sort()
        
        mco_client = McoSshClient()
        mco_id_rex = "/^openstack-compute-%s-\d*/"%(deployment_id)

        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[1])
        if_all_install_mco = call_rule_method('OpenStackInstallProcess', 'check_mco_status', mco_client = mco_client, mco_id_rex = mco_id_rex, registered_nodes = registered_nodes)
        
        logger.info('Call Puppet to start to install OpenStack compute nodes')
        try:
            call_rule_method('OpenStackInstallProcess', 'install_os_computer', deployment_id=deployment_id)
            call_rule_method("OpenStackInstallProcess", "update_monitor", deployment_id = deployment_id)
        finally:
            mco_client.close()
            call_rule_method("CommonProcess", "set_process_status", process_class = 'OpenStackInstallProcess', deployment_id = deployment_id, status = 'complete')
        
        return json.dumps({"result": "Finished"})

    @route('/openstack/start_install/<deployment_id>/controller', methods=['POST'])
    def install_os_controller(deployment_id):
        logger.info("Install OpenStack Controller Server")
        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[2])
        mco_client = McoSshClient()
        
        #Inject OpenStack installation script.
        call_rule_method('OpenStackInstallProcess', 'inject_os_script', deployment_id=deployment_id)
        
        openstack_controller_server_rex = "/^openstack-controller-%s-\d*/"%(deployment_id)
        output, error = mco_client.runonce_puppet(openstack_controller_server_rex)

        if error:
            logger.info("Install OpenStack Controller fail")
            mco_client.close()
            return json.dumps({"result": "Failed"})

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(openstack_controller_server_rex)
        logger.debug("is_running: %s" % str(is_running))
        logger.info("Start to check OpenStack controller installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status(openstack_controller_server_rex)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_os_controller:
                break

        mco_client.close()
        return json.dumps({"result": "Finished"})    


    @route('/openstack/start_install/<deployment_id>/computer', methods=['POST'])
    def install_os_computer(deployment_id):
        logger.info("Install OpenStack Compute Servers")
        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[3])
        mco_client = McoSshClient()
        
        #Inject OpenStack installation script.
        call_rule_method('OpenStackInstallProcess', 'inject_os_script', deployment_id=deployment_id)
        
        openstack_compute_server_rex = "/^openstack-compute-%s-\d*/"%(deployment_id)
        mco_client.runonce_puppet(openstack_compute_server_rex)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(openstack_compute_server_rex)
        logger.debug("is_running: %s" % str(is_running))
        logger.info("Start to check OpenStack compute installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status(openstack_compute_server_rex)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_os_compute_nodes:
                break

        mco_client.close()
        return json.dumps({"result": "Finished"})

        
    @route('/openstack/start_install/<deployment_id>/monitor', methods=['POST'])
    def update_monitor(deployment_id):
        import requests
        logger.info("Update monitor configuration for OpenStack")
        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[4])
        call_rule_method('OpenStackInstallProcess', 'get_nodes_info', deployment_id=deployment_id)
        
        with Connection() as db:
            deployment = db.os_deployments.find_one({'_id': deployment_id})
        
        openstack_hosts = []
        for node in deployment['nodes_info']:
            host_name = node['host_name']
            alias = node['host_name'] + '.' + deployment['domain_name']
            address = node['ip_address']
            
            #get node services from node assigner
            host_role = 'openstack-' + host_name.split('-')[1]
            node_assigner_api = CONF.get('Default','node_assigner_api')
            res = requests.get(node_assigner_api+'/deployment/'+deployment_id+'/roles/'+host_role)
            service_list = res.json()['service_list']
            openstack_hosts.append({'host_name': host_name,
                                    'alias': alias,
                                    'address': address,
                                    'deployments': service_list})
            
        openstack_service_properties = {  'system_disk_partition': deployment['system_disk_partition'],
                                          'os_auth_url': "http://%s:5000/v2.0" % (deployment['controller_ip']),
                                        'os_tenant': 'services',
                                        'os_user': 'monitor',
                                        'os_password': 'xl-#$39skl1d!',
                                        'os_nova_endpoint_url': "http://%s:8774/v2" % (deployment['controller_ip']),
                                        'os_cinder_endpoint_url': "http://%s:8776/v1" % (deployment['controller_ip']),
                                        'os_glance_endpoint_url': "http://%s:9292/v1" % (deployment['controller_ip']),
                                        'os_neutron_endpoint_url': "http://%s:9696/v2.0" % (deployment['controller_ip']),
                                        'os_ceilometer_endpoint_url':"http://%s:8777/v1" % (deployment['controller_ip']),
                                        'os_horizon_endpoint_url': "http://%s/horizon" % (deployment['controller_ip']),
                                        'ganglia_node': deployment['controller_ip'],
                                        'ntp_server': deployment['ntp_server'],
                                        'rabbitmq_user': deployment['rabbitmq_user'],
                                        'rabbitmq_password': deployment['rabbitmq_password'],
                                        'mysql_user': 'root',
                                        'mysql_password': deployment['mysql_root_password'],
                                        }
        openstack_cluster_name = 'openstack-' + deployment_id
        
        os_monitor_hiera_data = {'openstack::hosts': openstack_hosts, 'openstack::properties': openstack_service_properties, 'openstack::cluster::name': openstack_cluster_name}
            
        puppet_master_ip = CONF.get("PuppetMaster", "host")
        puppet_master = PuppetMasterActionClient(puppet_master_ip)
        res = puppet_master.inject_hiera_data('openstack_monitor.json', json.dumps(os_monitor_hiera_data))

        logger.info('Try to update monitor server')
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'monitor_server_ip': deployment.get('monitor_server_ip', '')})
        if monitor_server is not None:
            call_rule_method('MonitorInstallProcess', 'add_openstack_cluster', deployment_id=monitor_server['_id'], cluster_name = openstack_cluster_name, controller_ip = deployment['controller_ip'])
            call_rule_method('MonitorInstallProcess', 'install_monitor_server', deployment_id=monitor_server['_id'])
        else:
            logger.info('Monitor server does not exist')
            
        call_rule_method('OpenStackInstallProcess', 'set_status', deployment_id=deployment_id, status = stage[5])
        return json.dumps({"Result": "Finish update monitor server"})
        
    
    @route('/openstack/facts/<certname>')
    def get_facts(certname):
        logger.info("Call MCO to get facts for %s" % certname)
        mco_client = McoSshClient()
        facts = mco_client.get_os_facts(certname)
        mco_client.close()

        return json.dumps(facts)

    @route('/openstack/mco/status/<resource_id>', methods=['POST'])
    def check_mco_task_status(resource_id):
        mco_client = McoSshClient()
        is_running, status = mco_client.check_running_status(resource_id)
        mco_client.close()

        output = "{is_running: %s, status: %s}" % (str(is_running), str(status))

        return output
    
    @route('/openstack/site.pp')
    def get_install_openstack_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, "install_openstack.pp"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
            
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})
    
    @route('/openstack/<deployment_id>/inject_os_script', methods=['POST'])
    def inject_os_script(deployment_id):
        logger.info("Prepare meta-data and scripts")
        with Connection() as db:
            parameters = db.os_deployments.find_one({'_id': deployment_id})
        
        parameters_dic = {'openstack::controller::address::api': parameters['controller_ip'],
                          'openstack::tor::gateway': parameters['tor_gateway'],
                          'openstack::tor::netmask': parameters['tor_netmask'],
                          'openstack::tor::dns': parameters['tor_dns'],
                          'openstack::keystone::admin_password': parameters['admin_password'],
                          'openstack::keystone::admin_email': parameters['admin_email'],
                          'openstack::mysql::root_password': parameters['mysql_root_password'],
                          'openstack::rabbitmq::user': parameters['rabbitmq_user'],
                          'openstack::rabbitmq::password': parameters['rabbitmq_password'],
                          'openstack::network::api': parameters['api_network'],
                          'openstack::network::external': parameters['external_network'],
                          'openstack::network::management': parameters['management_network'],
                          'openstack::network::data': parameters['data_network'],
                          'openstack::network::external::nic': parameters['external_nic'],
                          'openstack::controller::address::management': parameters['controller_management_address'],
                          'openstack::storage::address::api': parameters['storage_api_address'],
                          'openstack::storage::address::management': parameters['storage_management_address'],
                          'openstack::deployment_name': 'openstack-' + deployment_id,
                          'openstack::udp_recv_channel': [ { 'port': 8649, 'bind': '0.0.0.0' },],
                          'openstack::udp_send_channel': [ { 'host': parameters['controller_ip'], 'port': 8649, 'ttl': 1 },],
                          'openstack::tcp_accept_channel': [ { 'port': 8649 },],
                          'monitor_server_ip': parameters['monitor_server_ip']
        }
        
        os_hiera_data_sample = open(os.path.join(STATIC_FILE_PATH, "openstack_hiera.json.sample"))
        os_hiera_data = json.load(os_hiera_data_sample)
        os_hiera_data.update(parameters_dic)
        os_hiera_data['openstack::mysql::allowed_hosts'].append(parameters['controller_ip'])

        logger.info("Start to inject OpenStack meta-data...")
        
        puppet_master_ip = CONF.get("PuppetMaster", "host")
        puppet_master = PuppetMasterActionClient(puppet_master_ip)
        res = puppet_master.inject_hiera_data('openstack.json', json.dumps(os_hiera_data))

        if res is True:
            logger.debug('OK')
        else:
            logger.error('Inject OpenStack meta-data failed')
            
        logger.info("Copy OpenStack install scripts")
        output = puppet_master.cp_os_script()
        
        logger.debug("Inject return: %s"%(output))

        return json.dumps({'parameters': parameters_dic})


