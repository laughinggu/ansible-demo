node /^openstack-controller-*/ {
  class { '::openstack::profile::base': }
  class { '::openstack::profile::firewall': }
  class { '::openstack::profile::rabbitmq': } ->
  class { '::openstack::profile::memcache': } ->
  class { '::openstack::profile::mysql': } ->
  class { '::openstack::profile::mongodb': } ->
  class { '::openstack::profile::keystone': } ->
  class { '::openstack::profile::ceilometer::api': } ->
  class { '::openstack::profile::glance::auth': } ->
  class { '::openstack::profile::cinder::api': } ->
  class { '::openstack::profile::nova::api': } ->
  class { '::openstack::profile::neutron::server': } ->
  class { '::openstack::profile::heat::api': } ->
  class { '::openstack::profile::horizon': }
  class { '::openstack::profile::auth_file': }

  class { '::openstack::profile::glance::api': }
  class { '::openstack::profile::cinder::volume': }

  class { '::openstack::profile::neutron::router': }

  exec {'stop iptables':
    require => Class['::openstack::profile::firewall', '::openstack::profile::horizon', '::openstack::profile::glance::api', '::openstack::profile::cinder::volume'],
    command => '/etc/init.d/iptables stop',
  }
  
  class { 'nagios::agent':
    allowed_hosts => hiera('monitor_server_ip'),
  }

  class { 'ganglia::gmond':
    cluster_name => hiera('openstack::deployment_name'),
    cluster_owner => 'monitor',
    udp_recv_channel   => hiera('openstack::udp_recv_channel'),
    udp_send_channel   => hiera('openstack::udp_send_channel'),
    tcp_accept_channel => hiera('openstack::tcp_accept_channel'),
  }

}

node /^openstack-compute-*/ {

  class { '::openstack::profile::base': }
  class { '::openstack::profile::firewall': }
  class { '::openstack::profile::neutron::agent': }
  class { '::openstack::profile::nova::compute': }
  class { '::openstack::profile::ceilometer::agent': }

  exec {'stop iptables':
    require => Class['::openstack::profile::firewall', '::openstack::profile::nova::compute'],
    command => '/etc/init.d/iptables stop',
  }
  
  class { 'nagios::agent':
    allowed_hosts => hiera('monitor_server_ip'),
  }

  class { 'ganglia::gmond':
    cluster_name => hiera('openstack::deployment_name'),
    cluster_owner => 'monitor',
    udp_recv_channel   => [],
    udp_send_channel   => hiera('openstack::udp_send_channel'),
    tcp_accept_channel => hiera('openstack::tcp_accept_channel'),
  }

}
