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
