'''
Created on Jun 3, 2013

@author: yank1
'''
import unittest

from process_controller.service import app
from flask import url_for

class Test(unittest.TestCase):

    def test_get_mirror(self):
        with app.test_request_context():
            print url_for('/mintor/network/mirrors/abc')
