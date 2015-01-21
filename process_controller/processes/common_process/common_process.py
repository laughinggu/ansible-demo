'''
Created on 2014-09-01

@author: baoj1
'''

from process_controller.processes import *

@process_plugin
class CommonProcess(object):
    
    '''
    Process for Common APIs
    '''
    
    @route('/running_processes')
    def get_running_process():
        logger.info("Get running processes: ")
        running_processes = []
        with Connection() as db:
            res = db.processes.find({'status': 'active'})
        for r in res:
            running_processes.append(r)
        logger.info(running_processes)
        return running_processes
            
    
    @route('/launch_process', methods = ['POST'])        
    def launch_process(process_class = None, deployment_id = None):
        logger.info("Create a new %s: %s"%(process_class, deployment_id))
        import datetime
        if process_class is None or deployment_id is None:
            request_obj = json.loads(request.data)
        if process_class is None:
            process_class = request_obj['process_class']
        if deployment_id is None:
            process_class = request_obj['deployment_id']
            
        is_running = False
        with Connection() as db:
            active_processes = db.processes.find({'status': 'active'})
            for process in active_processes:
                if process['deployment_id'] != deployment_id:
                    logger.error("Failed to launch process, another process is running.")
                    return False
                else:
                    is_running = True
                    
            if is_running == False:
                db.processes.insert({'process_class': process_class,
                                     'deployment_id': deployment_id,
                                     'created_at': str(datetime.datetime.utcnow()),
                                     'status': 'active'})
        return True
    
    
    @route('/set_process_status', methods = ['POST'])
    def set_process_status(process_class = None, deployment_id = None, status = None):
        logger.info("Set %s: %s to %s"%(process_class, deployment_id, status))
        import datetime
        
        if process_class is None or deployment_id is None or status is None:
            request_obj = json.loads(request.data)
        if process_class is None:
            process_class = request_obj['process_class']
        if deployment_id is None:
            deployment_id = request_obj['deployment_id']
        if status is None:
            status = request_obj['status']
            
        with Connection() as db:
            process = db.processes.find_one({'deployment_id': deployment_id, 'process_class': process_class})
            if process in None:
                logger.error("Undefined process.")
                return False
            process['status'] = status
            process['updated_at'] = str(datetime.datetime.utcnow())
            db.processes.save(process)
        return True
    
    
    
    
    
    
    
    