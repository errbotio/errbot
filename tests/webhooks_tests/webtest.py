import logging
from errbot import BotPlugin, botcmd
from errbot.builtins.webserver import webhook


class WebTest(BotPlugin):
    @webhook
    def webhook1(self, payload):
        logging.debug(str(payload))
        return str(payload)

    @webhook(r'/custom_webhook/')
    def webhook2(self, payload):
        logging.debug(str(payload))
        return str(payload)

    @webhook(r'/form/', form_param='form')
    def webhook3(self, payload):
        logging.debug(str(payload))
        return str(payload)

    @webhook(r'/custom_form/', form_param='form')
    def webhook4(self, payload):
        logging.debug(str(payload))
        return str(payload)

    @webhook(r'/raw/', raw=True)
    def webhook5(self, payload):
        logging.debug(str(payload))
        return str(type(payload))
