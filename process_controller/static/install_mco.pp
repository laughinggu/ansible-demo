node /^cloud-*/ {
    class { '::mcollective':
        middleware_hosts => [ '10.62.83.24' ],
    }

    mcollective::plugin { 'puppet':
        package => true,
    }

    mcollective::plugin { 'service':
        package => true,
    }
}