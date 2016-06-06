from errbot import BotPlugin, PY3


class Config(BotPlugin):
    """
    Just a plugin with a simple string config.
    """
    def get_configuration_template(self):
        if PY3:
            return {'One': 'one'}
        return {'One'.encode('utf-8'): 'one'.encode('utf-8')}  # forces bytes on py2 for the test
