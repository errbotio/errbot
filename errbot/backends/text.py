import logging
import sys
from time import sleep
import re

import copyreg
from ansi.color import fg, fx
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import get_lexer_by_name

from errbot.rendering import ansi, text, xhtml, imtext
from errbot.rendering.ansiext import enable_format, ANSI_CHRS, AnsiExtension
from errbot.backends.base import Message, Person, Presence, ONLINE, OFFLINE, Room, RoomOccupant
from errbot.core import ErrBot
from errbot.logs import console_hdlr

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

log = logging.getLogger(__name__)

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


class TextPerson(Person):
    """
    Simple Person implementation which represents users as simple text strings.
    """

    def __init__(self, person, client=None, nick=None, fullname=None):
        self._person = person
        self._client = client
        self._nick = nick
        self._fullname = fullname

    @property
    def person(self):
        return self._person

    @property
    def client(self):
        return self._client

    @property
    def nick(self):
        return self._nick

    @property
    def fullname(self):
        return self._fullname

    @property
    def aclattr(self):
        return str(self)

    def __str__(self):
        return '@' + self._person

    def __eq__(self, other):
        if not isinstance(other, Person):
            return False
        return self.person == other.person

    def __hash__(self):
        return self.person.__hash__()


class TextRoom(Room):

    def __init__(self, name, bot):
        self._topic = ''
        self._joined = False
        self.name = name
        self._bot = bot

        # fill up the room with a coherent set of identities.
        self._occupants = [TextOccupant('somebody', self),
                           TextOccupant(TextPerson(bot.bot_config.BOT_ADMINS[0]), self),
                           TextOccupant(bot.bot_identifier, self)]

    def join(self, username=None, password=None):
        self._joined = True

    def leave(self, reason=None):
        self._joined = False

    def create(self):
        self._joined = True

    def destroy(self):
        self._joined = False

    @property
    def exists(self):
        return True

    @property
    def joined(self):
        return self._joined

    @property
    def topic(self):
        return self._topic

    @topic.setter
    def topic(self, topic):
        self._topic = topic

    @property
    def occupants(self):
        return self._occupants

    def invite(self, *args):
        pass

    def __str__(self):
        return '#' + self.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


class TextOccupant(TextPerson, RoomOccupant):

    def __init__(self, person, room):
        super().__init__(person)
        self._room = room

    @property
    def room(self):
        return self._room

    def __str__(self):
        return f'#{self._room.name}/{self._person.person}'

    def __eq__(self, other):
        return self.person == other.person and self.room == other.room

    def __hash__(self):
        return self.person.__hash__() + self.room.__hash__()


INTRO = """
---
You start as a **bot admin in a one-on-one conversation** with the bot.

### Context of the chat

- Use `!inroom`{:color='blue'} to switch to a room conversation.
- Use `!inperson`{:color='blue'} to switch back to a one-on-one conversation.
- Use `!asuser`{:color='green'} to talk as a normal user.
- Use `!asadmin`{:color='red'} to switch back as a bot admin.

### Preferences

- Use `!ml`{:color='yellow'} to flip on/off the multiline mode (Enter twice at the end to send).

---
"""


