#*******************************************************************************
#                                                                              *
#          This puppet module is used to install cf v2 into any platform       *
#                                                                              *
#                                                                              *
#*******************************************************************************




#==========================domain, system domain and app domain=================
$cf_deployment_domain = $::cf_domain_v2                                        
#==================================== end ======================================



#==========================common password for cf v2 ===========================
$password = 'dangerous'                                             #
#==================================== end ======================================



#====================================ccdb configuration=========================
$cf_ccdb_address = $::ccdb_ip_v2                                                 #                                               
$ccdb_password = 'dangerous'                                            #
$db_encryption_key ='dangerous'                                    #
#==================================== end ======================================



#================================uaadb configuration============================
$cf_uaadb_address = $::uaadb_ip_v2                                                #
$uaadb_password = 'dangerous'                                             #
#==================================== end ======================================



#=======================uaa token and secret configuration=====================
$cf_uaa_client_secret = 'dangerous'                           
$cf_uaa_cc_client_secret = 'dangerous'                              
$cf_uaa_clients_login_secret = 'dangerous'                
$cf_uaa_clients_portal_secret = 'dangerous'                 
$cf_uaa_clients_autoscaling_service_secret = 'dangerous'          
$cf_uaa_clients_system_passwords_secret = 'dangerous'          
$cf_uaa_clients_cc_service_broker_client_secret = 'dangerous'       
$cf_uaa_scim_users_admin = 'dangerous'                         
$cf_uaa_scim_users_push_console = 'dangerous'                 
$cf_uaa_scim_users_smoke_tests = 'dangerous'                     
$cf_uaa_scim_users_system_services = 'dangerous'                
$cf_uaa_scim_users_system_verification = 'dangerous'          
#==================================== end =====================================



#=======================================ntp server =============================
$ntp_server = $::ntp_ip_v2                                                     #
#==================================== end ======================================


#=======================certification for haproxy and login ====================
$ha_proxy_cert = $::haproxy_cert_v2                                            #
$login_cert = $::login_cert_v2                                                 #
#==================================== end ======================================
 


#==============================syslog_aggregator configuration==================
$cf_syslog_aggregator_address = $::syslog_ip_v2                                #
$cf_syslog_aggregator_port = '1514'                                            #
$cf_syslog_aggregator_all = true                                               #
$cf_syslog_aggregator_transport = 'tcp'                                        #
#==================================== end ======================================



#=====================================nats configuration========================
$cf_nats_user = $::nats_username_v2                                                         #
$cf_nats_password = 'dangerous'                                          #
$cf_nats_port = '4222'                                                         #
$cf_nats_machines = $::nats_ip_v2                                                #
#==================================== end ======================================



#=====================================nfs configuration=========================
$cf_nfs_server_address  = $::nfs_ip_v2                                          #
$cf_nfs_server_network = $::nfs_network_v2                                         #
#==================================== end ======================================



#=====================================etcd machines=============================
$cf_etcd_machines_0 = $::etcd0_ip_v2                                              #
$cf_etcd_machines_1 = $::etcd1_ip_v2                                               #
$cf_etcd_machines_2 = $::etcd2_ip_v2                                               #
#==================================== end ======================================



#==============================route ip address=================================
$cf_route_ips = $::router_ip_v2                                                     #
#==================================== end ======================================



#==============================network used by apps and cf======================
$cf_networks_app = 'default'                                                   #
#==================================== end ======================================



#================================loggregator configuration======================
$cf_loggregator_user = 'loggregator'                                           #
$cf_loggregator_endpoint_host = $::loggregator_endpoint_ip_v2                     #
$cf_loggregator_server = $::loggregator_ip_v2                                     #
#==================================== end ======================================



#================================monitor configuration===================================
$nagios_server_ips = $::monitor_ip_v2                                                         
$ganglia_server_ip = $::monitor_ip_v2                                                        
$udp_recv_channel = [  { port => 8649, bind => '0.0.0.0' },]                               
$udp_send_channel = [  { host => $::collector_hostname_v2, port => 8649, ttl => 1 },]       
$tcp_accept_channel = [  { port => 8649 },]                                             
#==================================== end ==============================================#



#================================cf console configuration=======================
$hostip = $::console_ip_v2                                                       #    
$console_db_password = 'dangerous'     
#==================================== end =F=====================================



#================================ftp_host configuration=========================
#$ftp_host = '10.32.105.117'
$ftp_host = $::ftp_host_v2                                                    #
#==================================== end ======================================



#================================cf collector configuration=====================
#$cf_cluster_name = $::cluster_name_v2                                          #
$cf_cluster_name = cloudfoundryV2_20
$ganglia_host = $::monitor_ip_v2                                                #
$ganglia_port = '8649'                                                         #
$cf_collector_ip = $::collector_ip_v2
$cf_collector_hostname = $::collector_hostname_v2                                  #     
#==================================== end ======================================

#=======================================================cf monitor configuration====================================================
$contacts = [{ name => 'Henry Shao', email => 'Henry.Shao@emc.com', jobs => ['cloudfoundry',], cluster_names => [$cf_cluster_name,] }, ]  
$nagios_admin_username = 'nagiosadmin'                                                                                             
$nagios_admin_passwd = 'dangerous'                                                                                                 
$cloudfoundryv2_hosts = $::monitor_hosts_v2                
$clusters = [ { 'name' => $cf_cluster_name, 'address' => $cf_collector_ip  } ]                                                     
$gridname = 'elc-cloud'                                                                                                                  
#=============================================================== end ===================================================================

node /^monitor-*/  {

  class { 'nagios::server::base':    
    nagios_web_url                                              => "http://${nagios_server_ips}/nagios3/",
    contacts                                                    => $contacts,
  }

  class { 'nagios::server::service':    
    nagios_admin_username                                       => $nagios_admin_username,
    nagios_admin_passwd                                         => $nagios_admin_passwd,
  }

  class { 'nagios::server::cloudfoundry':    
    service_properties => {
        check_node_hostname   => $cf_collector_hostname,
        check_node   => $cf_collector_ip,
        domain => $cf_deployment_domain,
        ganglia_node   => $ganglia_server_ip,
        nats_url => "nats://$cf_nats_user:$cf_nats_password@$cf_nats_machines:4222",
        ntp_server => $ntp_server,
        system_disk_partition =>'/dev/vda1',
        ccdb_type => 'pgsql',
        ccdb_host => $cf_ccdb_address,
        ccdb_user => 'admin',
        ccdb_passwd => $ccdb_password,
        ccdb_connection => "host=$cf_ccdb_address,user=admin,passwd=$ccdb_password,db=ccdb,port=2544",
    },
    cluster_name                                                => $cf_cluster_name,
    ganglia_url                                                 => "http://${nagios_server_ips}/ganglia/?c=${cf_cluster_name}&h=\$HOSTALIAS\$",
    hosts                                                       => $cloudfoundryv2_hosts,
  }

  class { 'ganglia::web':
  }

  class { 'ganglia::gmetad':
    clusters                                                    => $clusters,
    gridname                                                    => $gridname,
  }

  class { 'nagios::agent':
         allowed_hosts => $nagios_server_ips,
  }

  class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => $udp_recv_channel,
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
  }

  Class['nagios::server::cloudfoundry'] ~> Service['nagios3']
  Class['nagios::agent'] ~> Service['nagios3']
}