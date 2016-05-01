# coding: utf-8

import argparse
from functools import wraps
import logging
import re
import shlex
import inspect
from typing import Callable, Any, Tuple

from .core_plugins.wsview import bottle_app, WebView
from errbot.backends.base import Message, ONLINE, OFFLINE, AWAY, DND  # noqa
from .utils import compat_str
from .utils import PY2, PY3  # noqa gbin: this is now used by plugins
from .botplugin import BotPlugin, SeparatorArgParser, ShlexArgParser, CommandError, Command  # noqa
from .flow import FlowRoot, BotFlow, Flow, FLOW_END
from .core_plugins.wsview import route, view  # noqa

__all__ = ['BotPlugin', 'CommandError', 'Command', 'webhook', 'webroute', 'webview',
           'botcmd', 're_botcmd', 'arg_botcmd', 'botflow', 'BotFlow', 'FlowRoot', 'Flow', 'FLOW_END']

log = logging.getLogger(__name__)

webroute = route  # this allows plugins to expose dynamic webpages on err embedded webserver
webview = view  # this allows to use the templating system


class ArgumentParseError(Exception):
    """Raised when ArgumentParser couldn't parse given arguments."""


class HelpRequested(Exception):
    """Signals that -h/--help was used and help should be displayed to the user."""


class ArgumentParser(argparse.ArgumentParser):
    """
    The python argparse.ArgumentParser, adapted for use within Err.
    """

    def error(self, message):
        raise ArgumentParseError(message)

    def print_help(self, file=None):
        # Implementation note: Only easy way to do this appears to be
        #   through raising an exception which we can catch later in
        #   a place where we have the ability to return a message to
        #   the user.
        raise HelpRequested()


def _tag_botcmd(func,
                hidden=None,
                name=None,
                split_args_with='',
                admin_only=False,
                historize=True,
                template=None,
                flow_only=False,
                _re=False,
                syntax=None,         # botcmd_only
                pattern=None,        # re_cmd only
                flags=0,              # re_cmd only
                matchall=False,      # re_cmd_only
                prefixed=True,       # re_cmd_only
                _arg=False,
                command_parser=None):  # arg_cmd only
    """
    Mark a method as a bot command.
    """
    if not hasattr(func, '_err_command'):  # don't override generated functions
        func._err_command = True
        func._err_command_name = name or func.__name__
        func._err_command_split_args_with = split_args_with
        func._err_command_admin_only = admin_only
        func._err_command_historize = historize
        func._err_command_template = template
        func._err_command_syntax = syntax
        func._err_command_flow_only = flow_only
        func._err_command_hidden = hidden if hidden is not None else flow_only

        # re_cmd
        func._err_re_command = _re
        if _re:
            func._err_command_re_pattern = re.compile(pattern, flags=flags)
            func._err_command_matchall = matchall
            func._err_command_prefix_required = prefixed
            func._err_command_syntax = pattern

        # arg_cmd
        func._err_arg_command = _arg
        if _arg:
            func._err_command_parser = command_parser
            # func._err_command_syntax is set at wrapping time.
    return func


