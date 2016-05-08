# -*- coding: utf-8 -*-
# vim: ts=4:sw=4
import logging
import sys
from time import sleep
import re

from ansi.color import fg, fx
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import get_lexer_by_name

from errbot import err
from errbot.rendering import ansi, text, xhtml, imtext
from errbot.rendering.ansiext import enable_format, ANSI_CHRS, AnsiExtension
from errbot.backends.base import Message, Presence, ONLINE, OFFLINE, Room
from errbot.backends.test import TestPerson
from errbot.errBot import ErrBot

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
        self.demo_mode = self.bot_config.TEXT_DEMO_MODE if hasattr(self.bot_config, 'TEXT_DEMO_MODE') else False
        self._rooms = set()
        if not self.demo_mode:
            self.md_html = xhtml()  # for more debug feedback on md
            self.md_text = text()  # for more debug feedback on md
            self.md_borderless_ansi = borderless_ansi()
            self.md_im = imtext()
            self.md_lexer = get_lexer_by_name("md", stripall=True)

        self.md_ansi = ansi()
        self.html_lexer = get_lexer_by_name("html", stripall=True)
        self.terminal_formatter = Terminal256Formatter(style='paraiso-dark')
        self.user = self.build_identifier(self.bot_config.BOT_ADMINS[0])

    def serve_forever(self):
        if self.demo_mode:
            # disable the console logging once it is serving in demo mode.
            root = logging.getLogger()
            root.removeHandler(err.console_hdlr)
            root.addHandler(logging.NullHandler())
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(Presence(identifier=self.user, status=ONLINE))
        try:
            while True:
                if ANSI or self.demo_mode:
                    entry = input('\n' + str(fg.cyan) + ' >>> ' + str(fx.reset))
                else:
                    entry = input('\n>>> ')
                msg = Message(entry)
                msg.frm = self.user
                msg.to = self.bot_identifier
                self.callback_message(msg)

                mentioned = [self.build_identifier(word[1:]) for word in re.findall(r"@[\w']+", entry)
                             if word.startswith('@')]
                if mentioned:
                    self.callback_mention(msg, mentioned)

                sleep(.5)
        except EOFError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            # simulate some real presence
            self.callback_presence(Presence(identifier=self.user, status=OFFLINE))
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def send_message(self, mess):
        if self.demo_mode:
            print(self.md_ansi.convert(mess.body))
        else:
            bar = '\n╌╌[{mode}]' + ('╌' * 60)
            super().send_message(mess)
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
        if text_representation.startswith('#'):
            return self.query_room(test_representation[1:])
        return TestPerson(text_representation)

    def build_reply(self, mess, text=None, private=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        response.to = mess.frm
        return response

    @property
    def mode(self):
        return 'text'

    def query_room(self, room):
        text_room = TextRoom(room)
        self._rooms.add(text_room)
        return text_room

    def rooms(self):
        return self._rooms

    def prefix_groupchat_reply(self, message, identifier):
        message.body = '@{0} {1}'.format(identifier.nick, message.body)


class TextRoom(Room):

    def __init__(self, name):
        self.topic_ = ''
        self.joined_ = False
        self.name = name

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

    def __str__(self):
        return self.name
