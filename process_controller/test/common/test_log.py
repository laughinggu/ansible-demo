'''
Created on Jun 3, 2013

@author: yank1
'''
import unittest

from process_controller.common import log

import logging
LOG = logging.getLogger(__name__)

class Test(unittest.TestCase):

    def setUp(self):
        log.setup()

    def testInfo(self):
        LOG.info("test Info")


