node /^cloud-controller-.*/  {
    class { 'cloudfoundry::core::cloudcontroller':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-healthmanager-.*/  {
    class { 'cloudfoundry::core::healthmanager':
        cf_nats_ip              => $::nat_ip,
        cf_ccdb_ip              => $::cc_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-nats-.*/  {
    class { 'cloudfoundry::core::nats':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-stager-.*/  {
    class { 'cloudfoundry::core::stager':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-uaa-.*/  {
    class { 'cloudfoundry::core::uaa':
        cf_nats_ip              => $::nat_ip,
        cf_ccdb_ip              => $::cc_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-dea-.*/  {
    class { 'cloudfoundry::dea':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-router-.*/  {
    class { 'cloudfoundry::router':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-mysql-.*/  {
    class { 'cloudfoundry::service::mysql_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-mongodb-.*/  {
    class { 'cloudfoundry::service::mongodb_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-postgresql-.*/  {
    class { 'cloudfoundry::service::postgresql_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-rabbitmq-.*/  {
    class { 'cloudfoundry::service::rabbitmq_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-redis-.*/  {
    class { 'cloudfoundry::service::redis_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-vblob-.*/  {
    class { 'cloudfoundry::service::vblob_node':
        cf_nats_ip              => $::nat_ip,
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }
}

node /^cloud-collector-.*/  {
    class { 'cloudfoundry::collector':
        cf_nats_ip              => $::nat_ip,
        ganglia_host            => '127.0.0.1',
        ganglia_port            => '8649',
        cf_deployment_domain    => $::cf_domain,
        cf_uaa_urisuaa          => $::cf_uaa_urisuaa,
        cf_uaa_urislogin        => $::cf_uaa_urislogin,
        udp_recv_channel        => [{ port => 8649, bind => '0.0.0.0' },],
        collector_ip            => $::collector_ip,
        nagios_server_ip        => $::nagios_server_ip,
        cluster_name            => $::cloudfoundry_cluster_name,
    }

    class { 'nagios::check_node':}
}