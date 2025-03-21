import time
class InterprocessObjects ():
    '''
    Objects used by the gateway process that various process require access to
    '''
    def __new__(cls):
        '''
        Object allocation
        '''
        if not hasattr(cls, 'instance'):
            cls.instance = super(InterprocessObjects, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        '''
        Contstructor - all attributes are truely defined outside of __init__
        '''
        if not hasattr(self, 'commandList'):
            #  only do this the first time
            self.commandList = None
            self.lastStatus = None
            self.continue_loop = None
            self.connection_number = None
            self.doCommand = None
            self.last_update_time = None
            self.message_update_counter = None
            self.update_status = self.update_status_template()
            next(self.update_status)

    def update_status_template(self):
        '''
        Template for creating an update_status generator
        '''
        while True:
            (device, field, value) = yield
            self.lastStatus[device+field] = value
            self.last_update_time = time.time()
