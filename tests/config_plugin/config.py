from errbot import BotPlugin


class Config(BotPlugin):
    """
    Just a plugin with a simple string config.
    """

    def get_configuration_template(self):
        return {"One": "one"}
