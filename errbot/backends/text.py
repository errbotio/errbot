# -*- coding: utf-8 -*-
# vim: ts=4:sw=4
import logging
import sys
from time import sleep

from ansi.color import fg, fx
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import get_lexer_by_name

from errbot.rendering import ansi, text, xhtml, imtext
from errbot.rendering.ansi import enable_format, ANSI_CHRS, AnsiExtension
from errbot.backends.base import Message, Presence, ONLINE, OFFLINE, MUCRoom
from errbot.backends.test import TestIdentifier
from errbot.errBot import ErrBot
from errbot.utils import deprecated

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

# Can't use __name__ because of Yapsy
log = logging.getLogger('errbot.backends.text')

ENCODING_INPUT = sys.stdin.encoding
ANSI = hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()


enable_format('borderless', ANSI_CHRS, borders=False)


def borderless_ansi():
    """This makes a converter from markdown to ansi (console) format.
    It can be called like this:
    from errbot.rendering import ansi
    md_converter = ansi()  # you need to cache the converter

    ansi_txt = md_converter.convert(md_txt)
    """
    md = Markdown(output_format='borderless', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


class TextBackend(ErrBot):
    def __init__(self, config):
        super().__init__(config)
        log.debug("Text Backend Init.")
        self.bot_identifier = self.build_identifier('Err')
        self._rooms = set()
        self.md_html = xhtml()  # for more debug feedback on md
        self.md_text = text()  # for more debug feedback on md
        self.md_ansi = ansi()
        self.md_borderless_ansi = borderless_ansi()
        self.md_im = imtext()
        self.md_lexer = get_lexer_by_name("md", stripall=True)
        self.html_lexer = get_lexer_by_name("html", stripall=True)
        self.terminal_formatter = Terminal256Formatter(style='paraiso-dark')

    def serve_forever(self):
        me = self.build_identifier(self.bot_config.BOT_ADMINS[0])
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(Presence(identifier=me, status=ONLINE))
        try:
            while True:
                if ANSI:
                    entry = input('\n' + str(fg.cyan) + ' >>> ' + str(fx.reset))
                else:
                    entry = input('\n>>> ')
                msg = Message(entry)
                msg.frm = me
                msg.to = self.bot_identifier
                self.callback_message(msg)
                sleep(.5)
        except EOFError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            # simulate some real presence
            self.callback_presence(Presence(identifier=me, status=OFFLINE))
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def send_message(self, mess):
        bar = '\n╌╌[{mode}]' + ('╌' * 60)
        super(TextBackend, self).send_message(mess)
        print(bar.format(mode='MD  '))
        if ANSI:
            print(highlight(mess.body, self.md_lexer, self.terminal_formatter))
        else:
            print(mess.body)
        print(bar.format(mode='HTML'))
        html = self.md_html.convert(mess.body)
        if ANSI:
            print(highlight(html, self.html_lexer, self.terminal_formatter))
        else:
            print(html)
        print(bar.format(mode='TEXT'))
        print(self.md_text.convert(mess.body))
        print(bar.format(mode='IM  '))
        print(self.md_im.convert(mess.body))
        if ANSI:
            print(bar.format(mode='ANSI'))
            print(self.md_ansi.convert(mess.body))
            print(bar.format(mode='BORDERLESS'))
            print(self.md_borderless_ansi.convert(mess.body))
        print('\n\n')

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        log.debug("*** Changed presence to [%s] %s", (status, message))

    def build_identifier(self, text_representation):
        return TestIdentifier(text_representation)

    def build_reply(self, mess, text=None, private=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        response.to = mess.frm
        response.type = 'chat' if private else mess.type
        return response

    @deprecated
    def join_room(self, room, username=None, password=None):
        return self.query_room(room)

    @property
    def mode(self):
        return 'text'

    def query_room(self, room):
        room = TextMUCRoom()
        self._rooms.add(room)
        return room

    def rooms(self):
        return self._rooms

    def prefix_groupchat_reply(self, message, identifier):
        message.body = '{0} {1}'.format(identifier.nick, message.body)


class TextMUCRoom(MUCRoom):

    def __init__(self):
        self.topic_ = ''
        self.joined_ = False

    def join(self, username=None, password=None):
        self.joined_ = True

    def leave(self, reason=None):
        self.joined_ = False

    def create(self):
        self.joined_ = True

    def destroy(self):
        self.joined_ = False

    @property
    def exists(self):
        return True

    @property
    def joined(self):
        return self.joined_

    @property
    def topic(self):
        return self.topic_

    @topic.setter
    def topic(self, topic):
        self.topic_ = topic

    @property
    def occupants(self):
        return [self.build_identifier("Somebody")]

    def invite(self, *args):
        pass
