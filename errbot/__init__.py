import logging

from errbot.botplugin import BotPlugin # repeat it here for convenience and coherence with @botcmd
def botcmd(*args, **kwargs):
    """Decorator for bot command functions
    extra parameters to customize the command:
    name : override the command name
    split_args_with : prepare the arguments by splitting them by the given character
    """

    def decorate(func, hidden=False, name=None, split_args_with = '', admin_only = False, historize = True, template = None):
        if not hasattr(func, '_err_command'): # don't override generated functions
            setattr(func, '_err_command', True)
            setattr(func, '_err_command_hidden', hidden)
            setattr(func, '_err_command_name', name or func.__name__)
            setattr(func, '_err_command_split_args_with', split_args_with)
            setattr(func, '_err_command_admin_only', admin_only)
            setattr(func, '_err_command_historize', historize)
            setattr(func, '_err_command_template', template)
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)

#def deprecated_botcmd(*args, **kwargs):
#    import traceback
#    tb = traceback.extract_stack()[-2]
#    logging.warn("""
#    DEPRECATED USAGE:
#    A plugin uses the former cmdbot place, please change the
#    'from errbot.jabberbot import botcmd'
#    the old @cmdbot is called from the line %i of %s
#    to
#    'from errbot import botcmd'
#    """%(tb[1], tb[0]))
#    return botcmd(*args, **kwargs)
# hack the module system to have a deprecated version of botcmd

import imp, sys

class DeprecationDetector(object):
    def __init__(self):
        # construct a virtual module
        self.module = imp.new_module('errbot.jabberbot')
        setattr(self.module, 'botcmd', botcmd)

    def find_module(self, fullname, path=None):
        if fullname == 'errbot.jabberbot':
            self.path = path
            return self
        return None

    def load_module(self, name):
        import traceback
        tb = traceback.extract_stack()[-2]
        logging.warn("""DEPRECATED USAGE:
            A plugin uses the former cmdbot place, please change the
            'from errbot.jabberbot import botcmd' line %i of %s
            to 'from errbot import botcmd'"""%(tb[1], tb[0]))
        return self.module

sys.meta_path = [DeprecationDetector()]
