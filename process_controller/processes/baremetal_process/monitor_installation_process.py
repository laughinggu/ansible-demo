from process_controller.processes import *
import time
import sys

each_check_span = 60
time_out_to_install_monitor_server = 3600
time_out_to_connect_to_mco = int(CONF.get("Default", "connect_timeout"))

@process_plugin
class MonitorInstallProcess(object):
    
    '''
    Install monitor server
    '''
    
    @route('/')
    def index():
        return 'The Process Controller APIs for install monitor server.'
    
    
    @route('/create_monitor', methods = ['POST'])
    def create_monitor_server():
        logger.info("Install a new monitor server")
        
        request_obj = json.loads(request.data)
        
        deployment_id = request_obj['server_id']
        
        with Connection() as db:
            db.monitor_servers.insert({'_id': deployment_id,
                                       'nagios_admin_username': request_obj['nagios_admin_username'],
                                       'nagios_admin_password': request_obj['nagios_admin_password'],
                                       'nagios_mail_name': request_obj['nagios_mail_name'],
                                       'monitor_server_ip': request_obj['monitor_server_ip'],
                                       'monitor_server_gateway': request_obj['monitor_server_gateway'],
                                       'monitor_server_netmask': request_obj['monitor_server_netmask'],
                                       'monitor_server_dns': request_obj['monitor_server_dns'],
                                       'ganglia_grid_name': request_obj['ganglia_grid_name'],
                                       'contacts': [],
                                       'ganglia_clusters': [],
                                       'openstack_clusters': [],
                                       'cloudfoundry_clusters': [],
                                       'monitor_openstack': 'False',
                                       'monitor_cloudfoundry': 'False'})
            
        call_rule_method("CommonProcess", "create_process", process_class = 'MonitorInstallProcess', deployment_id = deployment_id)
        call_rule_method("MonitorInstallProcess", "install_monitor_server", deployment_id = deployment_id)
        call_rule_method("CommonProcess", "set_process_status", process_class = 'MonitorInstallProcess', deployment_id = deployment_id, status = 'complete')
        
        return "Finished"    
    
    
    @route('/monitor/start_install/<deployment_id>')
    def install_monitor_server(deployment_id):
        logger.info("Start to install monitor server...")
        logger.info("Loop, check if monitor server has been ready")
        
        mco_client = McoSshClient()
        mco_id_rex = "monitor-%s-\d*"%(deployment_id)

        if_install_mco = False
        logger.info("Loop, check the resources to see if they all connect to MCO")
        total_time = 0
        
        while not if_install_mco:
            logger.info("In loop checking, current total time: %s" % str(total_time))
            node_list, count = mco_client.check_register_servers(mco_id_rex)

            logger.debug("Current service_list: %s" % str(node_list))
            # Check if all the resources connect to MCO
            if count > 0:
                if_install_mco = True
                break

            total_time += each_check_span
            if total_time >= time_out_to_connect_to_mco:
                break
            time.sleep(each_check_span) # Will re-check in 60 seconds.
        
        output = True
        if if_install_mco:
            call_rule_method('MonitorInstallProcess', 'inject_monitor_script', deployment_id=deployment_id)
            logger.info("Call mcollective to start installing monitor server")
            output, error = mco_client.runonce_puppet(mco_id_rex)
            if error:
                logger.info("Install Monitor fail")
                mco_client.close()
                return str(False)

            time.sleep(each_check_span)
            is_running, status = mco_client.check_running_status(mco_id_rex)
            logger.debug("is_running: %s" % str(is_running))
            logger.info("Start to check monitor server installation status")
            total_time = 0
            while is_running:
                is_running, status = mco_client.check_running_status(mco_id_rex)
                logger.debug("is_running inside: %s" % str(is_running))
                time.sleep(each_check_span)
                total_time += each_check_span
                if total_time >= time_out_to_install_monitor_server:
                    return str(False)
        else:
            output = "Timeout"

        mco_client.close()

        return str(output)

    
    @route('/monitor/<deployment_id>/inject_monitor_script', methods=['POST'])
    def inject_monitor_script(deployment_id):
        logger.info("Prepare monitor meta-data and scripts")
        with Connection() as db:
            parameters = db.monitor_servers.find_one({'_id': deployment_id})
            
        monitor_hiera_data = {'_id': deployment_id,
                              'nagios_admin_username': parameters['nagios_admin_username'],
                              'nagios_admin_password': parameters['nagios_admin_password'],
                              'nagios_mail_name': parameters['nagios_mail_name'],
                              'monitor_server_ip': parameters['monitor_server_ip'],
                              'monitor_server_gateway': parameters['monitor_server_gateway'],
                              'monitor_server_netmask': parameters['monitor_server_netmask'],
                              'monitor_server_dns': parameters['monitor_server_dns'],
                              'ganglia_grid_name': parameters['ganglia_grid_name'],
                              'contacts': parameters['contacts'],
                              'ganglia_clusters': parameters['ganglia_clusters'],
                              'monitor_openstack': parameters['monitor_openstack'],
                              'monitor_cloudfoundry': parameters['monitor_cloudfoundry']}
        
        logger.info("Start to inject monitor meta-data...")
        
        puppet_master_ip = CONF.get("PuppetMaster", "host")
        puppet_master = PuppetMasterActionClient(puppet_master_ip)
        res = puppet_master.inject_hiera_data('monitor.json', json.dumps(monitor_hiera_data))

        if res is True:
            logger.debug('OK')
        else:
            logger.error('Inject monitor meta-data failed')
            
        logger.info("Copy monitor install scripts")
        output = puppet_master.cp_monitor_script()
        logger.debug("Inject return: %s"%(output))
        return res


    @route('/monitor/site.pp')
    def get_install_monitor_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, "install_monitor.pp"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
            
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})
    
    
    @route('/monitor/add_openstack_cluster/<deployment_id>', methods = ['POST'])
    def add_openstack_cluster(deployment_id, cluster_name = None, controller_ip = None):
        logger.info('Add a new openstack cluster: %s to monitor server'%(cluster_name))
        if cluster_name is None:
            cluster_name = json.loads(request.data)['cluster_name']
        if controller_ip is None:
            controller_ip = json.loads(request.data)['controller_ip']
        output = False
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            if cluster_name in monitor_server['openstack_clusters']:
                logger.info("%s has been registered to monitor server"%(cluster_name))
            else:
                monitor_server['monitor_openstack'] = 'True'
                monitor_server['ganglia_clusters'].append( {'name': cluster_name, 'address': controller_ip })
                monitor_server['openstack_clusters'].append(cluster_name)
                db.monitor_servers.save(monitor_server)
                output = True
        return output
    
    @route('/monitor/add_cloudfoundry_cluster/<deployment_id>', methods = ['POST'])
    def add_cloudfoundry_cluster(deployment_id, cluster_name = None, collector_ip = None):
        logger.info('Add a new cloudfoundry cluster: %s to monitor server'%(cluster_name))
        if cluster_name is None:
            cluster_name = json.loads(request.data)['cluster_name']
        if collector_ip is None:
            collector_ip = json.loads(request.data)['collector_ip']
        output = False
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            if cluster_name in monitor_server['cloudfoundry_clusters']:
                logger.info("%s has been registered to monitor server"%(cluster_name))
            else:
                monitor_server['monitor_cloudfoundry'] = 'True'
                monitor_server['ganglia_clusters'].append( {'name': cluster_name, 'address': collector_ip })
                monitor_server['cloudfoundry_clusters'].append(cluster_name)
                db.monitor_servers.save(monitor_server)
                output = True
        return output
    
    @route('/monitor/remove_openstack_cluster/<deployment_id>', methods = ['POST'])
    def remove_openstack_cluster(deployment_id, cluster_name = None):
        logger.info('Remove %s from monitor server'%(cluster_name))
        if cluster_name is None:
            cluster_name = json.loads(request.data)['cluster_name']
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            for cluster in monitor_server['ganglia_clusters']:
                if cluster['name'] == cluster_name:
                    monitor_server['ganglia_clusters'].remove(cluster)
            monitor_server['openstack_clusters'].remove(cluster_name)
            if len(monitor_server['openstack_clusters']) < 1:
                monitor_server['monitor_openstack'] = 'False'
            db.monitor_servers.save(monitor_server)
        return
    
    @route('/monitor/remove_cloudfoundry_cluster/<deployment_id>', methods = ['POST'])
    def remove_cloudfoundry_cluster(deployment_id, cluster_name = None ):
        logger.info('Remove %s from monitor server'%(cluster_name))
        if cluster_name is None:
            cluster_name = json.loads(request.data)['cluster_name']
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            for cluster in monitor_server['ganglia_clusters']:
                if cluster['name'] == cluster_name:
                    monitor_server['ganglia_clusters'].remove(cluster)
            monitor_server['cloudfoundry_clusters'].remove(cluster_name)
            if len(monitor_server['cloudfoundry_clusters']) < 1:
                monitor_server['monitor_cloudfoundry'] = 'False'
            db.monitor_servers.save(monitor_server)
        return
            
    @route('/monitor/add_contact/<deployment_id>', methods = ['POST'])
    def add_contact(deployment_id):
        logger.info("Add a monitor contact:")
        request_obj = json.loads(request.data)
        contact = { 'name': request_obj['contact_name'],
                    'email': request_obj['contact_email'],
                    'jobs':  request_obj['jobs'],
                    'cluster_names': request_obj['clusters'] }
        logger.debug(contact)
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            monitor_server['contacts'].append(contact)
            db.monitor_servers.save(monitor_server)
        return
    
    @route('/monitor/remove_contact/<deployment_id>', methods = ['POST'])
    def remove_contact(deployment_id):
        logger.info("Add a monitor contact:")
        request_obj = json.loads(request.data)
        contact = { 'name': request_obj['contact_name'],
                    'email': request_obj['contact_email'],
                    'jobs':  request_obj['jobs'],
                    'cluster_names': request_obj['clusters'] }
        logger.debug(contact)
        with Connection() as db:
            monitor_server = db.monitor_servers.find_one({'_id': deployment_id})
            if contact in monitor_server['contacts']:
                monitor_server['contacts'].remove(contact)
            db.monitor_servers.save(monitor_server)
        return
    
    
    
    
    
    
    
    
    
    
    
    
    
        
