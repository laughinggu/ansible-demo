from process_controller.processes import *

import logging
import sys
import time
import re
import thread


from heatclient.openstack.common.apiclient import base

logger = logging.getLogger(__name__)
STATIC_FILE_PATH = '/opt/orchestrator/process_controller/static'

cf_puppet_master = None
time_out_to_connect_to_mco = int(CONF.get("Default", "connect_timeout"))
port = CONF.get("Default", "port")
ip = CONF.get("Default", "orchestrator_ip")
service_endpoint = "http://%s:%s" % (ip, port)

each_check_span = 60
time_out_to_install_other_components = 5400
time_out_to_install_monitor = 600

time_out_to_install_layer = 7200

external_monitor = False
stage = ["CREATE_STACK", "INSTALL_MCO", "REGIESTER_NODE", "INSTALL_CF", "INSTALL_MONITOR", "FINISH"]

@process_plugin
class CFV2InstallProcess(object):
    @route('/')
    def index():
        return 'The Process Controller APIs for install Cloud Foundry Version 2.'

    @route('/cloudfoundry_heat_script/heatv2_nova.yaml', methods=['GET'])
    def get_heat_nova_script():
        dea_count = int(request.args.get('dea_count', 1))
        content = find_template('heatv2_nova.yaml').render(dea_count=dea_count)
        return Response(content, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=heatv2_nova.yaml"})

    @route('/cloudfoundry_heat_script/heatv2_neutron.yaml', methods=['GET'])
    def get_heat_neutron_script():
        dea_count = int(request.args.get('dea_count', 1))
        router_count = int(request.args.get('router_count', 1))
        content = find_template('heatv2_neutron.yaml').render(dea_count=dea_count, router_count=router_count)
        return Response(content, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=heatv2_neutron.yaml"})

    @route('/create_cf_cluster/<project_name>/<stack_name>', methods=['POST'])
    def create_cf_cluster(project_name, stack_name):
        logger.info("~~Heat is careating Stack for install Cloud Foundry V2...")

        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name

        heat_client_parameters = {}
        if request_obj['parameters'].has_key('openstack_username'):
            heat_client_parameters['username'] = request_obj['parameters']['openstack_username']
        if request_obj['parameters'].has_key('openstack_password'):
            heat_client_parameters['password'] = request_obj['parameters']['openstack_password']
        if request_obj['parameters'].has_key('heat_auth_url'):
            heat_client_parameters['auth_url'] = request_obj['parameters']['heat_auth_url']

        heat_client = htclient.heat(project_name, **heat_client_parameters)
        is_Neutron = request_obj['parameters']['neutron']
        logger.info("Whether with neutron:" + str(is_Neutron))

        if(is_Neutron == 'true'):
            request_obj['template_url'] = service_endpoint + "/contrib/CFV2InstallProcess/cloudfoundry_heat_script/heatv2_neutron.yaml"
        else:
            request_obj['template_url'] = service_endpoint + "/contrib/CFV2InstallProcess/cloudfoundry_heat_script/heatv2_nova.yaml"

        deployment_id = request_obj['parameters']['deployment_id']
        logger.debug("Stack parameters: " + json.dumps(request_obj))
        stack_manager = heat_client.stacks
        stack = stack_manager.create(**request_obj)
        logger.info("Start to create Stack...")

        logger.info("Create a Cloud Foundry V2 Deployment in Database...")

        with Connection() as db:
            db.cf_deployments.insert({'_id': deployment_id, 'monitor_ip': request_obj['parameters']['monitor_ip'],'ccdb_type': request_obj['parameters']['ccdb_type'], 'system_disk_partition': request_obj['parameters']['system_disk_partition'], 'ntp_server': request_obj['parameters']['ntp_server'], 'nats_username': request_obj['parameters']['nats_username'], 'nats_password': request_obj['parameters']['nats_password'], 'status': stage[0],
                'stack_name': request_obj['stack_name'], 'cf_domain': request_obj['parameters']['cf_domain'], 'uaa_urls': request_obj['parameters']['uaa_urls'],'nfs_server_network':request_obj['parameters']['nfs_server_network'],'nagios_server_ip':request_obj['parameters']['nagios_server_ip']
                ,'mco_client_ip':request_obj['parameters']['mco_client_ip'],'mco_client_username':request_obj['parameters']['mco_client_username'],'mco_client_password':request_obj['parameters']['mco_client_password']
                ,'external_net_ip':request_obj['parameters']['public_net_id'],'neutron':request_obj['parameters']['neutron'],'ftp_host':request_obj['parameters']['ftp_host'],'orchestrator_ip':request_obj['parameters']['orchestrator_ip']})

        call_rule_method('CFV2InstallProcess', 'set_status', deployment_id=deployment_id, status=stage[0])
        logger.info("Generate Certifications...")
        call_rule_method('CFV2InstallProcess', 'set_status', deployment_id=deployment_id, status=stage[1])
        call_rule_method('CFV2InstallProcess', 'generate_cert', cf_domain=request_obj['parameters']['cf_domain'], deployment_id=deployment_id)

        logger.info("Calling kickstart_cf_install to install Cloud Foundry...")
        call_rule_method('CFV2InstallProcess', 'kickstart_cf_install', deployment_id=deployment_id)

        return str(deployment_id)

    @route('/create_cf_cluster_ansible/<project_name>/<stack_name>', methods=['POST'])
    def create_cf_cluster_ansible(project_name, stack_name):
        logger.info("~~Ansible is creating Stack for install Cloud Foundry V2...")

        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name
        request_obj['template_url'] = service_endpoint + "/contrib/CFV2InstallProcess/cloudfoundry_heat_script/heatv2.yaml"
        deployment_id = request_obj['parameters']['deployment_id']
        logger.debug("Stack parameters: " + json.dumps(request_obj))

        logger.info("Create a Cloud Foundry V2 Deployment in Database...")

        with Connection() as db:
            db.cf_deployments.insert({'_id': deployment_id, 'monitor_ip': request_obj['parameters']['monitor_ip'],'ccdb_type': request_obj['parameters']['ccdb_type'], 'system_disk_partition': request_obj['parameters']['system_disk_partition'], 'ntp_server': request_obj['parameters']['ntp_server'], 'nats_username': request_obj['parameters']['nats_username'], 'nats_password': request_obj['parameters']['nats_password'], 'status': stage[0],'stack_name': request_obj['stack_name'], 'cf_domain': request_obj['parameters']['cf_domain'], 'uaa_urls': request_obj['parameters']['uaa_urls'],'nfs_server_network':request_obj['parameters']['nfs_server_network'],'collector_floating_ip':request_obj['parameters']['collector_floating_ip']})

        logger.info("Play Ansible...")
        ansilbe_client = AnsibleClient()
        ansilbe_client.play_ansible(deployment_id)

        call_rule_method('CFV2InstallProcess', 'set_status', deployment_id=deployment_id, status=stage[0])
        logger.info("Generate Certifications...")
        call_rule_method('CFV2InstallProcess', 'generate_cert', cf_domain=request_obj['parameters']['cf_domain'], deployment_id=deployment_id)

        logger.info("Calling kickstart_cf_install to install Cloud Foundry...")
        call_rule_method('CFV2InstallProcess', 'kickstart_cf_install', deployment_id=deployment_id)

        ansilbe_client.close()

        return str(deployment_id)


    @route('/mco/site.pp', methods=['GET'])
    def get_install_mco_script():
        file_object = open(os.path.join(STATIC_FILE_PATH,'install_mco.pp'))
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

    @route('/cloudfoundry/<deployment_id>/register_monitor_node/<monitor_ip>', methods=['POST'])
    def register_monitor_node(monitor_ip, deployment_id):
        orchestrator_ip = CONF.get("Default", "orchestrator_ip")
        monitor_client = MonitorActionClient(monitor_ip)
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            puppet_master_ip = cf_deployment['puppet_master_ip']

        return monitor_client.register_V2(deployment_id, orchestrator_ip,puppet_master_ip)

    @route('/cloudfoundry/start_install/<deployment_id>', methods=['POST'])
    def kickstart_cf_install(deployment_id):
        logger.info("Start to install Cloud Foundry V2...")
        logger.info("Get all resources created in Heat V2")
        resources = htclient.get_all_resources_in_heat_v2()

        if_all_install_mco = False
        mco_client = McoSshClient(deployment_id)
        mco_id_rex = "/^cloud-.*-%s-\d*/"%(deployment_id)

        logger.info("Loop, monitor the reource to see if they all connect to MCO")
        total_time = 0
        while not if_all_install_mco:
            logger.info("In loop checking, current total time: %s" % str(total_time))
            server_list, count = mco_client.check_register_servers(mco_id_rex)

            logger.debug("Current service_list: %s " %str(server_list))

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
                    facts = eval(call_rule_method('CFV2InstallProcess', "get_facts", deployment_id=deployment_id,certname=server))
                    logger.debug("Server: %s" % str(server))

                    if re.match(r"^cloud-ccdb-%s-\d*" % (deployment_id), server):
                        logger.debug("A ccdb node")
                        cf_deployment['ccdb_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-uaadb-%s-\d*" % (deployment_id), server):
                        logger.debug("A uaadb node")
                        cf_deployment['uaadb_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-syslog-%s-\d*" % (deployment_id), server):
                        logger.debug("A syslog node")
                        cf_deployment['syslog_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-nfsserver-%s-\d*" % (deployment_id), server):
                        logger.debug("A nfsserver node")
                        cf_deployment['nfs_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-nats-%s-\d*" % (deployment_id), server):
                        logger.debug("A nats node")
                        cf_deployment['nats_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-etcd-%s-0" % (deployment_id), server):
                        logger.debug("A etcd0 node")
                        cf_deployment['etcd0_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-etcd-%s-1" % (deployment_id), server):
                        logger.debug("A etcd1 node")
                        cf_deployment['etcd1_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-etcd-%s-2" % (deployment_id), server):
                        logger.debug("A etcd2 node")
                        cf_deployment['etcd2_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-router-%s-\d*" % (deployment_id), server):
                        logger.debug("A router node")
                        cf_deployment['router_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-loggregatorserver-%s-\d*" % (deployment_id), server):
                        logger.debug("A loggregatorserver node")
                        cf_deployment['loggregator_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-loggregatortrafficcontroller-%s-\d*" % (deployment_id), server):
                        logger.debug("A loggregatortrafficcontroller node")
                        cf_deployment['loggregator_endpoint_ip'] = facts['ipaddress']

                    if re.match(r"^cloud-collector-%s-\d*" % (deployment_id), server):
                        logger.debug("A collector node")
                        cf_deployment['collector_ip'] = facts['ipaddress']
                        cf_deployment['collector_hostname'] = facts['hostname']

                    if re.match(r"^cloud-console-%s-\d*" % (deployment_id), server):
                        logger.debug("A console node")
                        cf_deployment['console_ip'] = facts['ipaddress']

                    node_infos.append(facts)
                    logger.debug("Facts: %s" % str(facts))

                cf_deployment['node_infos'] = node_infos
                cf_deployment['status'] = stage[2]
                db.cf_deployments.save(cf_deployment)

                with Connection() as db:
                        cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                        monitor_ip = cf_deployment['monitor_ip']

                if monitor_ip !='':
                    call_rule_method('CFV2InstallProcess', 'register_monitor_node', monitor_ip=monitor_ip, deployment_id=deployment_id)
                    logger.debug("Inject Cloud Foundry with external monitor installation script.")
                    call_rule_method('CFV2InstallProcess', 'inject_cf_with_external_monitor_script', deployment_id=deployment_id)
                else:
                    logger.debug("Inject Cloud Foundry with internal monitor installation script.")
                    call_rule_method('CFV2InstallProcess', 'inject_cf_script', deployment_id=deployment_id)

                logger.info("Call puppet to start to install Cloud Foundry V2")
                call_rule_method('CFV2InstallProcess', 'install_cf_layer1', deployment_id=deployment_id)
                call_rule_method('CFV2InstallProcess', 'install_cf_layer2', deployment_id=deployment_id)
                call_rule_method('CFV2InstallProcess', 'install_cf_layer3', deployment_id=deployment_id)
                call_rule_method('CFV2InstallProcess', 'install_cf_layer4', deployment_id=deployment_id)

                if monitor_ip !='':
                    logger.debug("Inject MONITOR installation script.")
                    call_rule_method('CFV2InstallProcess', 'inject_monitor_script', deployment_id=deployment_id)
                    call_rule_method('CFV2InstallProcess', 'install_monitor', deployment_id=deployment_id)

                cf_deployment['status'] = stage[5]

                db.cf_deployments.save(cf_deployment)

        else:
            output = "Timeout"

        mco_client.close()

        return str(output)

    @route('/cloudfoundry/<deployment_id>/facts', methods=['GET'])
    def get_deployment_facts(deployment_id):
        facts = ",,,,,,,,,,,,,,,,,,,,,,"
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            if (cf_deployment.has_key('ccdb_ip') and cf_deployment.has_key('uaadb_ip') and cf_deployment.has_key('syslog_ip') and
             cf_deployment.has_key('nfs_ip')and cf_deployment.has_key('nats_ip')and cf_deployment.has_key('etcd0_ip') and
             cf_deployment.has_key('etcd1_ip') and  cf_deployment.has_key('etcd2_ip')and  cf_deployment.has_key('router_ip') and
             cf_deployment.has_key('loggregator_ip') and cf_deployment.has_key('loggregator_endpoint_ip')
             and cf_deployment.has_key('collector_ip')and cf_deployment.has_key('ntp_server')and cf_deployment.has_key('console_ip')
             and cf_deployment.has_key('haproxy_out')and cf_deployment.has_key('login_out')and cf_deployment.has_key('nfs_server_network')
             and cf_deployment.has_key('collector_hostname')and cf_deployment.has_key('nats_username')
             and cf_deployment.has_key('monitor_ip')and cf_deployment.has_key('cf_domain')
             and cf_deployment.has_key('nagios_server_ip')and cf_deployment.has_key('ftp_host')):
                facts = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s" % (cf_deployment['ccdb_ip'], cf_deployment['uaadb_ip'], cf_deployment['syslog_ip']
                    ,cf_deployment['nfs_ip'],cf_deployment['nats_ip'] ,cf_deployment['etcd0_ip'],cf_deployment['etcd1_ip']
                    ,cf_deployment['etcd2_ip'],cf_deployment['router_ip'],cf_deployment['loggregator_ip'],cf_deployment['loggregator_endpoint_ip']
                    ,cf_deployment['collector_ip'],cf_deployment['ntp_server'],cf_deployment['console_ip']
                    ,cf_deployment['haproxy_out'],cf_deployment['login_out'],cf_deployment['nfs_server_network']
                    ,cf_deployment['collector_hostname'],cf_deployment['nats_username'],cf_deployment['monitor_ip']
                    ,cf_deployment['cf_domain'],cf_deployment['nagios_server_ip'],cf_deployment['ftp_host'])

        return facts

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


    @route('/cf/site.pp', methods=['GET'])
    def get_install_cf_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, 'install_cfv2.pp'))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})


    @route('/cloudfoundry/start_install/<deployment_id>/layer1', methods=['POST'])
    def install_cf_layer1(deployment_id):
        logger.info("Call puppet to start to install Cloud Foundry V2 Layer1")

        layer1_server_rex = ["/^cloud-syslog-%s-\d*/"%(deployment_id),"/^cloud-nfsserver-%s-\d*/"%(deployment_id),
        "/^cloud-ccdb-%s-\d*/"%(deployment_id),"/^cloud-uaadb-%s-\d*/"%(deployment_id),
        "/^cloud-haproxy-%s-\d*/"%(deployment_id),"/^cloud-nats-%s-\d*/"%(deployment_id)]

        mco_client = McoSshClient(deployment_id)
        outputs, errors = mco_client.runonce_puppet_batch(layer1_server_rex)

        for error in errors:
            if error:
                logger.info("Install Layer1 Server fail")
                mco_client.close()
                return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status_batch(layer1_server_rex)
        logger.debug("Layer1 is_running: %s" % str(is_running))
        logger.info("Start to check Layer1 installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status_batch(layer1_server_rex)
            logger.debug("Layer1 is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_layer:
                break

        mco_client.close()

        logger.info("Finish installing Cloud Foundry V2 Layer1")

        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/layer2', methods=['POST'])
    def install_cf_layer2(deployment_id):
        logger.info("Call puppet to start to install Cloud Foundry V2 Layer2")

        layer2_server_rex = ["/^cloud-etcd-%s-\d*/"%(deployment_id),"/^cloud-collector-%s-\d*/"%(deployment_id),
        "/^cloud-console-%s-\d*/"%(deployment_id)]

        mco_client = McoSshClient(deployment_id)
        outputs, errors = mco_client.runonce_puppet_batch(layer2_server_rex)

        for error in errors:
            if error:
                logger.info("Install Layer2 fail")
                mco_client.close()
                return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status_batch(layer2_server_rex)
        logger.debug("Layer2 is_running: %s" % str(is_running))
        logger.info("Start to check Layer2 installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status_batch(layer2_server_rex)
            logger.debug("Layer2 is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_layer:
                break

        mco_client.close()

        logger.info("Finish installing Cloud Foundry V2 Layer2")
        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/layer3', methods=['POST'])
    def install_cf_layer3(deployment_id):
        logger.info("Call puppet to start to install Cloud Foundry V2 Layer3")

        layer3_server_rex = ["/^cloud-loggregatorserver-%s-\d*/"%(deployment_id),"/^cloud-loggregatortrafficcontroller-%s-\d*/"%(deployment_id),
        "/^cloud-healthmanager-%s-\d*/"%(deployment_id)]

        mco_client = McoSshClient(deployment_id)
        outputs, errors = mco_client.runonce_puppet_batch(layer3_server_rex)

        for error in errors:
            if error:
                logger.info("Install Layer3 Server fail")
                mco_client.close()
                return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status_batch(layer3_server_rex)
        logger.debug("Layer3 is_running: %s" % str(is_running))
        logger.info("Start to check Layer3 installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status_batch(layer3_server_rex)
            logger.debug("Layer3 is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_layer:
                break

        mco_client.close()

        logger.info("Finish installing Cloud Foundry V2 Layer3")
        return str(True)

    @route('/cloudfoundry/start_install/<deployment_id>/layer4', methods=['POST'])
    def install_cf_layer4(deployment_id):
        logger.info("Call puppet to start to install Cloud Foundry V2 Layer4")

        layer4_server_rex = ["/^cloud-login-%s-\d*/"%(deployment_id),"/^cloud-uaa-%s-\d*/"%(deployment_id),
        "/^cloud-cloudcontroller-%s-\d*/"%(deployment_id),"/^cloud-cloudcontrollerworker-%s-\d*/"%(deployment_id)
        ,"/^cloud-dea-%s-\d*/"%(deployment_id),"/^cloud-router-%s-\d*/"%(deployment_id)
        ,"/^cloud-clockglobal-%s-\d*/"%(deployment_id)]

        mco_client = McoSshClient(deployment_id)
        outputs, errors = mco_client.runonce_puppet_batch(layer4_server_rex)

        for error in errors:
            if error:
                logger.info("Install Layer4 Server fail")
                mco_client.close()
                return str(False)

        time.sleep(each_check_span)
        is_running, status = mco_client.check_running_status_batch(layer4_server_rex)
        logger.debug("Layer4 is_running: %s" % str(is_running))
        logger.info("Start to check Layer4 installation status")
        total_time = 0
        while is_running:
            is_running, status = mco_client.check_running_status_batch(layer4_server_rex)
            logger.debug("Layer4 is_running inside: %s" % str(is_running))
            time.sleep(each_check_span)
            total_time += each_check_span

            if total_time >= time_out_to_install_layer:
                break

        mco_client.close()
        logger.info("Finish installing Cloud Foundry V2 Layer4")

        call_rule_method('CFV2InstallProcess', 'set_status', deployment_id=deployment_id, status=stage[3])

        return str(True)


    @route('/add_new_dea/<deployment_id>/<project_name>/<stack_name>', methods=['POST'])
    def append_new_dea(project_name, stack_name, deployment_id):
        logger.info("Add a new DEA to existed deployment...")
        logger.debug("Inject MCO installation script.")
        call_rule_method('CFV2InstallProcess', 'inject_mco_script', deployment_id=deployment_id)

        heat_client = htclient.heat(project_name)
        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name
        request_obj['template_url'] = service_endpoint + "/contrib/CFV2InstallProcess/cloudfoundry_heat_script/%s/heat_new_dea.yaml"%(deployment_id)
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
            mco_client = McoSshClient(deployment_id)

            while not if_install_mco:
                server_list, count = mco_client.check_register_servers(resource_id)

                logger.debug("Current  service_list = map(str,role['service_list']): %s" % str(server_list))
                # Check if all the resources connect to MCO
                if 1 == count and resource_id in server_list:
                    if_install_mco = True
                    break

                total_time += each_check_span

                if total_time >= time_out_to_connect_to_mco:
                    break

                time.sleep(each_check_span)

            logger.info("Add %s into database..." % resource_id)
            facts = eval(call_rule_method('CFV2InstallProcess', "get_facts", deployment_id=deployment_id,certname=resource_id))
            node_infos.append(facts)

            db.cf_deployments.save(cf_deployment)


            logger.info("Start to call Puppet to install a new DEA...")

            logger.debug("Inject Cloud Foundry installation script.")
            call_rule_method('CFV2InstallProcess', 'inject_cf_script', deployment_id=deployment_id)
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
            call_rule_method('CFV2InstallProcess', 'install_monitor', deployment_id=deployment_id)

        return str(True)

    @route('/cloudfoundry_heat_script/<deployment_id>/heat_new_dea.yaml', methods=['GET'])
    def get_new_dea_script(deployment_id):
        file_object = open(os.path.join(STATIC_FILE_PATH, 'heat_new_dea.yaml'))
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


    @route('/cloudfoundry/start_install/<deployment_id>/monitor', methods=['POST'])
    def install_monitor(deployment_id):
        logger.info("Install or Update Monitor Server")
        rex_for_monitor = "monitor-%s-1"%(deployment_id)
        mco_client = McoSshClient(deployment_id)
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
        call_rule_method('CFV2InstallProcess', 'set_status', deployment_id=deployment_id, status=stage[4])
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
        status = "UNKOWN"
        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            status = cf_deployment['status']

        return status

    # @route('/cloudfoundry/mco/status/<resource_id>', methods=['POST'])
    # def check_mco_task_status(resource_id):
    #     mco_client = McoSshClient()
    #     is_running, status = mco_client.check_running_status(resource_id)
    #     mco_client.close()

    #     output = "{is_running: %s, status: %s}" % (str(is_running), str(status))

    #     return output

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
                    # logger.debug("Role of node: %s" % cf_role_name)
                    role = db.roles.find_one({"role_name": cf_role_name})
                    service_list = map(str,role['service_list'])
                    # logger.debug("Service list of %s: %s" % (cf_role_name, service_list))
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

    @route('/get_facts/<deployment_id>/<certname>', methods=['POST'])
    def get_facts(deployment_id,certname):
        logger.info("Call MCO to get facts for %s" % certname)
        mco_client = McoSshClient(deployment_id)
        facts = mco_client.get_facts(certname)
        mco_client.close()

        return str(facts)

    @route('/add_new_router/<deployment_id>/<project_name>/<stack_name>', methods=['POST'])
    def append_new_router(project_name, stack_name, deployment_id):
        logger.info("Add a new ROUTER to existed deployment...")
        logger.debug("Inject MCO installation script.")
        call_rule_method('CFV2InstallProcess', 'inject_mco_script', deployment_id=deployment_id)

        heat_client = htclient.heat(project_name)
        request_obj = json.loads(request.data)
        request_obj['stack_name'] = stack_name
        request_obj['template_url'] = service_endpoint + "/contrib/CFV2InstallProcess/cloudfoundry_heat_script/%s/heat_new_router.yaml"%(deployment_id)
        logger.info("Template URL: "+request_obj['template_url'])
        deployment_id = request_obj['parameters']['deployment_id']
        logger.info("Stack parameters: " + json.dumps(request_obj))

        logger.info("Start to add new ROUTER to deployment: %s" % deployment_id)
        stack_manager = heat_client.stacks
        stack = stack_manager.create(**request_obj)

        logger.info("Create stack!!!")

        with Connection() as db:
            logger.info("Connect to DB...")
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            node_infos = cf_deployment['node_infos']

            max_router_id = 0
            for node_info in node_infos:
                if re.match(r"^cloud-router-%s-\d*" % (deployment_id), node_info['hostname']):
                    router_id = node_info['hostname'].split("-")[-1]
                    logger.debug("ROUTER ID: %s" % router_id)
                    if (int(router_id) > max_router_id):
                        max_router_id = int(router_id)

            new_router_id = str((max_router_id+1))
            resource_id = "cloud-router-%s-%s"%(deployment_id, new_router_id)
            logger.info("Loop, waiting %s installed MCO..." % resource_id)

            if_install_mco = False
            total_time = 0
            mco_client = McoSshClient(deployment_id)

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
            facts = eval(call_rule_method('CFV2InstallProcess', "get_facts", deployment_id=deployment_id,certname=resource_id))
            node_infos.append(facts)

            db.cf_deployments.save(cf_deployment)

            logger.info("Start to call Puppet to install a new ROUTER...")

            logger.debug("Inject Cloud Foundry installation script.")
            call_rule_method('CFV2InstallProcess', 'inject_cf_script', deployment_id=deployment_id)
            output, error = mco_client.runonce_puppet(resource_id)

            if error:
                logger.info("Install new ROUTER Server fail")
                mco_client.close()
                return str(False)

            time.sleep(each_check_span)
            is_running, status = mco_client.check_running_status(resource_id)
            logger.debug("is_running: %s" % str(is_running))
            logger.info("Start to check new ROUTER installation status")
            total_time = 0
            while is_running:
                is_running, status = mco_client.check_running_status(resource_id)
                logger.debug("is_running inside: %s" % str(is_running))
                time.sleep(each_check_span)
                total_time += each_check_span

                if total_time >= time_out_to_install_other_components:
                    break

            mco_client.close()

            logger.debug("Finally update monitor server, make the new added ROUTER under monitor.")
            call_rule_method('CFV2InstallProcess', 'install_monitor', deployment_id=deployment_id)

        return str(True)

    @route('/cloudfoundry_heat_script/<deployment_id>/heat_new_router.yaml', methods=['GET'])
    def get_new_router_script(deployment_id):
        file_object = open(os.path.join(STATIC_FILE_PATH, 'heat_new_router.yaml'))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()

        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            node_infos = cf_deployment['node_infos']

            max_router_id = 0
            for node_info in node_infos:
                if re.match(r"^cloud-router-%s-\d*" % (deployment_id), node_info['hostname']):
                    router_id = node_info['hostname'].split("-")[-1]
                    logger.debug("ROUTER ID: %s" % router_id)
                    if (int(router_id) > max_router_id):
                        max_router_id = int(router_id)

            new_router_id = str((max_router_id+1))
            logger.info("Return a ROUTER with ID: %s" % new_router_id)
            # all_text = all_text.replace("[^ID^]", new_router_id)

            all_text = all_text.replace("[^ID^]", new_router_id).replace("[^puppet_master_ip^] ", cf_deployment['puppet_master_ip'])

            print all_text
        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=heat_new_router.yaml"})


    @route('/cloudfoundry/generate_cert/<cf_domain>/<deployment_id>', methods=['POST'])
    def generate_cert(cf_domain,deployment_id):
        logger.info("Generate cert")
        cert_client = CertGenClient()
        cert_client.gen_cert(cf_domain)
        haproxy_out = cert_client.read_cert('haproxy.out')
        logger.info("haproxy_out %s" , haproxy_out)
        login_out = cert_client.read_cert('login.out')
        logger.info("login_out %s", login_out)

        cert_client.close()

        with Connection() as db:
            cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
            cf_deployment['haproxy_out'] = haproxy_out
            cf_deployment['login_out'] = login_out

            db.cf_deployments.save(cf_deployment)

        return str(True)

    @route('/monitor/site.pp', methods=['GET'])
    def get_install_monitor_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, 'install_monitor_cfv2.pp'))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()

        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})


    @route('/cloudfoundry/<deployment_id>/inject_monitor_script', methods=['POST'])
    def inject_monitor_script(deployment_id):
        global cf_puppet_master
        if not cf_puppet_master:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                puppet_master_ip = cf_deployment['puppet_master_ip']
                cf_puppet_master = PuppetMasterActionClient(puppet_master_ip)

        logger.info("Start to inject MONITOR install Script")
        output = cf_puppet_master.cp_cfv2_monitor_script()

        return output

    @route('/cfwithexternalmonitor/site.pp', methods=['GET'])
    def get_cf_with_external_monitor_script():
        file_object = open(os.path.join(STATIC_FILE_PATH, 'install_cfv2_with_external_monitor.pp'))
        try:
            all_text = file_object.read()
        finally:
            file_object.close()

        return Response(all_text, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename=site.pp"})


    @route('/cloudfoundry/<deployment_id>/inject_cf_with_external_monitor_script', methods=['POST'])
    def inject_cf_with_external_monitor_script(deployment_id):
        global cf_puppet_master
        if not cf_puppet_master:
            with Connection() as db:
                cf_deployment = db.cf_deployments.find_one({'_id': deployment_id})
                puppet_master_ip = cf_deployment['puppet_master_ip']
                cf_puppet_master = PuppetMasterActionClient(puppet_master_ip)

        logger.info("Start to inject Cloud Foundry with External Monitor install Script")
        output = cf_puppet_master.cp_cf_with_external_monitor_script()

        logger.debug("Inject return: %s"%(output))

        return output

    @route('/cloudfoundry/ansilbe_play/<deployment_id>', methods=['POST'])
    def ansilbe_play(deployment_id):
        ansilbe_client = AnsibleClient()
        out = ansilbe_client.setup_ansible()
        logger.info("Setup return: %s"%(out))

        out = ansilbe_client.play_ansible(deployment_id)
        logger.info("play return: %s"%(out))
        # out = ansilbe_client.cd_ansible()
        # logger.info("cd return: %s"%(out))
        return out
