from __future__ import absolute_import
from errbot import BotPlugin, botcmd, re_botcmd, arg_botcmd


class Test(BotPlugin):
    @botcmd
    def test_template1(self, msg, args):
        self.send_templated(msg.frm, 'test', {'variable': 'ok'})

    @botcmd(template='test')
    def test_template2(self, msg, args):
        return {'variable': 'ok'}

    @botcmd(template='test')
    def test_template3(self, msg, args):
        yield {'variable': 'ok'}

    @arg_botcmd('my_var', type=str, template='test')
    def test_template4(self, msg, my_var=None):
        return {'variable': 'ok'}
