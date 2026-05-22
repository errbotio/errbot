from errbot import BotPlugin, botcmd

class CollisionA(BotPlugin):
    @botcmd(template='collision')
    def test_a(self, msg, args):
        return {'name': 'PluginA'}

    @botcmd
    def test_manual(self, msg, args):
        self.send_templated(msg.frm, 'collision', {'name': 'PluginA'})
