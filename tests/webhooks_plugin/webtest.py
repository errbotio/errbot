import logging
from errbot import BotPlugin
from errbot.core_plugins.webserver import webhook
from flask import abort, after_this_request

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

        @after_this_request
        def add_header(response):
            response.headers['X-Powered-By'] = 'Errbot'
            return response
        return str(payload)

    @webhook
    def webhook7(self, payload):
        abort(403, "Forbidden")

    webhook8 = webhook(r'/lambda')(lambda x, y: str(x) + str(y))

    # Just to test https://github.com/errbotio/errbot/issues/1043
    @webhook(raw=True)
    def raw2(self, payload):
        log.debug(str(payload))
        return str(type(payload))
