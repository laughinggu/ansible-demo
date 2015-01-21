'''
Created on June 4th, 2014

@author: Layne
'''

import os
import importlib
import inspect
import logging
import traceback

from flask import Flask, Response, jsonify
from process_controller.common.config import CONF, STATIC_FILE_PATH, TEMPLATE_PATH

from jinja2 import Environment, FileSystemLoader

app = Flask('process_controller')

logger = logging.getLogger(__name__)

if(CONF.getboolean("Default","debug")):
    app.debug = True

rule_dict = {}

method_dict = {}

new_rule_list = []

def process_plugin(cls):
    process_clazz = cls.__name__.split(".")[-1]
    for f, rule_list in rule_dict.iteritems():
        if f in cls.__dict__.values():
            setattr(f, "__clazz__", process_clazz)
            options = rule_list[1]
            endpoint = options.pop('endpoint', process_clazz + "." + f.__name__)
            new_rule = "/contrib/" + process_clazz + rule_list[0]
            if new_rule not in new_rule_list:
                app.add_url_rule(new_rule, endpoint, f, **options)
                new_rule_list.append(new_rule)
    return cls

def route(rule, **options):
    def decorator(f):
        rule_dict[f] = [rule, options]
        return f
    return decorator

def call_rule_method(clazz_name, method_name, **kwargs):
    for method in rule_dict.keys():
        if method_name == method.__name__ and clazz_name == method.__clazz__:
            return method(**kwargs)

# initialize jinja2 template
template_env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))

def find_template(template):
    return template_env.get_template(template)

# Import all processes
from process_controller.processes import *
process_base_dir = CONF.get("Process","BASE_PROCESS_DIR")
process_modules = CONF.get("Process","PROCESSES")

process_list = process_modules.split(",")
for process in process_list:
    path_list = ".".join([process_base_dir, process]).split(".")
    process_module = importlib.import_module(".".join(path_list[:-1]))
    process_clazz = getattr(process_module,  path_list[-1])

    process_clazz()

@app.errorhandler(Exception)
def handle_invalid_usage(error):
    error_rep = {
        'status': 'Error',
        'message': str(error.message)
    }
    response = Response(response=str(error_rep), status=500)
    logger.error(traceback.format_exc())

    return response
