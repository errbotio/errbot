from errbot.backends.test import FullStackTest, pushMessage, popMessage
import requests


class TestWebhooks(FullStackTest):
    @classmethod
    def setUpClass(cls):
        super(TestWebhooks, cls).setUpClass()
        pushMessage("!config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
        popMessage()

    def test_404(self):
        self.assertEquals(requests.post('http://localhost:3141/randomness_blah', "{'toto': 'titui'}").status_code, 404)

    def test_webserver_ok(self):
        pushMessage("!webstatus")
        self.assertIn("echo", popMessage())

    def test_plain_json(self):
        self.assertEquals(requests.post('http://localhost:3141/echo/', '{"toto": "titui"}').text, "{'toto': 'titui'}")  # yes as it takes a json and gives back the python representation as string


    def test_form(self):
        payload = {'toto': 'titui'}
        self.assertEquals(requests.post('http://localhost:3141/echo/', data=payload).text, "{'toto': 'titui'}")  # yes as it takes a json and gives back the python representation as string
