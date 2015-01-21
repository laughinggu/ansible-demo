'''
Created on June 5th, 2014

@author: Layne
'''

import pymongo
import logging

from process_controller.common.config import CONF

logger = logging.getLogger(__name__)

class Connection:
    def __enter__(self):
        mongo_host = str(CONF.get("DB", "MONGODB_HOST"))
        logger.info('*** Connecting to Database...')
        logger.info("Host: %s", mongo_host)

        self.conn = pymongo.MongoClient(host=mongo_host)
        self.db = self.conn.orchestrator
        return  self.db
        
    def __exit__(self, type, value, traceback):
        self.conn.disconnect()