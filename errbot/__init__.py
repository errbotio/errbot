
def botcmd(*args, **kwargs):
    """Decorator for bot command functions
    extra parameters to customize the command:
    name : override the command name
    thread : asynchronize the command
    split_args_with : prepare the arguments by splitting them by the given character
    """

    def decorate(func, hidden=False, name=None, thread=False, split_args_with = None, admin_only = False, historize = True, template = None):
        if not hasattr(func, '_jabberbot_command'): # don't override generated functions
            setattr(func, '_jabberbot_command', True)
            setattr(func, '_jabberbot_command_hidden', hidden)
            setattr(func, '_jabberbot_command_name', name or func.__name__)
            setattr(func, '_jabberbot_command_split_args_with', split_args_with)
            setattr(func, '_jabberbot_command_admin_only', admin_only)
            setattr(func, '_jabberbot_command_historize', historize)
            setattr(func, '_jabberbot_command_thread', thread) # Experimental!
            setattr(func, '_jabberbot_command_template', template) # Experimental!
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
