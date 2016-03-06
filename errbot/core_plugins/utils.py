from os import path

from errbot import BotPlugin, botcmd
from errbot.utils import tail


class Utils(BotPlugin):

    # noinspection PyUnusedLocal
    @botcmd
    def echo(self, mess, args):
        """ A simple echo command. Useful for encoding tests etc ...
        """
        return args

    @botcmd
    def whoami(self, mess, args):
        """ A simple command echoing the details of your identifier. Useful to debug identity problems.
        """
        if args:
            frm = self.build_identifier(str(args).strip('"'))
        else:
            frm = mess.frm
        resp = "| key      | value\n"
        resp += "| -------- | --------\n"
        resp += "| person   | `%s`\n" % frm.person
        resp += "| nick     | `%s`\n" % frm.nick
        resp += "| fullname | `%s`\n" % frm.fullname
        resp += "| client   | `%s`\n\n" % frm.client

        #  extra info if it is a MUC
        if hasattr(frm, 'room'):
            resp += "\n`room` is %s\n" % frm.room
        resp += "\n\n- string representation is '%s'\n" % frm
        resp += "- class is '%s'\n" % frm.__class__.__name__

        return resp

    # noinspection PyUnusedLocal
    @botcmd(historize=False)
    def history(self, mess, args):
        """display the command history"""
        answer = []
        user_cmd_history = self._bot.cmd_history[mess.frm.person]
        l = len(user_cmd_history)
        for i in range(0, l):
            c = user_cmd_history[i]
            answer.append('%2i:%s%s %s' % (l - i, self._bot.prefix, c[0], c[1]))
        return '\n'.join(answer)

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def log_tail(self, mess, args):
        """ Display a tail of the log of n lines or 40 by default
        use : !log tail 10
        """
        # admin_only(mess)  # uncomment if paranoid.
        n = 40
        if args.isdigit():
            n = int(args)

        if self.bot_config.BOT_LOG_FILE:
            with open(self.bot_config.BOT_LOG_FILE) as f:
                return '```\n' + tail(f, n) + '\n```'
        return 'No log is configured, please define BOT_LOG_FILE in config.py'

    @botcmd
    def render_test(self, mess, args):
        """ Tests / showcases the markdown rendering on your current backend
        """
        with open(path.join(path.dirname(path.realpath(__file__)), 'test.md')) as f:
            return f.read()
