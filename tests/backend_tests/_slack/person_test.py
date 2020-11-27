import sys
import unittest
import logging
import os
from tempfile import mkdtemp
from mock import MagicMock

from errbot.backends._slack.person import *


log = logging.getLogger(__name__)


class SlackPersonTests(unittest.TestCase):

    def setUp(self):
        self.webClient = MagicMock()
        self.userid = 'Utest_user_id'
        self.channelid= 'Ctest_channel_id'
        self.p = SlackPerson(self.webClient, userid=self.userid, channelid=self.channelid)

    def test_username(self):
        self.webClient.users_info.return_value = {'user': {'name': 'test_username'}}
        self.assertEqual(self.p.username, 'test_username')
        self.assertEqual(self.p.username, 'test_username')
        self.webClient.users_info.assert_called_once_with(user=self.userid)

    def test_username_not_found(self):
        self.webClient.users_info.return_value = {'user': None}
        self.assertEqual(self.p.username, '<Utest_user_id>')
        self.assertEqual(self.p.username, '<Utest_user_id>')
        self.webClient.users_info.assert_called_with(user=self.userid)
        self.assertEqual(self.webClient.users_info.call_count, 2)
