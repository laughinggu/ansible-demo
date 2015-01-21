$admin_password = 'password'
$keystone_admin_token = 'admin'


$rabbit_password = 'guest'
$rabbit_user = 'guest'
$cinder_db_password = 'cinder_db_password'
$cinder_user_password = 'cinder_user_password'
$ceilometer_user_password = 'ceilometer_user_password'

$admin_email = 'layne.peng@emc.com'

$controller_ip = '10.32.170.44'
$controller_netmask = '255.255.255.0'
$compute_ip = ['10.32.170.45', '10.32.170.46','10.32.170.47','10.32.170.48','10.32.170.197','10.32.170.198','10.32.170.199','10.32.170.189']
$compute_netmask = '255.255.255.0'
$gateway = '10.32.170.1'
$dns_server = '10.32.105.131'
$ntp_server = ['10.32.97.145']

/* Monitoring Conf */    #Not required if it has been defined in monitor.pp
#$nagios_server_ip = '10.32.105.164'
#$udp_recv_channel = [  { port => 8649, bind => '0.0.0.0' },]
#$udp_send_channel = [  { host => '10.32.170.44', port => 8649, ttl => 1 },]
#$tcp_accept_channel = [  { port => 8649 },]

node /^controller-(.*)/ {
   network::interface { 'eth0':
      ipaddress => $controller_ip,
      gateway   => $gateway,
      netmask   => $controller_netmask,
      dns_nameservers => $dns_server,
    }

   network::interface { 'eth1':
      ipaddress => '0.0.0.0',
      netmask   => '255.255.255.255',
   }

   exec{'Restart Network':
      command => '/etc/init.d/networking restart',
      require => network::interface['eth0','eth1'],
   }

	class { 'openstack::controller':
	  public_address          => $controller_ip,
	  public_interface        => 'eth0',
	  private_interface       => 'eth1',
	  internal_address        => $controller_ip,
	  floating_range          => '10.32.170.64/24',
	  fixed_range             => '10.0.0.0/24',
	  multi_host              => true,
	  network_manager         => 'nova.network.manager.FlatDHCPManager',
	  admin_email             => 'layne.peng@emc.com',
	  admin_password          => $admin_password,
	  cinder_db_password      => $cinder_db_password,
	  cinder_user_password    => $cinder_user_password ,
	  keystone_admin_token    => $keystone_admin_token,
	  keystone_db_password    => 'keystone_db_password',
	  glance_user_password    => 'glance_user_password',
	  glance_db_password      => 'glance_db_password',
	  nova_db_password        => 'nova_db_password',
	  nova_user_password      => 'nova_user_password',
  	rabbit_password         => $rabbit_password,
  	rabbit_user             => $rabbit_user,
	  secret_key              => '12345',
	  quantum                 => false,
	  mysql_root_password     => 'password',
  	mysql_account_security  => false,
	}

	 class { 'openstack::auth_file':
	   admin_password       => $admin_password,
	   keystone_admin_token => $keystone_admin_token,
	   controller_node      => $controller_ip,
	 }

	  # And create the database
  	class { 'heat::db::mysql':
   	   password => 'heat',
  	}

 	  # Common class
  	class { 'heat':
       # The keystone_password parameter is mandatory
       keystone_password => 'heat_user_password',
       sql_connection    => 'mysql://heat:heat@localhost/heat'
    }

   # Install heat-engine
 	 class { 'heat::engine':
   	   auth_encryption_key => 'heat_auth_encryption_key',
   	   heat_waitcondition_server_url => "http://$controller_ip:8000/v1/waitcondition",
   	   heat_metadata_server_url      => "http://$controller_ip:8000",
       heat_watch_server_url         => "http://$controller_ip:8003",
  	}

    # Install the heat-api service
    class { 'heat::api': }

    class { 'heat::keystone::auth' :
      password                       => 'heat_user_password',
      public_address                 => $controller_ip,
      admin_address                  => $controller_ip,
      internal_address               => $controller_ip,
    }

    class { 'heat::keystone::auth_cfn' :
      password                       => 'heat_user_password',
      public_address                 => $controller_ip,
      admin_address                  => $controller_ip,
      internal_address               => $controller_ip,
    }

    # Install the heat-api-cfn service
    class { 'heat::api_cfn': }

    # Install the heat-api-cloudwatch service
    class { 'heat::api_cloudwatch': }

    # Install Ceilometer
    class {'ceilometer':
      metering_secret => 'password',
    }

    class {'ceilometer::keystone::auth' :
      password		=> $ceilometer_user_password,
      public_address	=> $controller_ip,
      admin_address	=> $controller_ip,
      internal_address	=> $controller_ip,
    }

    class {'ceilometer::api': 
      keystone_password => $ceilometer_user_password,
    }

    class { 'ceilometer::agent::auth':
      auth_url      => "http://$controller_ip:35357/v2.0",
      auth_password => $ceilometer_user_password,
    }


    class { 'ceilometer::agent::central':}

    class {'::mongodb::server':
       port    => 27018,
       bind_ip  => ['0.0.0.0'],
       verbose => true,
    }

    class { 'ceilometer::db':
      database_connection => "mongodb://$controller_ip:27018/ceilometer",
      require             => Class['::mongodb::server'],
    }

    # Purge 1 month old meters
    class { 'ceilometer::expirer':
      time_to_live => '2592000',
    }

    class { 'ceilometer::collector':
    }

    class { 'nagios::agent':
      allowed_hosts => $nagios_server_ip,
    }

    class { 'ganglia::gmond':
      cluster_name => 'opentack-physical',
      cluster_owner => 'elc',
      udp_recv_channel   => $udp_recv_channel,
      udp_send_channel   => $udp_send_channel,
      tcp_accept_channel => $tcp_accept_channel,
    }

   class { '::ntp':
      servers => $ntp_server,
   }

   class { '::mcollective':
     middleware       => true,
     middleware_hosts => [ $middleware_ip ],
   }
}