def botcmd(*args,
           hidden: bool=None,
           name: str=None,
           split_args_with: str='',
           admin_only: bool=False,
           historize: bool=True,
           template: str=None,
           flow_only: bool=False,
           syntax: str=None) -> Callable[[BotPlugin, Message, Any], Any]:
    """
    Decorator for bot command functions

    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param split_args_with: Automatically split arguments on the given separator.
        Behaviour of this argument is identical to :func:`str.split()`
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The markdown template to use.
    :param syntax: The argument syntax you expect for example: '[name] <mandatory>'.
    :param flow_only: Flag this command to be available only when it is part of a flow.
                       If True and hidden is None, it will switch hidden to True.

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
        return _tag_botcmd(func,
                           _re=False,
                           _arg=False,
                           hidden=hidden,
                           name=name or func.__name__,
                           split_args_with=split_args_with,
                           admin_only=admin_only,
                           historize=historize,
                           template=template,
                           syntax=syntax,
                           flow_only=flow_only)
    return decorator(args[0]) if args else decorator


def re_botcmd(*args,
              hidden: bool=None,
              name: str=None,
              admin_only: bool=False,
              historize: bool=True,
              template: str=None,
              pattern: str=None,
              flags: int=0,
              matchall: bool=False,
              prefixed: bool=True,
              flow_only: bool=False) -> Callable[[BotPlugin, Message, Any], Any]:
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
    :param template: The template to use when using markdown output
    :param flow_only: Flag this command to be available only when it is part of a flow.
                       If True and hidden is None, it will switch hidden to True.

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
    def decorator(func):
        return _tag_botcmd(func,
                           _re=True,
                           _arg=False,
                           hidden=hidden,
                           name=name or func.__name__,
                           admin_only=admin_only,
                           historize=historize,
                           template=template,
                           pattern=pattern,
                           flags=flags,
                           matchall=matchall,
                           prefixed=prefixed,
                           flow_only=flow_only)
    return decorator(args[0]) if args else decorator


def botmatch(*args, **kwargs):
    """
    Decorator for regex-based message match.

    :param *args: The regular expression a message should match against in order to
                   trigger the command.
    :param flags: The `flags` parameter which should be passed to :func:`re.compile()`. This
        allows the expression's behaviour to be modified, such as making it case-insensitive
        for example.
    :param matchall: By default, only the first match of the regular expression is returned
        (as a `re.MatchObject`). When *matchall* is `True`, all non-overlapping matches are
        returned (as a list of `re.MatchObject` items).
    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The template to use when using Markdown output.
    :param flow_only: Flag this command to be available only when it is part of a flow.
                       If True and hidden is None, it will switch hidden to True.

    For example::

        @botmatch(r'^(?:Yes|No)$')
        def yes_or_no(self, msg, match):
            pass
    """
    def decorator(func, pattern):
        return _tag_botcmd(func,
                           _re=True,
                           _arg=False,
                           prefixed=False,
                           hidden=kwargs.get('hidden', None),
                           name=kwargs.get('name', func.__name__),
                           admin_only=kwargs.get('admin_only', False),
                           flow_only=kwargs.get('flow_only', False),
                           historize=kwargs.get('historize', True),
                           template=kwargs.get('template', None),
                           pattern=pattern,
                           flags=kwargs.get('flags', 0),
                           matchall=kwargs.get('matchall', False))
    if len(args) == 2:
        return decorator(*args)
    if len(args) == 1:
        return lambda f: decorator(f, args[0])
    raise ValueError("botmatch: You need to pass the pattern as parameter to the decorator.")


def arg_botcmd(*args,
               hidden: bool=None,
               name: str=None,
               admin_only: bool=False,
               historize: bool=True,
               template: str=None,
               flow_only: bool=False,
               unpack_args: bool=True,
               **kwargs) -> Callable[[BotPlugin, Message, Any], Any]:
    """
    Decorator for argparse-based bot command functions

    https://docs.python.org/3/library/argparse.html

    This decorator creates an argparse.ArgumentParser and uses it to parse the commands arguments.

    This decorator can be used multiple times to specify multiple arguments.

    Any valid argparse.add_argument() parameters can be passed into the decorator.
    Each time this decorator is used it adds a new argparse argument to the command.

    :param hidden: Prevents the command from being shown by the built-in help command when `True`.
    :param name: The name to give to the command. Defaults to name of the function itself.
    :param admin_only: Only allow the command to be executed by admins when `True`.
    :param historize: Store the command in the history list (`!history`). This is enabled
        by default.
    :param template: The template to use when using markdown output
    :param flow_only: Flag this command to be available only when it is part of a flow.
                       If True and hidden is None, it will switch hidden to True.
    :param unpack_args: Should the argparser arguments be "unpacked" and passed on the the bot
        command individually? If this is True (the default) you must define all arguments in the
        function separately. If this is False you must define a single argument `args` (or
        whichever name you prefer) to receive the result of `ArgumentParser.parse_args()`.

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into commands that can be given to the bot. The methods will be called
    with the original msg and the argparse parsed arguments. These methods are
    expected to have a signature like the following (assuming `unpack_args=True`)::

        @arg_botcmd('value', type=str)
        @arg_botcmd('--repeat-count', dest='repeat', type=int, default=2)
        def repeat_the_value(self, msg, value=None, repeat=None):
            return value * repeat

    The given `msg` will be the full message object that was received, which includes data
    like sender, receiver, the plain-text and html body (if applicable), etc.
    `value` will hold the value passed in place of the `value` argument and
    `repeat` will hold the value passed in place of the `--repeat-count` argument.

    If you don't like this automatic *"unpacking"* of the arguments,
    you can use `unpack_args=False` like this::

        @arg_botcmd('value', type=str)
        @arg_botcmd('--repeat-count', dest='repeat', type=int, default=2, unpack_args=False)
        def repeat_the_value(self, msg, args):
            return arg.value * args.repeat

    .. note::
        The `unpack_args=False` only needs to be specified once, on the bottom `@args_botcmd`
        statement.
    """

    def decorator(func):

        if not hasattr(func, '_err_command'):

            err_command_parser = ArgumentParser(
                prog=name or func.__name__,
                description=func.__doc__,
            )

            @wraps(func)
            def wrapper(self, mess, args):

                # Some clients automatically convert consecutive dashes into a fancy
                # hyphen, which breaks long-form arguments. Undo this conversion to
                # provide a better user experience.
                args = shlex.split(args.replace('—', '--'))
                try:
                    parsed_args = err_command_parser.parse_args(args)
                except ArgumentParseError as e:
                    yield "I'm sorry, I couldn't parse that; %s" % e
                    yield err_command_parser.format_usage()
                    return
                except HelpRequested:
                    yield err_command_parser.format_help()
                    return

                if unpack_args:
                    func_args = []
                    func_kwargs = vars(parsed_args)
                else:
                    func_args = [parsed_args]
                    func_kwargs = {}

                if inspect.isgeneratorfunction(func):
                    for reply in func(self, mess, *func_args, **func_kwargs):
                        yield reply
                else:
                    yield func(self, mess, *func_args, **func_kwargs)

            _tag_botcmd(wrapper,
                        _re=False,
                        _arg=True,
                        hidden=hidden,
                        name=name or wrapper.__name__,
                        admin_only=admin_only,
                        historize=historize,
                        template=template,
                        flow_only=flow_only,
                        command_parser=err_command_parser)
        else:
            # the function has already been wrapped
            # alias it so we can update it's arguments below
            wrapper = func

        wrapper._err_command_parser.add_argument(*args, **kwargs)
        wrapper.__doc__ = wrapper._err_command_parser.format_help()
        format = wrapper._err_command_parser.format_usage()
        wrapper._err_command_syntax = format[len('usage: ')+len(wrapper._err_command_parser.prog)+1:-1]

        return wrapper

    return decorator


def _tag_webhook(func, uri_rule, methods, form_param, raw):
    log.info("webhooks:  Flag to bind %s to %s" % (uri_rule, func.__name__))
    func._err_webhook_uri_rule = uri_rule
    func._err_webhook_methods = methods
    func._err_webhook_form_param = form_param
    func._err_webhook_raw = raw
    return func


def webhook(*args,
            methods: Tuple[str]=('POST', 'GET'),
            form_param: str=None,
            raw: bool=False) -> Callable[[BotPlugin, Any], str]:
    """
    Decorator for webhooks

    :param uri_rule:
        The URL to use for this webhook, as per Bottle request routing syntax.
        For more information, see:

        * http://bottlepy.org/docs/dev/tutorial.html#request-routing
        * http://bottlepy.org/docs/dev/routing.html
    :param methods:
        A tuple of allowed HTTP methods. By default, only GET and POST
        are allowed.
    :param form_param:
        The key who's contents will be passed to your method's `payload` parameter.
        This is used for example when using the `application/x-www-form-urlencoded`
        mimetype.
    :param raw:
        When set to true, this overrides the request decoding (including form_param) and
        passes the raw http request to your method's `payload` parameter.
        The value of payload will be a Bottle
        `BaseRequest <http://bottlepy.org/docs/dev/api.html#bottle.BaseRequest>`_.

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into webhooks which can be reached on Err's built-in webserver.
    The bundled *Webserver* plugin needs to be configured before these URL's become reachable.

    Methods with this decorator are expected to have a signature like the following::

        @webhook
        def a_webhook(self, payload):
            pass
    """

    if isinstance(args[0], (str, bytes)):  # first param is uri_rule.
        return lambda func: _tag_webhook(func,
                                         compat_str(args[0]).rstrip('/'),  # trailing / is also be stripped on incoming.
                                         methods=methods,
                                         form_param=form_param,
                                         raw=raw)
    return _tag_webhook(args[0],
                        r'/' + args[0].__name__,
                        methods=methods,
                        form_param=form_param,
                        raw=raw)


def cmdfilter(*args, **kwargs):
    """
    Decorator for command filters.

    This decorator should be applied to methods of :class:`~errbot.botplugin.BotPlugin`
    classes to turn them into command filters.

    These filters are executed just before the execution of a command and provide
    the means to add features such as custom security, logging, auditing, etc.

    These methods are expected to have a signature and a return a tuple like the following::

        @cmdfilter
        def some_command(self, msg, cmd, args, dry_run):
            # if dry_run, it should just filter without acting on it (sending message, asking for an OTP etc...)
            # or return None, None, None to defer its execution.
            # otherwise can modify msg, cmd or args and return:
            return msg, cmd, args

    """
    def decorate(func):
        if not hasattr(func, '_err_command_filter'):  # don't override generated functions
            func._err_command_filter = True
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    return lambda func: decorate(func)


def botflow(*args, **kwargs):
    """
    Decorator for flow of commands.

    TODO(gbin): example / docs
    """
    def decorate(func):
        if not hasattr(func, '_err_flow'):  # don't override generated functions
            func._err_flow = True
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    return lambda func: decorate(func)
