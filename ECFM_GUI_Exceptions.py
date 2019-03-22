from GlobalSettings import *

class IDA_GUI_Error(Exception):
    pass

class InitVarException(IDA_GUI_Error):
    def __init__(self, varname, msg, value):
        self.varname = varname
        self.msg = msg
        self.value = value
    def __str__(self):
        return 'Following error occured when initializing variable {0}'\
                .format(self.varname) + ' with the value {0}:'.format(\
                self.value) + '\n' + self.msg + '\n'

class FormatVarException(IDA_GUI_Error):
    def __init__(self, varname, msg, value):
        self.varname = varname
        self.msg = msg
        self.value = value
    def __str__(self):
        return 'Following error occured when formatting {0}'\
                .format(self.varname) + ' with the value {0}:'.format(\
                self.value) + '\n' + self.msg + '\n'

class ConfigInputException(IDA_GUI_Error):
    def __init__(self, filename, msg):
        self.filename = filename
        self.msg = msg

    def __str__(self):
        return 'Failed to load configfile at:\n{0}\n'.format(self.filename) + \
               '\nFollowing Error occured:\n{0}'.format(self.msg)

class ConfigOutputException(IDA_GUI_Error):
    def __init__(self, filename, msg):
        self.filename = filename
        self.msg = msg

    def __str__(self):
        return 'Failed to save configfile at:\n{0}'.format(self.filename) + \
               '\nFollowing Error occured:\n{0}'.format(self.msg)
