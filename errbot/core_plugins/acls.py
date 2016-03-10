import fnmatch
from errbot import BotPlugin, cmdfilter
from errbot.backends.base import RoomOccupant
from errbot.utils import compat_str


BLOCK_COMMAND = (None, None, None)


def get_acl_usr(msg):
    if hasattr(msg.frm, 'aclattr'):  # if the identity requires a special field to be used for acl
        return msg.frm.aclattr
    return msg.frm.person  # default


def glob(text, patterns):
    """
    Match text against the list of patterns according to unix glob rules.
    Return True if a match is found, False otherwise.
    """
    return any(fnmatch.fnmatchcase(compat_str(text), compat_str(pattern)) for pattern in patterns)


def ciglob(text, patterns):
    """
    Case-insensitive version of glob.

    Match text against the list of patterns according to unix glob rules.
    Return True if a match is found, False otherwise.
    """
    return glob(text.lower(), [p.lower() for p in patterns])


class ACLS(BotPlugin):
    """ This checks commands for potential ACL violations.
    """

    def access_denied(self, msg, reason, dry_run):
        if not dry_run or not self.bot_config.HIDE_RESTRICTED_ACCESS:
            self._bot.send_simple_reply(msg, reason)
        return BLOCK_COMMAND

    @cmdfilter
    def acls(self, msg, cmd, args, dry_run):
        """
        Check command against ACL rules

        :param msg: The original message the commands is coming from.
        :param cmd: The command name
        :param args: Its arguments.
        :param dry_run: pass True to not act on the check (messages / deferred auth etc.)

        Return None, None, None if the command is blocked or deferred
        """
        self.log.debug("Check %s for ACLs." % cmd)

        usr = get_acl_usr(msg)

        self.log.debug("Matching ACLs against username %s" % usr)

        if cmd not in self.bot_config.ACCESS_CONTROLS:
            self.bot_config.ACCESS_CONTROLS[cmd] = self.bot_config.ACCESS_CONTROLS_DEFAULT

        if ('allowusers' in self.bot_config.ACCESS_CONTROLS[cmd] and not
           glob(usr, self.bot_config.ACCESS_CONTROLS[cmd]['allowusers'])):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)

        if ('denyusers' in self.bot_config.ACCESS_CONTROLS[cmd] and
           glob(usr, self.bot_config.ACCESS_CONTROLS[cmd]['denyusers'])):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)

        if msg.is_group:
            if not isinstance(msg.frm, RoomOccupant):
                raise Exception('msg.frm is not a RoomOccupant Class of frm : %s' % msg.frm.__class__)
            room = str(msg.frm.room)
            if ('allowmuc' in self.bot_config.ACCESS_CONTROLS[cmd] and
               self.bot_config.ACCESS_CONTROLS[cmd]['allowmuc'] is False):
                return self.access_denied(msg, "You're not allowed to access this command from a chatroom", dry_run)

            if ('allowrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and not
               glob(room, self.bot_config.ACCESS_CONTROLS[cmd]['allowrooms'])):
                return self.access_denied(msg, "You're not allowed to access this command from this room", dry_run)

            if ('denyrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and
               glob(room, self.bot_config.ACCESS_CONTROLS[cmd]['denyrooms'])):
                return self.access_denied(msg, "You're not allowed to access this command from this room", dry_run)

        elif ('allowprivate' in self.bot_config.ACCESS_CONTROLS[cmd] and
              self.bot_config.ACCESS_CONTROLS[cmd]['allowprivate'] is False):
            return self.access_denied(
                    msg,
                    "You're not allowed to access this command via private message to me", dry_run)

        return msg, cmd, args

    @cmdfilter
    def admin(self, msg, cmd, args, dry_run):
        """
        Check command against the is_admin criteria.

        :param msg: The original message the commands is coming from.
        :param cmd: The command name
        :param args: Its arguments.
        :param dry_run: pass True to not act on the check (messages / deferred auth etc.)

        """
        self.log.info("Check if %s is admin only command." % cmd)
        f = self._bot.all_commands[cmd]

        if f._err_command_admin_only:
            if msg.is_group:
                return self.access_denied(
                        msg,
                        "You cannot administer the bot from a chatroom, message the bot directly", dry_run)

            if not glob(get_acl_usr(msg), self.bot_config.BOT_ADMINS):
                return self.access_denied(msg, "This command requires bot-admin privileges", dry_run)

        return msg, cmd, args
