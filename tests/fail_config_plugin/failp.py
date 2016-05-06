from errbot import BotPlugin
from errbot.utils import ValidationException


class FailP(BotPlugin):
    """
    Just a plugin failing at config time.
    """
    def get_configuration_template(self):
        return {'One': 1, 'Two': 2}

    def check_configuration(self, configuration):
        raise ValidationException('Message explaning why it failed.')
