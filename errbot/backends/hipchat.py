from errbot.backends.jabber import JabberBot

# It is just a different mode for the moment
class HipchatBot(JabberBot):
    @property
    def mode(self):
        return 'hipchat'

