from __future__ import absolute_import
from errbot import BotPlugin, botcmd, re_botcmd, arg_botcmd


class Test(BotPlugin):
    @botcmd
    def test_template1(self, msg, args):
        self.send_templated(msg.frm, 'test', {'variable': 'ok'})

    @botcmd(template='test')
    def test_template2(self, msg, args):
        return {'variable': 'ok'}
