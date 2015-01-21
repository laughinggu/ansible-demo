/*
   Monitoring Server.pp
*/


$nagios_server_ip = hiera('monitor_server_ip')
$ganglia_clusters = hiera('ganglia_clusters')
$ganglia_grid_name = hiera('ganglia_grid_name')

$contacts = hiera('contacts')

node /^monitor-*/ {
  network::interface { 'eth0':
    ipaddress => hiera('monitor_server_ip'),
	gateway   => hiera('monitor_server_gateway'),
    netmask   => hiera('monitor_server_netmask'),
    dns_nameservers => hiera('monitor_server_dns'),
  }
  
  class { 'nagios::server::base':
    nagios_web_url => "http://${nagios_server_ip}/nagios3/",
    contacts => $contacts,
  }

  class { 'nagios::server::service':
    nagios_admin_username => hiera('nagios_admin_username'),
    nagios_admin_passwd => hiera('nagios_admin_password'),
  }

  if hiera('monitor_openstack') == 'True' {
      $openstack_cluster_name = hiera('openstack::cluster::name')
      
	  class { 'nagios::server::openstack':
	    cluster_name => $openstack_cluster_name,
	    ganglia_url => "http://${nagios_server_ip}/ganglia/?c=${openstack_cluster_name}&h=\$HOSTALIAS\$",
	    hosts => hiera('openstack::hosts'),
	    service_properties => hiera('openstack::properties'),
	  }
  }

  if hiera('monitor_cloudfoundry') == 'True' {
	  class { 'nagios::server::cloudfoundry':
	    cluster_name => $::cloudfoundry_cluster_name,
	    ganglia_url => "http://${nagios_server_ip}/ganglia/?c=${::cloudfoundry_cluster_name}&h=\$HOSTALIAS\$",
	    hosts => $::cloudfoundry_hosts,
	    service_properties => $::cloudfoundry_service_properties,
	  }
  }

  class { 'nagios::agent':
    allowed_hosts => $nagios_server_ip,
  }

  class { 'nagios::mail':
    mailname => hiera('nagios_mail_name'),
  }

  class { 'ganglia::web':
  }

  class { 'ganglia::gmetad':
    clusters => $ganglia_clusters,
    gridname => $ganglia_grid_name
  }

  class { 'ganglia::gmond':
    cluster_name => 'monitor_server',
    cluster_owner => 'monitor',
    udp_recv_channel   => [],
    udp_send_channel   => $udp_send_channel,
    tcp_accept_channel => $tcp_accept_channel,
  }
  
}