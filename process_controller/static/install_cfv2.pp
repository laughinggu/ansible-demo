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
$nagios_server_ips = $::syslog_ip_v2                                                         
$ganglia_server_ip = $::syslog_ip_v2                                                        
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
$ftp_host = $::ftp_host_v2                                                   #
#==================================== end ======================================



#================================cf collector configuration=====================
$cf_cluster_name = $::cluster_name_v2                                          #
$ganglia_host = $::syslog_ip_v2                                                #
$ganglia_port = '8649'                                                         #
$cf_collector_ip = $::collector_ip_v2                                          #
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


node /^cloud-syslog-.*/  {

  class { 'cloudfoundryv2::rsyslog':
        ftp_host                                                => $ftp_host,            
  }

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

node /^cloud-console-.*/  {
    class { 'cloudfoundryv2::console':
        hostip                                                  => $hostip,
        domain                                                  => $cf_deployment_domain,
        portal_password                                         => $cf_uaa_clients_portal_secret,
        console_db_password                                     => $console_db_password,
        ftp_host                                                => $ftp_host,            
        }

        class { 'nagios::agent':
         allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }

}

node /^cloud-collector-.*/  {
    class { 'cloudfoundryv2::collector':
        cf_cluster_name                                          => $cf_cluster_name,
        cf_nats_user                                             => $cf_nats_user,
        cf_nats_password                                         => $cf_nats_password,
        cf_nats_machines                                         => $cf_nats_machines,
        cf_nats_port                                             => $cf_nats_port,
        ganglia_host                                             => $ganglia_host,
        ganglia_port                                             => $ganglia_port,
        ftp_host                                                 => $ftp_host,            
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

        class { 'nagios::check_node_v2':}

}

node /^cloud-ccdb-.*/  {
        class { 'cloudfoundryv2::ccdb':
        ipaddress                                               => $::ipaddress,
        cf_ccdb_password                                        => $ccdb_password,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
         allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-cloudcontroller-.*/  {
        class { 'cloudfoundryv2::cloudcontroller':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,   
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport, 
        cf_domain                                               => $cf_deployment_domain,     
        cf_system_domain                                        => $cf_deployment_domain,     
        cf_app_domain                                           => $cf_deployment_domain,     
        cf_nats_user                                            => $cf_nats_user,       
        cf_nats_password                                        => $cf_nats_password,   
        cf_nats_port                                            => $cf_nats_port,       
        cf_nats_machines                                        => $cf_nats_machines,   
        cf_nfs_server_address                                   => $cf_nfs_server_address,      
        cf_bulk_api_password                                    => $password,
        cf_staging_upload_password                              => $password,
        cf_db_encryption_key                                    => $db_encryption_key,   
        cf_ccdb_ng_password                                     => $ccdb_password,
        cf_ccdb_ng_address                                      => $cf_ccdb_address,
        cf_uaa_clients_cc_service_broker_client_secret          => $cf_uaa_clients_cc_service_broker_client_secret,   
        cf_loggregator_endpoint_host                            => $cf_loggregator_endpoint_host,               
        cf_loggregator_endpoint_shared_secret                   => $password,   
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-clockglobal-.*/  {
        class { 'cloudfoundryv2::clock-global':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,   
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport, 
        cf_domain                                               => $cf_deployment_domain,     
        cf_system_domain                                        => $cf_deployment_domain,     
        cf_app_domain                                           => $cf_deployment_domain,     
        cf_nats_user                                            => $cf_nats_user,       
        cf_nats_password                                        => $cf_nats_password,   
        cf_nats_port                                            => $cf_nats_port,       
        cf_nats_machines                                        => $cf_nats_machines,   
        cf_nfs_server_address                                   => $cf_nfs_server_address,      
        cf_bulk_api_password                                    => $password,
        cf_staging_upload_password                              => $password,
        cf_db_encryption_key                                    => $db_encryption_key,   
        cf_ccdb_ng_password                                     => $ccdb_password,
        cf_ccdb_ng_address                                      => $cf_ccdb_address,
        cf_uaa_clients_cc_service_broker_client_secret          => $cf_uaa_clients_cc_service_broker_client_secret,   
        cf_loggregator_endpoint_host                            => $cf_loggregator_endpoint_host,               
        cf_loggregator_endpoint_shared_secret                   => $password,   
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-cloudcontrollerworker-.*/  {
        class { 'cloudfoundryv2::cloudcontroller-worker':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,   
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport, 
        cf_domain                                               => $cf_deployment_domain,     
        cf_system_domain                                        => $cf_deployment_domain,     
        cf_app_domain                                           => $cf_deployment_domain,     
        cf_nats_user                                            => $cf_nats_user,       
        cf_nats_password                                        => $cf_nats_password,   
        cf_nats_port                                            => $cf_nats_port,       
        cf_nats_machines                                        => $cf_nats_machines,   
        cf_nfs_server_address                                   => $cf_nfs_server_address,      
        cf_bulk_api_password                                    => $password,
        cf_staging_upload_password                              => $password,
        cf_db_encryption_key                                    => $db_encryption_key,   
        cf_ccdb_ng_password                                     => $ccdb_password,
        cf_ccdb_ng_address                                      => $cf_ccdb_address,
        cf_uaa_clients_cc_service_broker_client_secret          => $cf_uaa_clients_cc_service_broker_client_secret,   
        cf_loggregator_endpoint_host                            => $cf_loggregator_endpoint_host,               
        cf_loggregator_endpoint_shared_secret                   => $password,  
        ftp_host                                                => $ftp_host, 
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-dea-.*/  {
        class { 'cloudfoundryv2::dea':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_domain                                               => $cf_deployment_domain,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_loggregator_endpoint_host                            => $cf_loggregator_endpoint_host,
        cf_loggregator_endpoint_shared_secret                   => $password,  
        ftp_host                                                => $ftp_host, 
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-etcd-.*/  {
        class { 'cloudfoundryv2::etcd':
        ipaddress                                               => $::ipaddress,
        cf_etcd_machines_0                                      => $cf_etcd_machines_0,
        cf_etcd_machines_1                                      => $cf_etcd_machines_1,
        cf_etcd_machines_2                                      => $cf_etcd_machines_2,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_username                                        => $cf_nats_username,
        cf_nats_password                                        => $cf_nats_password,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-haproxy-.*/  {
        class { 'cloudfoundryv2::haproxy':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_route_ips                                            => $cf_route_ips,
        cf_networks_app                                         => $cf_networks_app,  
        ftp_host                                                => $ftp_host,  
        ha_proxy_cert                                           => $ha_proxy_cert,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-healthmanager-.*/  {
        class { 'cloudfoundryv2::healthmanager':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_domain                                               => $cf_deployment_domain,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_ccng_bulk_api_password                               => $password,
        cf_etcd_machines_0                                      => $cf_etcd_machines_0,
        cf_etcd_machines_1                                      => $cf_etcd_machines_1,
        cf_etcd_machines_2                                      => $cf_etcd_machines_2,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-loggregatorserver-.*/  {
        class { 'cloudfoundryv2::loggregator-server':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_loggregator_user                                     => $cf_loggregator_user,
        cf_loggregator_password                                 => $password,
        cf_loggregator_shared_secret                            => $password,
        cf_etcd_machines_0                                      => $cf_etcd_machines_0,
        cf_etcd_machines_1                                      => $cf_etcd_machines_1,
        cf_etcd_machines_2                                      => $cf_etcd_machines_2,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_nats_port                                            => $cf_nats_port,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-loggregatortrafficcontroller-.*/  {
        class { 'cloudfoundryv2::loggregator-traffic-controller':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_loggregator_servers                                  => $cf_loggregator_server,
        cf_system_domain                                        => $cf_deployment_domain,
        cf_domain                                               => $cf_deployment_domain,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_nats_port                                            => $cf_nats_port,
        cf_loggregator_shared_secret                            => $password,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-login-.*/  {
        class { 'cloudfoundryv2::login':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_domain                                               => $cf_deployment_domain,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_uaa_clients_login_secret                             => $cf_uaa_clients_login_secret,
        ftp_host                                                => $ftp_host,
        login_cert                                              => $login_cert,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-nats-.*/  {
        class { 'cloudfoundryv2::nats':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-nfsserver-.*/  {
        class { 'cloudfoundryv2::nfs-server':
        ipaddress                                               => $::ipaddress,
        cf_nfs_server_network                                   => $cf_nfs_server_network,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-router-.*/  {
        class { 'cloudfoundryv2::router':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_router_port                                          => $cf_router_port,
        cf_router_status_port                                   => $cf_router_status_port,
        cf_router_status_user                                   => $cf_router_status_user,
        cf_router_status_password                               => $password,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_loggregator_endpoint_host                            => $cf_loggregator_endpoint_host,
        cf_loggregator_endpoint_shared_secret                   => $password,
        cf_networks_app                                         => $cf_networks_app,
        ftp_host                                                => $ftp_host,
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-uaa-.*/  {
        class { 'cloudfoundryv2::uaa':
        ipaddress                                               => $::ipaddress,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        cf_syslog_aggregator_all                                => $cf_syslog_aggregator_all,
        cf_syslog_aggregator_transport                          => $cf_syslog_aggregator_transport,
        cf_uaa_client_secret                                    => $cf_uaa_client_secret,
        cf_uaa_cc_client_secret                                 => $cf_uaa_cc_client_secret,
        cf_uaa_clients_login_secret                             => $cf_uaa_clients_login_secret,
        cf_uaa_clients_portal_secret                            => $cf_uaa_clients_portal_secret,
        cf_uaa_clients_autoscaling_service_secret               => $cf_uaa_clients_autoscaling_service_secret,
        cf_uaa_clients_system_passwords_secret                  => $cf_uaa_clients_system_passwords_secret,
        cf_uaa_clients_cc_service_broker_client_secret          => $cf_uaa_clients_cc_service_broker_client_secret,
        cf_uaa_scim_users_admin                                 => $cf_uaa_scim_users_admin,
        cf_uaa_scim_users_push_console                          => $cf_uaa_scim_users_push_console,
        cf_uaa_scim_users_smoke_tests                           => $cf_uaa_scim_users_smoke_tests,
        cf_uaa_scim_users_system_services                       => $cf_uaa_scim_users_system_services,
        cf_uaa_scim_users_system_verification                   => $cf_uaa_scim_users_system_verification,
        cf_ccdb_address                                         => $cf_ccdb_address,
        cf_ccdb_password                                        => $ccdb_password,
        cf_domain                                               => $cf_deployment_domain,
        cf_nats_password                                        => $cf_nats_password,
        cf_nats_port                                            => $cf_nats_port,
        cf_nats_user                                            => $cf_nats_user,
        cf_nats_machines                                        => $cf_nats_machines,
        cf_uaadb_address                                        => $cf_uaadb_address,
        cf_uaadb_password                                       => $uaadb_password,
        ftp_host                                                => $ftp_host,
                
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }
}

node /^cloud-uaadb-.*/  {
        class { 'cloudfoundryv2::uaadb':
        ipaddress                                               => $::ipaddress,
        cf_uaadb_password                                       => $uaadb_password,
        cf_syslog_aggregator_address                            => $cf_syslog_aggregator_address,
        cf_syslog_aggregator_port                               => $cf_syslog_aggregator_port,
        ftp_host                                                => $ftp_host,
        
        }

        class { 'nagios::agent':
        allowed_hosts => $nagios_server_ips,
        }

        class { 'ganglia::gmond':
        cluster_name => $cf_cluster_name,
        cluster_owner => 'elc',
        udp_recv_channel   => [],
        udp_send_channel   => $udp_send_channel,
        tcp_accept_channel => $tcp_accept_channel,
        }

}