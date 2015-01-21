# vim: tabstop=4 shiftwidth=4 softtabstop=4

import os
import sys
import ConfigParser

CONF = ConfigParser.ConfigParser()

APP_PATH = '/opt/orchestrator/process_controller'
STATIC_FILE_PATH = os.path.join(APP_PATH, 'static')
TEMPLATE_PATH = os.path.join(APP_PATH, 'templates')

PUPPET_HIERA_PATH = "/etc/puppet/hieradata"

#search each lib path, then /etc/orchestrator/process_controller.conf
files = map(lambda f:os.path.normpath(os.path.join(f, 'etc', 'process_controller', 'process_controller.conf')), sys.path)
files.append('/etc/process_controller/process_controller.conf')

def load():
    for f in files:
        if os.path.exists(f):
            CONF.read(f)
            break

load()
