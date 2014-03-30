import logging
import sys
import re

PY3 = sys.version_info[0] == 3
PY2 = not PY3

__all__ = ['BotPlugin', 'webhook', 'webroute', 'webview']

from errbot.botplugin import BotPlugin  # repeat it here for convenience and coherence with @botcmd
from errbot.builtins.wsview import webhook, route, view  # idem repeat here the webhook feature for convenience to expose webhooks


webroute = route  # this allows plugins to expose dynamic webpages on err embedded webserver
webview = view  # this allows to use the templating system


def botcmd(*args, **kwargs):
    """Decorator for bot command functions
    extra parameters to customize the command:
    name : override the command name
    split_args_with : prepare the arguments by splitting them by the given character
    """

    def decorate(func, hidden=False, name=None, split_args_with='', admin_only=False, historize=True, template=None):
        if not hasattr(func, '_err_command'):  # don't override generated functions
            setattr(func, '_err_command', True)
            setattr(func, '_err_re_command', False)
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


def re_botcmd(*args, **kwargs):
    """
    Decorator for bot regex-based command functions

    Pattern is the regular expression pattern to match on
    Flags corresponds with the flags parameter on re.compile()

    Use prefixed=False when this bot command does not require a prefix in
    order to trigger.
    Other parameters are the same as with :func:`errbot.botcmd`
    """

    def decorate(func, pattern, flags=0, prefixed=True, hidden=False, name=None, admin_only=False, historize=True, template=None):
        if not hasattr(func, '_err_command'):  # don't override generated functions
            setattr(func, '_err_command', True)
            setattr(func, '_err_re_command', True)
            setattr(func, '_err_command_re_pattern', re.compile(pattern, flags=flags))
            setattr(func, '_err_command_prefix_required', prefixed)
            setattr(func, '_err_command_hidden', hidden)
            setattr(func, '_err_command_name', name or func.__name__)
            setattr(func, '_err_command_admin_only', admin_only)
            setattr(func, '_err_command_historize', historize)
            setattr(func, '_err_command_template', template)
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)
