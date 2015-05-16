import argparse
from functools import wraps
import logging
import re
import shlex

from . import PY2
from .builtins.wsview import bottle_app, WebView


def botcmd(*args, **kwargs):
    """
    Decorator for bot command functions

    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param split_args_with: Automatically split arguments on the given separator.
        Behaviour of this argument is identical to :func:`str.split()`
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The template to use when using XHTML-IM output

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into commands that can be given to the bot. These methods are
    expected to have a signature like the following::

        @botcmd
        def some_command(self, msg, args):
            pass

    The given `msg` will be the full message object that was received, which includes data
    like sender, receiver, the plain-text and html body (if applicable), etc. `args` will
    be a string or list (depending on your value of `split_args_with`) of parameters that
    were given to the command by the user.
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
    Decorator for regex-based bot command functions

    :param pattern: The regular expression a message should match against in order to
        trigger the command.
    :param flags: The `flags` parameter which should be passed to :func:`re.compile()`. This
        allows the expression's behaviour to be modified, such as making it case-insensitive
        for example.
    :param matchall: By default, only the first match of the regular expression is returned
        (as a `re.MatchObject`). When *matchall* is `True`, all non-overlapping matches are
        returned (as a list of `re.MatchObject` items).
    :param prefixed: Requires user input to start with a bot prefix in order for the pattern
        to be applied when `True` (the default).
    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The template to use when using XHTML-IM output

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into commands that can be given to the bot. These methods are
    expected to have a signature like the following::

        @re_botcmd(pattern=r'^some command$')
        def some_command(self, msg, match):
            pass

    The given `msg` will be the full message object that was received, which includes data
    like sender, receiver, the plain-text and html body (if applicable), etc. `match` will
    be a :class:`re.MatchObject` containing the result of applying the regular expression on the
    user's input.
    """

    def decorate(func, pattern, flags=0, matchall=False, prefixed=True, hidden=False, name=None, admin_only=False,
                 historize=True, template=None):
        if not hasattr(func, '_err_command'):  # don't override generated functions
            setattr(func, '_err_command', True)
            setattr(func, '_err_re_command', True)
            setattr(func, '_err_command_re_pattern', re.compile(pattern, flags=flags))
            setattr(func, '_err_command_matchall', matchall)
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



def arg_botcmd(*args, hidden=False, name=None, admin_only=False,
               historize=True, template=None, **kwargs):
    """
    Decorator for argparse-based bot command functions

    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The template to use when using XHTML-IM output
    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into commands that can be given to the bot. These methods are
    expected to have a signature like the following::
        @botcmd
        def some_command(self, msg, args):
            pass
    The given `msg` will be the full message object that was received, which includes data
    like sender, receiver, the plain-text and html body (if applicable), etc. `args` will
    be a string or list (depending on your value of `split_args_with`) of parameters that
    were given to the command by the user.
    """

    def decorator(func):

        if not hasattr(func, '_err_command'):

            err_command_parser = argparse.ArgumentParser(description=func.__doc__)

            @wraps(func)
            def wrapper(self, mess, args):

                args = shlex.split(args)
                parsed_args = err_command_parser.parse_args(args)
                parsed_kwargs = vars(parsed_args)

                return func(self, mess, **parsed_kwargs)

            setattr(wrapper, '_err_command', True)
            setattr(wrapper, '_err_re_command', False)
            setattr(wrapper, '_err_arg_command', True)
            setattr(wrapper, '_err_command_hidden', hidden)
            setattr(wrapper, '_err_command_name', name or wrapper.__name__)
            setattr(wrapper, '_err_command_split_args_with', '')
            setattr(wrapper, '_err_command_admin_only', admin_only)
            setattr(wrapper, '_err_command_historize', historize)
            setattr(wrapper, '_err_command_template', template)
            setattr(wrapper, '_err_command_parser', err_command_parser)

        else:
            # the function has already been wrapped
            # alias it so we can update it's arguments below
            wrapper = func

        wrapper._err_command_parser.add_argument(*args, **kwargs)
        wrapper.__doc__ = wrapper._err_command_parser.format_help()

        return wrapper

    return decorator


def webhook(*args, **kwargs):
    """
    Decorator for webhooks

    :param uri_rule: A regular expression against which the called URL should
        match in order for the webhook to trigger. If left undefined then the URL
        `/<method_name>/` will be used instead.
    :param methods: A tuple of allowed HTTP methods. By default, only GET and POST
        are allowed.
    :param form_param: The key who's contents will be passed to your method's `payload`
        parameter. This is used for example when using the `application/x-www-form-urlencoded`
        mimetype.
    :param raw: Boolean to overrides the request decoding (including form_param) and
        passes the raw http request to your method's `payload`.
        The passed type in payload will provide the BaseRequest interface as defined here:
        http://bottlepy.org/docs/dev/api.html#bottle.BaseRequest

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into webhooks which can be reached on Err's built-in webserver.
    The bundled *Webserver* plugin needs to be configured before these URL's become reachable.

    Methods with this decorator are expected to have a signature like the following::

        @webhook
        def a_webhook(self, payload):
            pass
    """

    def decorate(func, uri_rule, methods=('POST', 'GET'), form_param=None, raw=False):
        logging.info("webhooks:  Bind %s to %s" % (uri_rule, func.__name__))

        for verb in methods:
            bottle_app.route(uri_rule, verb, callback=WebView(func, form_param, raw), name=func.__name__ + '_' + verb)
        return func

    if isinstance(args[0], str) or (PY2 and isinstance(args[0], basestring)):
        return lambda method: decorate(method, args[0], **kwargs)
    return decorate(args[0], '/' + args[0].__name__ + '/', **kwargs)
