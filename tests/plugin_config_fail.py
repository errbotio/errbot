from os import path

from errbot.backends.test import FullStackTest


class FailedConfigTest(FullStackTest):

    def setUp(self, *args, **kwargs):
        kwargs['extra_plugin_dir'] = path.join(path.dirname(
            path.realpath(__file__)), 'fail_config_plugin')

        super().setUp(*args, **kwargs)

    def test_failed_config(self):
        self.assertCommand('!plugin config Failp {}',
                           'Incorrect plugin configuration: Message explaning why it failed.')
