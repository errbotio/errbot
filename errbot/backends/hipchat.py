from errbot.backends.xmpp import XMPPBackend, XMPPConnection


class HipchatClient(XMPPConnection):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.debug = kwargs.pop('debug')
        super(HipchatClient, self).__init__(*args, **kwargs)


# It is just a different mode for the moment
class HipchatBackend(XMPPBackend):
    def __init__(self, username, password, token=None):
        self.api_token = token
        self.password = password
        super(HipchatBackend, self).__init__(username, password)

    def create_connection(self):
        return HipchatClient(self.jid, password=self.password, debug=[], token=self.api_token)

    @property
    def mode(self):
        return 'hipchat'
