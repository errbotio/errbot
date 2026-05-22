from errbot import BotPlugin, botcmd

class CollisionB(BotPlugin):
    @botcmd(template='collision')
    def test_b(self, msg, args):
        return {'name': 'PluginB'}
