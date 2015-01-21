# vim: tabstop=4 shiftwidth=4 softtabstop=4

import os
import sys
import logging
import logging.config

from process_controller.common import config

def setup():
    log_conf_files = ['logging.conf',
             os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, 'etc', 'process_controller')),
             '/etc/process_controller/logging.conf']

    print log_conf_files
    
    for f in log_conf_files:
        if os.path.exists(f):
            logging.config.fileConfig(f)
            break
    
    if(config.CONF.getboolean('Default', "debug")):
        logging.basicConfig(level=logging.DEBUG)
    if(config.CONF.getboolean('Default', "verbose")):
        logging.basicConfig(level=logging.INFO)
