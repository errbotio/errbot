from __future__ import absolute_import
from errbot import BotPlugin, botcmd, Command, botmatch


def say_foo(plugin, msg, args):
    return 'foo %s' % type(plugin)


class Dyna(BotPlugin):
    """Just a test plugin to see if synamic plugin API works.
    """
    @botcmd
    def add_simple(self, _, _1):
        simple1 = Command(lambda plugin, msg, args: 'yep %s' % type(plugin), name='say_yep')
        simple2 = Command(say_foo)

        self.create_dynamic_plugin('simple', (simple1, simple2))

        return 'added'

    @botcmd
    def remove_simple(self, msg, args):
        self.destroy_dynamic_plugin('simple')
        return 'removed'

    @botcmd
    def add_re(self, _, _1):
        re1 = Command(lambda plugin, msg, match: 'fffound',
                      name='ffound',
                      cmd_type=botmatch,
                      cmd_args=(r'^.*cheese.*$',))
        self.create_dynamic_plugin('re', (re1, ))
        return 'added'

    @botcmd
    def remove_re(self, msg, args):
        self.destroy_dynamic_plugin('re')
        return 'removed'

    @botcmd
    def add_saw(self, _, _1):
        re1 = Command(lambda plugin, msg, args: '+'.join(args),
                      name='splitme',
                      cmd_type=botcmd,
                      cmd_kwargs={'split_args_with': ','})
        self.create_dynamic_plugin('saw', (re1, ))
        return 'added'

    @botcmd
    def remove_saw(self, msg, args):
        self.destroy_dynamic_plugin('saw')
        return 'removed'