node /^compute-(.*)/ {
	network::interface { 'eth0':
      ipaddress => $compute_ip[$1],
	    gateway   => $gateway,
      netmask   => $compute_netmask,
      dns_nameservers => $dns_server,
    }

   network::interface { 'eth1':
      ipaddress => '0.0.0.0',
      netmask   => '255.255.255.255',
   }

	exec {'Restart Network':
	  command => '/etc/init.d/networking restart',
	  require => network::interface['eth0','eth1'],
	}

	class { 'openstack::compute':
	  private_interface  => 'eth1',
	  public_interface   => 'eth0',
	  internal_address   => $compute_ip[$1],
	  libvirt_type       => 'kvm',
	  fixed_range        => '10.0.0.0/24',
	  db_host            => $controller_ip,
	  network_manager    => 'nova.network.manager.FlatDHCPManager',
	  multi_host         => true,
	  rabbit_host        => $controller_ip,
	  rabbit_password    => $rabbit_password,
	  rabbit_user        => $rabbit_user,
	  cinder_db_password => $cinder_db_password,
	  glance_api_servers => "$controller_ip:9292",
	  nova_db_password   => 'nova_db_password',
	  nova_user_password => 'nova_user_password',
	  vncproxy_host      => $controller_ip,
    vncserver_listen   => $compute_ip[$1],
	  te_iscsi_target_prefix   => $te_iscsi_target_prefix,
    iscsi_ip_address         => '10.13.182.11',
	  cinder_volume_driver     => 'te',
    te_base_url        => $te_base_url ,
    te_default_pool    => $storage_pool_for_openstack,
	  vnc_enabled        => true,
	  manage_volumes     => true,
	  quantum            => false,
	}

	class { 'openstack::auth_file':
	   admin_password       => $admin_password,
	   keystone_admin_token => $keystone_admin_token,
	   controller_node      => $controller_ip,
	}

  class { 'nagios::agent':
     allowed_hosts => $nagios_server_ip,
  }

  class { 'ganglia::gmond':
    cluster_name => 'openstack-physical',
    cluster_owner => 'elc',
    udp_recv_channel   => [],
    udp_send_channel   => $udp_send_channel,
    tcp_accept_channel => $tcp_accept_channel,
  }

  class {'ceilometer':
     metering_secret => 'password',
     rabbit_host     =>  $controller_ip,
  }

  class { 'ceilometer::agent::auth':
    auth_url      => "http://$controller_ip:35357/v2.0",
    auth_password => $ceilometer_user_password,
  }

  class { 'ceilometer::agent::compute':}

  class { '::ntp':
    servers => $ntp_server,
  }

  class { '::mcollective':
    middleware_hosts => [ $middleware_ip ],
  }

  mcollective::plugin { 'puppet':
    package => true,
  }

  mcollective::plugin { 'service':
    package => true,
  }
}