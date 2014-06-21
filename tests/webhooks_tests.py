import requests
import socket
import os
import logging
import json
from errbot.backends.test import FullStackTest, pushMessage, popMessage
from errbot import PY2
from time import sleep
from config import BOT_DATA_DIR

PYTHONOBJECT = ['foo', {'bar': ('baz', None, 1.0, 2)}]
JSONOBJECT = json.dumps(PYTHONOBJECT)

def webserver_ready(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return True
    except:
        return False


class TestWebhooks(FullStackTest):

    def setUp(self, extra_test_file=None):
        plugin_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'webhooks_tests'
        super(TestWebhooks, TestWebhooks).setUp(self, extra_test_file=plugin_dir)

        pushMessage("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        popMessage()
        while not webserver_ready('localhost', 3141):
            logging.debug("Webserver not ready yet, sleeping 0.1 second")
            sleep(0.1)

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

    def test_webhooks_with_raw_request(self):
        form = {'form': JSONOBJECT}
        self.assertEquals(requests.post('http://localhost:3141/raw/', data=form).text, "<class 'bottle.LocalRequest'>")

    def test_generate_certificate_creates_usable_cert(self):
        key_path = os.sep.join((BOT_DATA_DIR, "webserver_key.pem"))
        cert_path = os.sep.join((BOT_DATA_DIR, "webserver_certificate.pem"))

        pushMessage("!generate_certificate")
        self.assertTrue("Generating" in popMessage(timeout=1))

        # Generating a certificate could be slow on weak hardware, so keep a safe
        # timeout on the first popMessage()
        self.assertTrue("successfully generated" in popMessage(timeout=60))
        self.assertTrue("is recommended" in popMessage(timeout=1))
        self.assertTrue(key_path in popMessage(timeout=1))

        pushMessage("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL': {'certificate': '%s', 'key': '%s', 'host': 'localhost', 'port': 3142, 'enabled': True}}" % (cert_path, key_path))
        popMessage()

        while not webserver_ready('localhost', 3142):
            logging.debug("Webserver not ready yet, sleeping 0.1 second")
            sleep(0.1)

        self.assertEquals(
            requests.post('https://localhost:3142/webhook1/', JSONOBJECT, verify=False).text,
            repr(json.loads(JSONOBJECT))
        )
