from process_controller.processes import *

import logging
import sys
import time
import re
import thread

from heatclient.openstack.common.apiclient import base

logger = logging.getLogger(__name__)

STATIC_FILE_PATH = '/opt/orchestrator/process_controller/static'
deployment_id = 2
cf_puppet_master = None
time_out_to_connect_to_mco = int(CONF.get("Default", "connect_timeout"))
port = CONF.get("Default", "port")
ip = CONF.get("Default", "orchestrator_ip")
service_endpoint = "http://%s:%s" % (ip, port)

each_check_span = 60
time_out_to_install_nat = 1800
time_out_to_install_cc = 1800
time_out_to_install_other_components = 5400
time_out_to_install_monitor = 600
stage = ["CREATE_STACK", "INSTALL_MCO", "REGIESTER_NODE", "INSTALL_CF", "INSTALL_MONITOR", "FINISH"]

@process_plugin
class CFInstallProcess(object):
    @route('/')
    def index():
        return 'The Process Controller APIs for install Cloud Foundry.'

    @route('/create_cf_cluster/<project_name>/<stack_name>', methods=['POST'])
    def create_cf_cluster(project_name, stack_name):
        logger.info("Creating Stack for install Cloud Foundry...")
        heat_client = htclient.heat(project_name)
        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name
        request_obj['template_url'] = service_endpoint + "/contrib/CFInstallProcess/cloudfoundry_heat_script/heat.yaml"
        deployment_id = request_obj['parameters']['deployment_id']
        logger.debug("Stack parameters: " + json.dumps(request_obj))

        stack_manager = heat_client.stacks
        stack = stack_manager.create(**request_obj)
        logger.info("Start to create Stack...")

        logger.info("Create a Cloud Foundry Deployment in Database...")
        with Connection() as db:
            db.cf_deployments.insert({'_id': deployment_id, 
                                      'monitor_ip': request_obj['parameters']['monitor_ip'],
                                      'ccdb_type': request_obj['parameters']['ccdb_type'], 
                                      'system_disk_partition': request_obj['parameters']['system_disk_partition'], 
                                      'ntp_server': request_obj['parameters']['ntp_server'], 
                                      'nats_username': request_obj['parameters']['nats_username'], 
                                      'nats_password': request_obj['parameters']['nats_password'], 
                                      'status': stage[0],'stack_name': request_obj['stack_name'], 
                                      'cf_domain': request_obj['parameters']['cf_domain'], 
                                      'uaa_urls': request_obj['parameters']['uaa_urls']})

        call_rule_method("CommonProcess", "create_process", process_class = 'CFInstallProcess', deployment_id = deployment_id)
        
        logger.info("Register external monitor...")
        call_rule_method('CFInstallProcess', 'register_monitor_node', monitor_ip=request_obj['parameters']['monitor_ip'], deployment_id=deployment_id)

        logger.info("Calling kickstart_cf_install to install Cloud Foundry...")
        call_rule_method('CFInstallProcess', 'kickstart_cf_install', deployment_id=deployment_id)
        
        call_rule_method("CommonProcess", "set_process_status", process_class = 'CFInstallProcess', deployment_id = deployment_id, status = 'complete')
        
        return str(deployment_id)

    @route('/add_new_dea/<deployment_id>/<project_name>/<stack_name>', methods=['POST'])
    def append_new_dea(project_name, stack_name, deployment_id):
        logger.info("Add a new DEA to exited deployment...")
        logger.debug("Inject MCO installation script.")
        call_rule_method('CFInstallProcess', 'inject_mco_script', deployment_id=deployment_id)      

        heat_client = htclient.heat(project_name)
        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name
        request_obj['template_url'] = service_endpoint + "/contrib/CFInstallProcess/cloudfoundry_heat_script/%s/heat_new_dea.yaml"%(deployment_id)
        logger.debug(request_obj['template_url'])
        deployment_id = request_obj['parameters']['deployment_id']
        logger.debug("Stack parameters: " + json.dumps(request_obj))
        
        logger.info("Start to add new DEA to deployment: %s" % deployment_id)
        stack_manager = heat_client.stacks
        stack = stack_manager.create(**request_obj)

        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            node_infos = cf_deployment['node_infos']

            max_dea_id = 0
            for node_info in node_infos:
                if re.match(r"^cloud-dea-%s-\d*" % (deployment_id), node_info['hostname']):
                    dea_id = node_info['hostname'].split("-")[-1]
                    logger.debug("DEA ID: %s" % dea_id)
                    if (int(dea_id) > max_dea_id):
                        max_dea_id = int(dea_id)

            new_dea_id = str((max_dea_id+1))
            resource_id = "cloud-dea-%s-%s"%(deployment_id, new_dea_id)
            logger.info("Loop, waiting %s installed MCO..." % resource_id)

            if_install_mco = False
            total_time = 0
            mco_client = McoSshClient()

            while not if_install_mco: 
                server_list, count = mco_client.check_register_servers(resource_id)

                logger.debug("Current service_list: %s" % str(server_list))
                # Check if all the resources connect to MCO
                if 1 == count and resource_id in server_list:
                    if_install_mco = True
                    break

                total_time += each_check_span

                if total_time >= time_out_to_connect_to_mco:
                    break

                time.sleep(each_check_span)

            logger.info("Add %s into database..." % resource_id)
            facts = eval(call_rule_method('CFInstallProcess', "get_facts", certname=resource_id))
            node_infos.append(facts)

            db.cf_deployments.save(cf_deployment)


            logger.info("Start to call Puppet to install a new DEA...")

            logger.debug("Inject Cloud Foundry installation script.")
            call_rule_method('CFInstallProcess', 'inject_cf_script', deployment_id=deployment_id)            
            output, error = mco_client.runonce_puppet(resource_id)

            if error:
                logger.info("Install new DEA Server fail")
                mco_client.close()
                return str(False)

            time.sleep(each_check_span)
            is_running, status = mco_client.check_running_status(resource_id)
            logger.debug("is_running: %s" % str(is_running))
            logger.info("Start to check new DEA installation status")
            total_time = 0
            while is_running:
                is_running, status = mco_client.check_running_status(resource_id)
                logger.debug("is_running inside: %s" % str(is_running))
                time.sleep(each_check_span)
                total_time += each_check_span

                if total_time >= time_out_to_install_other_components:
                    break

            mco_client.close()

            logger.debug("Finally update monitor server, make the new added DEA under monitor.")
            call_rule_method('CFInstallProcess', 'install_monitor', deployment_id=deployment_id)

        return str(True)


    @route('/cloudfoundry_heat_script/heat.yaml', methods=['GET'])
    def get_heat_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, "heat.yaml"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
    
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=heat.yaml"})

    @route('/cloudfoundry_heat_script/<deployment_id>/heat_new_dea.yaml', methods=['GET'])
    def get_new_dea_script(deployment_id):
        file_object = open(os.path.join(STATIC_FILE_PATH, "heat_new_dea.yaml"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()

        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            node_infos = cf_deployment['node_infos']

            max_dea_id = 0
            for node_info in node_infos:
                if re.match(r"^cloud-dea-%s-\d*" % (deployment_id), node_info['hostname']):
                    dea_id = node_info['hostname'].split("-")[-1]
                    logger.debug("DEA ID: %s" % dea_id)
                    if (int(dea_id) > max_dea_id):
                        max_dea_id = int(dea_id)

            new_dea_id = str((max_dea_id+1))
            logger.info("Return a DEA with ID: %s" % new_dea_id)

            all_text = all_text.replace("[^ID^]", new_dea_id).replace("[^puppet_master_ip^] ", cf_deployment['puppet_master_ip'])
    
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=heat_new_dea.yaml"})

    @route('/mco/site.pp', methods=['GET'])
    def get_install_mco_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, "install_mco.pp"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
    
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})

    @route('/cf/site.pp', methods=['GET'])
    def get_install_cf_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, "install_cf.pp"))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
    
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})

    @route('/cloudfoundry/puppet_master_ready', methods=['POST'])
    def confirm_puppet_master():
        logger.info("Register Puppet Master node")
        puppet_master_ip = request.form['puppetmaster']
        deployment_id = request.form['deployment_id']
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            cf_deployment['puppet_master_ip'] = puppet_master_ip

            db.cf_deployments.save(cf_deployment)

        return "OK"

    @route('/cloudfoundry/start_install/<deployment_id>', methods=['POST'])
    def kickstart_cf_install(deployment_id):   
        logger.info("Start to install Cloud Foundry...")

        logger.info("Get all resources created in Heat")
        resources = htclient.get_all_resources_in_heat()

        if_all_install_mco = False
        mco_client = McoSshClient()
        mco_id_rex = "/^cloud-.*-%s-\d*/"%(deployment_id)

        logger.info("Loop, monitor the resources to see if they all connect to MCO")
        total_time = 0
        while not if_all_install_mco:
            logger.info("In loop checking, current total time: %s" % str(total_time))
            server_list, count = mco_client.check_register_servers(mco_id_rex)

            logger.debug("Current service_list: %s" % str(server_list))
            # Check if all the resources connect to MCO
            if len(resources) == count:
                all_in_list = True
                for resource in resources:
                    if resource not in server_list:
                        if_all_install_mco = False
                        break

                if_all_install_mco = all_in_list

            total_time += each_check_span

            if total_time >= time_out_to_connect_to_mco:
                break

            time.sleep(each_check_span) # Will re-check in 60 seconds.

        output = True
        if if_all_install_mco:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                cf_deployment['status'] = stage[1]
                db.cf_deployments.save(cf_deployment)

                node_infos = []
                for server in server_list:
                    facts = eval(call_rule_method('CFInstallProcess', "get_facts", certname=server))

                    if re.match(r"^cloud-nats-%s-\d*" % (deployment_id), server): # is is nats server
                        logger.debug("A nats node")
                        cf_deployment['nats_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-collector-%s-\d*" % (deployment_id), server): # is is collector server
                        logger.debug("A collector node")
                        cf_deployment['collector_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-controller-%s-\d*" % (deployment_id), server): # is is collector server
                        logger.debug("A controller node")
                        cf_deployment['controller_ip'] = facts['ipaddress']

                    node_infos.append(facts)
                    logger.debug("Facts: %s" % str(facts))

                cf_deployment['node_infos'] = node_infos
                cf_deployment['status'] = stage[2]
                db.cf_deployments.save(cf_deployment)

                logger.debug("Inject Cloud Foundry installation script.")
                call_rule_method('CFInstallProcess', 'inject_cf_script', deployment_id=deployment_id)

                logger.info("Call puppet to start to install Cloud Foundry")
                call_rule_method('CFInstallProcess', 'install_nats_server', deployment_id=deployment_id)
                call_rule_method('CFInstallProcess', 'install_controller_server', deployment_id=deployment_id)
                call_rule_method('CFInstallProcess', 'install_other_components', deployment_id=deployment_id)
                call_rule_method('CFInstallProcess', 'install_monitor', deployment_id=deployment_id)

                cf_deployment['status'] = stage[5]
                db.cf_deployments.save(cf_deployment)
        else:
            output = "Timeout"

        mco_client.close()

        return str(output)

    @route('/cloudfoundry/start_install/<deployment_id>/nats', methods=['POST'])
    def install_nats_server(deployment_id):
        logger.info("Install Nats Server")
        mco_client = McoSshClient()
        nats_server_rex = "/^cloud-nats-%s-\d*/"%(deployment_id)
        output, error = mco_client.runonce_puppet(nats_server_rex)

        if error:
            logger.info("Install NATs Server fail")
            mco_client.close()
            return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(nats_server_rex)
        logger.debug("is_running: %s" % str(is_running))
        logger.info("Start to check NATs installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status(nats_server_rex)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_nat:
                break

        mco_client.close()
        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/cc', methods=['POST'])
    def install_controller_server(deployment_id):
        logger.info("Install Cloud Controller Server")
        mco_client = McoSshClient()
        cloud_controller_server_rex = "/^cloud-controller-%s-\d*/"%(deployment_id)
        output, error = mco_client.runonce_puppet(cloud_controller_server_rex)

        if error:
            logger.info("Install Cloud Controller fail")
            mco_client.close()
            return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(cloud_controller_server_rex)
        logger.debug("is_running: %s" % str(is_running))
        logger.info("Start to check Cloud Controller installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status(cloud_controller_server_rex)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_cc:
                break

        mco_client.close()
        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/others', methods=['POST'])
    def install_other_components(deployment_id):
        logger.info("Install other Components")
        outputs = []
        mco_client = McoSshClient()
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            node_infos = cf_deployment['node_infos']
            for node in node_infos:
                certname = node['hostname']
                output, error = mco_client.runonce_puppet(certname)

                outputs.append(output)

        logger.info("Output of running installation: " + str(outputs))
        rex_for_all_component = "/^cloud-.*-%s-\d*/"%(deployment_id)
        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(rex_for_all_component)
        logger.info("Start to check All Cloud Foundry Component installation status")
        total_time = 0
        logger.debug("is_running: %s" % str(is_running))
        while is_running:
            is_running, status = mco_client.check_running_status(rex_for_all_component)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_other_components:
                break

        mco_client.close()
        call_rule_method('CFInstallProcess', 'set_status', deployment_id=deployment_id, status=stage[3])
        return str(True)
    
    @route('/cloudfoundry/start_install/<deployment_id>/monitor', methods=['POST'])
    def install_monitor(deployment_id):
        logger.info("Install or Update Monitor Server")
       # rex_for_monitor = "monitor-%s-0"%(deployment_id)
        rex_for_monitor = "monitor-20-1"
        mco_client = McoSshClient()
        output, error = mco_client.runonce_puppet(rex_for_monitor)

        if error:
            logger.info("Install monitor fail")
            mco_client.close()
            return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status(rex_for_monitor)
        logger.info("Start to check Monitor installation status")
        total_time = 0
        logger.debug("is_running: %s" % str(is_running))
        while is_running:
            is_running, status = mco_client.check_running_status(rex_for_monitor)
            logger.debug("is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_monitor:
                break

        mco_client.close()
        call_rule_method('CFInstallProcess', 'set_status', deployment_id=deployment_id, status=stage[4])
        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/<status>', methods=['PUT'])
    def set_status(deployment_id, status):
        if status not in stage:
            return str(False)

        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            cf_deployment['status'] = status
            db.cf_deployments.save(cf_deployment)

        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/status', methods=['GET'])
    def get_status(deployment_id):
        status = "UNKNOW"
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            status = cf_deployment['status']

        return status

    @route('/cloudfoundry/mco/status/<resource_id>', methods=['POST'])
    def check_mco_task_status(resource_id):
        mco_client = McoSshClient()
        is_running, status = mco_client.check_running_status(resource_id)
        mco_client.close()

        output = "{is_running: %s, status: %s}" % (str(is_running), str(status))

        return output

    @route('/cloudfoundry/<deployment_id>/facts', methods=['GET'])
    def get_deployment_facts(deployment_id):
        facts = ",,,"
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            if cf_deployment.has_key('nats_ip') and cf_deployment.has_key('collector_ip') and cf_deployment.has_key('controller_ip') and cf_deployment.has_key('cf_domain'):
                facts = "%s, %s, %s, %s" % (cf_deployment['nats_ip'], cf_deployment['collector_ip'], cf_deployment['controller_ip'], cf_deployment['cf_domain'])

        return facts

    @route('/cloudfoundry/<deployment_id>/monitor_hosts', methods=['GET'])
    def get_deployment_monitor_hosts(deployment_id):
        facts = "["
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            if cf_deployment.has_key('node_infos'):
                node_infos = cf_deployment['node_infos']
                for one_node_info in node_infos:
                    cf_host_name = one_node_info['hostname']
                    cf_role_name = "-".join(cf_host_name.split("-")[:-2])
                    logger.debug("Role of node: %s" % cf_role_name)

                    role = db.roles.find_one({"role_name": cf_role_name})
                    service_list = map(str,role['service_list'])
                    logger.debug("Service list of %s: %s" % (cf_role_name, service_list))
                    one_line = "{'alias' => '%s', 'host_name' => '%s', 'address' => '%s', 'deployments' => %s}," % (one_node_info['fqdn'], one_node_info['hostname'], one_node_info['ipaddress'], str(service_list))
                    facts += one_line

        return facts + "]"

    @route('/cloudfoundry/<deployment_id>/service_properties', methods=['GET'])
    def get_cloudfoundry_service_properties(deployment_id):
        service_properties = ",,,,,,,,,"
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            if cf_deployment.has_key('nats_ip') and cf_deployment.has_key('collector_ip') and cf_deployment.has_key('controller_ip') and cf_deployment.has_key('node_infos'):
                collector_ip = cf_deployment['collector_ip']
                cf_domain = cf_deployment['cf_domain']
                nats_url = "nats://%s:%s@%s:4222" % (cf_deployment['nats_username'], cf_deployment['nats_password'], cf_deployment['nats_ip'])
                ntp_server = cf_deployment['ntp_server']
                system_disk_partition = cf_deployment['system_disk_partition']
                ccdb_type = cf_deployment['ccdb_type']

                node_infos = cf_deployment['node_infos']
                for one_node_info in node_infos:
                    if re.match(r"^cloud-collector-%s-\d*" % (deployment_id), one_node_info['hostname']): 
                        logger.debug("A collector node")
                        check_node_hostname = one_node_info['hostname']

                    if re.match(r"^cloud-controller-%s-\d*" % (deployment_id), one_node_info['hostname']): # Need to change in v2 version.
                        logger.debug("A Controler node")
                        ccdb_host = one_node_info['ipaddress']

                        ccdb_connection = "host=%s,user=root,passwd=mysql,db=cloud_controller" % (ccdb_host)

                service_properties = "{'check_node_hostname' => '%s', 'check_node' => '%s', 'domain' => '%s', 'ganglia_node'   => '%s', 'nats_url' => '%s', 'ntp_server' => '%s', 'system_disk_partition' =>'%s', 'ccdb_type' => '%s', 'ccdb_host' => '%s', 'ccdb_user' => 'root', 'ccdb_passwd' => 'mysql', 'ccdb_connection' => '%s'}" % (check_node_hostname, collector_ip, cf_domain, collector_ip, nats_url, ntp_server, system_disk_partition, ccdb_type, ccdb_host, ccdb_connection)

        return service_properties  

    @route('/cloudfoundry/<deployment_id>/infos', methods=['GET'])
    def get_deployment_infos(deployment_id):
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})

        return str(cf_deployment)

    @route('/get_facts/<certname>', methods=['POST'])
    def get_facts(certname):
        logger.info("Call MCO to get facts for %s" % certname)
        mco_client = McoSshClient()
        facts = mco_client.get_facts(certname)
        mco_client.close()

        return str(facts)

    @route('/cloudfoundry/<deployment_id>/inject_cf_script', methods=['POST'])
    def inject_cf_script(deployment_id):
        global cf_puppet_master
        if not cf_puppet_master:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                puppet_master_ip = cf_deployment['puppet_master_ip']
                cf_puppet_master = PuppetMasterActionClient(puppet_master_ip)

        logger.info("Start to inject Cloud Foundry install Script")
        output = cf_puppet_master.cp_cf_script()

        logger.debug("Inject return: %s"%(output))

        return output

    @route('/cloudfoundry/<deployment_id>/inject_mco_script', methods=['POST'])
    def inject_mco_script(deployment_id):
        global cf_puppet_master
        if not cf_puppet_master:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                puppet_master_ip = cf_deployment['puppet_master_ip']
                cf_puppet_master = PuppetMasterActionClient(puppet_master_ip)

        logger.info("Start to inject MCO install Script")
        output = cf_puppet_master.cp_mco_script()

        return output

    @route('/cloudfoundry/<deployment_id>/register_monitor_node/<monitor_ip>', methods=['POST'])
    def register_monitor_node(monitor_ip, deployment_id):
        orchestrator_ip = CONF.get("Default", "orchestrator_ip")
        monitor_client = MonitorActionClient(monitor_ip)

        return monitor_client.register(deployment_id, orchestrator_ip)
