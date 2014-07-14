import json
import logging
import os
import requests
import socket
from time import sleep

import pytest

from errbot.backends.test import testbot, push_message, pop_message

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


@pytest.fixture(autouse=True)
def webserver(testbot):
    push_message("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
    pop_message()
    while not webserver_ready('localhost', 3141):
        logging.debug("Webserver not ready yet, sleeping 0.1 second")
        sleep(0.1)


class TestWebhooks(object):
    extra_plugin_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'webhooks_tests'

    def test_not_configured_url_returns_404(self, testbot):
        assert requests.post(
            'http://localhost:3141/randomness_blah',
            "{'toto': 'titui'}"
        ).status_code == 404

    def test_webserver_plugin_ok(self, testbot):
        push_message("!webstatus")
        assert "/echo/" in pop_message()

    def test_json_is_automatically_decoded(self):
        assert requests.post(
            'http://localhost:3141/webhook1/',
            JSONOBJECT
        ).text == repr(json.loads(JSONOBJECT))

    def test_json_on_custom_url_is_automatically_decoded(self):
        assert requests.post(
            'http://localhost:3141/custom_webhook/',
            JSONOBJECT
        ).text == repr(json.loads(JSONOBJECT))

    def test_post_form_data_on_webhook_without_form_param_is_automatically_decoded(self):
        assert requests.post(
            'http://localhost:3141/webhook1/',
            data=JSONOBJECT
        ).text == repr(json.loads(JSONOBJECT))

    def test_post_form_data_on_webhook_with_custom_url_and_without_form_param_is_automatically_decoded(self):
        assert requests.post(
            'http://localhost:3141/custom_webhook/',
            data=JSONOBJECT
        ).text == repr(json.loads(JSONOBJECT))

    def test_webhooks_with_form_parameter_decode_json_automatically(self):
        form = {'form': JSONOBJECT}
        assert requests.post(
            'http://localhost:3141/form/',
            data=form
        ).text == repr(json.loads(JSONOBJECT))

    def test_webhooks_with_form_parameter_on_custom_url_decode_json_automatically(self):
        form = {'form': JSONOBJECT}
        assert requests.post(
            'http://localhost:3141/custom_form/',
            data=form
        ).text, repr(json.loads(JSONOBJECT))

    def test_webhooks_with_raw_request(self):
        form = {'form': JSONOBJECT}
        assert requests.post(
            'http://localhost:3141/raw/',
            data=form
        ).text == "<class 'bottle.LocalRequest'>"

    def test_generate_certificate_creates_usable_cert(self):
        from config import BOT_DATA_DIR
        key_path = os.sep.join((BOT_DATA_DIR, "webserver_key.pem"))
        cert_path = os.sep.join((BOT_DATA_DIR, "webserver_certificate.pem"))

        push_message("!generate_certificate")
        assert "Generating" in pop_message(timeout=1)

        # Generating a certificate could be slow on weak hardware, so keep a safe
        # timeout on the first pop_message()
        assert "successfully generated" in pop_message(timeout=60)
        assert "is recommended" in pop_message(timeout=1)
        assert key_path in pop_message(timeout=1)

        webserver_config = {
            'HOST': 'localhost',
            'PORT': 3141,
            'SSL': {
                'certificate': cert_path,
                'key': key_path,
                'host': 'localhost',
                'port': 3142,
                'enabled': True,
            }
        }
        push_message("!config Webserver {!r}".format(webserver_config))
        pop_message()

        while not webserver_ready('localhost', 3142):
            logging.debug("Webserver not ready yet, sleeping 0.1 second")
            sleep(0.1)

        assert requests.post(
            'https://localhost:3142/webhook1/',
            JSONOBJECT,
            verify=False
        ).text == repr(json.loads(JSONOBJECT))