class TextBackend(ErrBot):
    def __init__(self, config):
        super().__init__(config)
        log.debug("Text Backend Init.")

        if hasattr(self.bot_config, 'BOT_IDENTITY') and 'username' in self.bot_config.BOT_IDENTITY:
            self.bot_identifier = self.build_identifier(self.bot_config.BOT_IDENTITY['username'])
        else:
            # Just a default identity for the bot if nothing has been specified.
            self.bot_identifier = self.build_identifier('@errbot')

        log.debug('Bot username set at %s.', self.bot_identifier)
        self._inroom = False
        self._rooms = []
        self._multiline = False

        self.demo_mode = self.bot_config.TEXT_DEMO_MODE if hasattr(self.bot_config, 'TEXT_DEMO_MODE') else False
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
        self._register_identifiers_pickling()

    @staticmethod
    def _unpickle_identifier(identifier_str):
        return TextBackend.__build_identifier(identifier_str)

    @staticmethod
    def _pickle_identifier(identifier):
        return TextBackend._unpickle_identifier, (str(identifier),)

    def _register_identifiers_pickling(self):
        """
        Register identifiers pickling.
        """
        TextBackend.__build_identifier = self.build_identifier
        for cls in (TextPerson, TextOccupant, TextRoom):
            copyreg.pickle(cls, TextBackend._pickle_identifier, TextBackend._unpickle_identifier)

    def serve_forever(self):
        self.readline_support()

        if not self._rooms:
            # artificially join a room if None were specified.
            self.query_room('#testroom').join()

        if self.demo_mode:
            # disable the console logging once it is serving in demo mode.
            root = logging.getLogger()
            root.removeHandler(console_hdlr)
            root.addHandler(logging.NullHandler())
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(Presence(identifier=self.user, status=ONLINE))

        self.send_message(Message(INTRO))

        try:
            while True:

                if self._inroom:
                    frm = TextOccupant(self.user, self.rooms[0])
                    to = self.rooms[0]
                else:
                    frm = self.user
                    to = self.bot_identifier

                print()
                full_msg = ''
                while True:
                    prompt = '[␍] ' if full_msg else '>>> '
                    if ANSI or self.demo_mode:
                        color = fg.red if self.user.person in self.bot_config.BOT_ADMINS[0] else fg.green
                        prompt = f'{color}[{frm} ➡ {to}] {fg.cyan}{prompt}{fx.reset}'
                        entry = input(prompt)
                    else:
                        entry = input(f'[{frm} ➡ {to}] {prompt}')

                    if not self._multiline:
                        full_msg = entry
                        break

                    if not entry:
                        break

                    full_msg += entry + '\n'

                msg = Message(full_msg)
                msg.frm = frm
                msg.to = to

                self.callback_message(msg)

                mentioned = [self.build_identifier(word) for word in re.findall(r'(?<=\s)@[\w]+', entry)]
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

    def readline_support(self):
        try:
            # Load readline for better editing/history behaviour
            import readline

            # Implement a simple completer for commands
            def completer(txt, state):
                options = [i for i in self.all_commands if i.startswith(txt)] if txt else list(self.all_commands.keys())
                if state < len(options):
                    return options[state]

            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer)

        except ImportError:
            # Readline is Unix-only
            log.debug("Python readline module is not available")

    def send_message(self, msg):
        if self.demo_mode:
            print(self.md_ansi.convert(msg.body))
        else:
            bar = '\n╌╌[{mode}]' + ('╌' * 60)
            super().send_message(msg)
            print(bar.format(mode='MD  '))
            if ANSI:
                print(highlight(msg.body, self.md_lexer, self.terminal_formatter))
            else:
                print(msg.body)
            print(bar.format(mode='HTML'))
            html = self.md_html.convert(msg.body)
            if ANSI:
                print(highlight(html, self.html_lexer, self.terminal_formatter))
            else:
                print(html)
            print(bar.format(mode='TEXT'))
            print(self.md_text.convert(msg.body))
            print(bar.format(mode='IM  '))
            print(self.md_im.convert(msg.body))
            if ANSI:
                print(bar.format(mode='ANSI'))
                print(self.md_ansi.convert(msg.body))
                print(bar.format(mode='BORDERLESS'))
                print(self.md_borderless_ansi.convert(msg.body))
            print('\n\n')

    def add_reaction(self, msg: Message, reaction: str) -> None:
        # this is like the Slack backend's add_reaction
        self._react('+', msg, reaction)

    def remove_reaction(self, msg: Message, reaction: str) -> None:
        self._react('-', msg, reaction)

    def _react(self, sign, msg, reaction):
        self.send(msg.frm, f'reaction {sign}:{reaction}:', in_reply_to=msg)

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        log.debug("*** Changed presence to [%s] %s", (status, message))

    def build_identifier(self, text_representation):
        if text_representation.startswith('#'):
            rem = text_representation[1:]
            if '/' in text_representation:
                room, person = rem.split('/')
                return TextOccupant(TextPerson(person), TextRoom(room, self))
            return self.query_room('#' + rem)
        if not text_representation.startswith('@'):
            raise ValueError('An identifier for the Text backend needs to start with # for a room or @ for a person.')
        return TextPerson(text_representation[1:])

    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        if private:
            response.to = msg.frm
        else:
            response.to = msg.frm.room if isinstance(msg.frm, RoomOccupant) else msg.frm
        return response

    @property
    def mode(self):
        return 'text'

    def query_room(self, room):
        if not room.startswith('#'):
            raise ValueError('A Room name must start by #.')
        text_room = TextRoom(room[1:], self)
        if text_room not in self._rooms:
            self._rooms.insert(0, text_room)
        else:
            self._rooms.insert(0, self._rooms.pop(self._rooms.index(text_room)))
        return text_room

    @property
    def rooms(self):
        return self._rooms

    def prefix_groupchat_reply(self, message, identifier):
        message.body = f'{identifier.person} {message.body}'
