from errbot.backends.test import FullStackTest
from os import path


class TestMentions(FullStackTest):

    def setUp(self, *args, **kwargs):
        kwargs['extra_plugin_dir'] = path.join(path.dirname(
            path.realpath(__file__)), 'mention_plugin')
        super().setUp(*args, **kwargs)

    def test_foreign_mention(self):
        self.assertCommand('I am telling you something @toto', 'Somebody mentioned toto!')

    def test_self_mention(self):
        self.assertCommand('I am telling you something @Err', 'Somebody mentioned me!')
