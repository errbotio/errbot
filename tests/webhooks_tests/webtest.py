import logging
from errbot import BotPlugin
from errbot.core_plugins.webserver import webhook
from bottle import abort, response

log = logging.getLogger(__name__)


class WebTest(BotPlugin):
    @webhook
    def webhook1(self, payload):
        log.debug(str(payload))
        return str(payload)

    @webhook(r'/custom_webhook')
    def webhook2(self, payload):
        log.debug(str(payload))
        return str(payload)

    @webhook(r'/form', form_param='form')
    def webhook3(self, payload):
        log.debug(str(payload))
        return str(payload)

    @webhook(r'/custom_form', form_param='form')
    def webhook4(self, payload):
        log.debug(str(payload))
        return str(payload)

    @webhook(r'/raw', raw=True)
    def webhook5(self, payload):
        log.debug(str(payload))
        return str(type(payload))

    @webhook
    def webhook6(self, payload):
        log.debug(str(payload))
        response.set_header("X-Powered-By", "Err")
        return str(payload)

    @webhook
    def webhook7(self, payload):
        abort(403, "Forbidden")
