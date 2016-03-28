from __future__ import absolute_import
from errbot import BotPlugin, botcmd, re_botcmd, arg_botcmd


class Test(BotPlugin):
    """Just a test plugin to see if _err_botcmd_syntax is consistent on all types of botcmd
    """
    @botcmd     # no syntax
    def foo_nosyntax(self, msg, args):
        pass

    @botcmd(syntax='[optional] <mandatory>')
    def foo(self, msg, args):
        pass

    @re_botcmd(pattern=r".*")
    def re_foo(self, msg, match):
        pass

    @arg_botcmd('value', type=str)
    @arg_botcmd('--repeat-count', dest='repeat', type=int, default=2)
    def arg_foo(self, msg, value=None, repeat=None):
        return value * repeat
