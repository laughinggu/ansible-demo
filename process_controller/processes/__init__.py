'''
Created on June 5th, 2014

@author: Layne
'''


import json
import types
import logging

from flask import abort, request, Response

from process_controller.clients.mco_ssh_client import McoSshClient
from process_controller.clients.heat_client import client as htclient
from process_controller.clients.puppet_master_action_client import PuppetMasterActionClient
from process_controller.clients.monitor_action_client import MonitorActionClient
from process_controller.clients.cert_generate_client import CertGenClient
from process_controller.clients.ansible_client import AnsibleClient

from process_controller.service import *
from process_controller.db.connection import Connection


logger = logging.getLogger(__name__)

def show_one(o, show_list):
    show = {}
    for k in show_list:
        if hasattr(o, k):
            print o
            show[k] = o.__getattr__(k)
    return show

def response_parser(list, show_list):
    response_list = []
    if isinstance(list, types.ListType):
        print "0"
        for o in list:
            if not isinstance(o, types.ListType):
                print "1"
                logger.debug("It's not a list. Show one object.")
                response_list.append(show_one(o, show_list))
            else:
                print "2"
                logger.debug("It's a list. Continue to response as a list.")
                Response(o, show_list)
    return response_list


def to_bool(value):
    """
       Converts 'something' to boolean. Raises exception for invalid formats
           Possible True  values: 1, True, "1", "TRue", "yes", "y", "t"
           Possible False values: 0, False, None, [], {}, "", "0", "faLse", "no", "n", "f", 0.0, ...
    """
    if str(value).lower() in ("yes", "y", "true",  "t", "1"): return True
    if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): return False
    raise Exception('Invalid value for boolean conversion: ' + str(value))