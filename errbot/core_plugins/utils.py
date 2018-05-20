from os import path

from errbot import BotPlugin, botcmd


def tail(f, window=20):
    return ''.join(f.readlines()[-window:])


class Utils(BotPlugin):

    # noinspection PyUnusedLocal
    @botcmd
    def echo(self, _, args):
        """ A simple echo command. Useful for encoding tests etc ...
        """
        return args

    @botcmd
    def whoami(self, msg, args):
        """ A simple command echoing the details of your identifier. Useful to debug identity problems.
        """
        if args:
            frm = self.build_identifier(str(args).strip('"'))
        else:
            frm = msg.frm
        resp = "| key      | value\n"
        resp += "| -------- | --------\n"
        resp += f"| person   | `{frm.person}`\n"
        resp += f"| nick     | `{frm.nick}`\n"
        resp += f"| fullname | `{frm.fullname}`\n"
        resp += f"| client   | `{frm.client}`\n\n"

        #  extra info if it is a MUC
        if hasattr(frm, 'room'):
            resp += f"\n`room` is {frm.room}\n"
        resp += f"\n\n- string representation is '{frm}'\n"
        resp += f"- class is '{frm.__class__.__name__}'\n"

        return resp

    # noinspection PyUnusedLocal
    @botcmd(historize=False)
    def history(self, msg, args):
        """display the command history"""
        answer = []
        user_cmd_history = self._bot.cmd_history[msg.frm.person]
        length = len(user_cmd_history)
        for i in range(0, length):
            c = user_cmd_history[i]
            answer.append(f'{length - i:2d}:{self._bot.prefix}{c[0]} {c[1]}')
        return '\n'.join(answer)

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def log_tail(self, msg, args):
        """ Display a tail of the log of n lines or 40 by default
        use : !log tail 10
        """
        n = 40
        if args.isdigit():
            n = int(args)

        if self.bot_config.BOT_LOG_FILE:
            with open(self.bot_config.BOT_LOG_FILE) as f:
                return '```\n' + tail(f, n) + '\n```'
        return 'No log is configured, please define BOT_LOG_FILE in config.py'

    @botcmd
    def render_test(self, _, args):
        """ Tests / showcases the markdown rendering on your current backend
        """
        with open(path.join(path.dirname(path.realpath(__file__)), 'test.md')) as f:
            return f.read()
