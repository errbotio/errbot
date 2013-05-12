import requests
import os
import logging
import json
from errbot.backends.test import FullStackTest, pushMessage, popMessage
from errbot import PY2
from time import sleep

PYTHONOBJECT = ['foo', {'bar': ('baz', None, 1.0, 2)}]
JSONOBJECT = json.dumps(PYTHONOBJECT)


class TestWebhooks(FullStackTest):
    @classmethod
    def setUpClass(cls, extra_test_file=None):
        plugin_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'webhooks_tests'
        super(TestWebhooks, cls).setUpClass(extra_test_file=plugin_dir)

        pushMessage("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        popMessage()

    def test_webserver_plugin_ok(self):
        pushMessage("!webstatus")
        self.assertIn("echo", popMessage())

    def test_not_configured_url_returns_404(self):
        self.assertEquals(requests.post('http://localhost:3141/randomness_blah', "{'toto': 'titui'}").status_code, 404)

    def test_json_is_automatically_decoded(self):
        self.assertEquals(requests.post('http://localhost:3141/webhook1/', JSONOBJECT).text, repr(json.loads(JSONOBJECT)))

    def test_json_on_custom_url_is_automatically_decoded(self):
        self.assertEquals(requests.post('http://localhost:3141/custom_webhook/', JSONOBJECT).text, repr(json.loads(JSONOBJECT)))

    def test_post_form_data_on_webhook_without_form_param_is_automatically_decoded(self):
        self.assertEquals(requests.post('http://localhost:3141/webhook1/', data=JSONOBJECT).text, repr(json.loads(JSONOBJECT)))

    def test_post_form_data_on_webhook_with_custom_url_and_without_form_param_is_automatically_decoded(self):
        self.assertEquals(requests.post('http://localhost:3141/custom_webhook/', data=JSONOBJECT).text, repr(json.loads(JSONOBJECT)))

    def test_webhooks_with_form_parameter_decode_json_automatically(self):
        form = {'form': JSONOBJECT}
        self.assertEquals(requests.post('http://localhost:3141/form/', data=form).text, repr(json.loads(JSONOBJECT)))

    def test_webhooks_with_form_parameter_on_custom_url_decode_json_automatically(self):
        form = {'form': JSONOBJECT}
        self.assertEquals(requests.post('http://localhost:3141/custom_form/', data=form).text, repr(json.loads(JSONOBJECT)))
