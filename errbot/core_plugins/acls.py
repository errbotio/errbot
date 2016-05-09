import fnmatch
from errbot import BotPlugin, cmdfilter
from errbot.backends.base import RoomOccupant
from errbot.utils import compat_str, is_str


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
    if is_str(patterns):
        patterns = (patterns,)
    return any(fnmatch.fnmatchcase(compat_str(text), compat_str(pattern)) for pattern in patterns)


def ciglob(text, patterns):
    """
    Case-insensitive version of glob.

    Match text against the list of patterns according to unix glob rules.
    Return True if a match is found, False otherwise.
    """
    if is_str(patterns):
        patterns = (patterns,)
    return glob(text.lower(), [p.lower() for p in patterns])


class ACLS(BotPlugin):
    """ This checks commands for potential ACL violations.
    """

    def access_denied(self, msg, reason, dry_run):
        if not dry_run and not self.bot_config.HIDE_RESTRICTED_ACCESS:
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
        f = self._bot.all_commands[cmd]
        cmd_str = "{plugin}:{command}".format(
            plugin=type(f.__self__).__name__,
            command=cmd,
        )

        usr = get_acl_usr(msg)
        acl = self.bot_config.ACCESS_CONTROLS_DEFAULT.copy()
        for pattern, acls in self.bot_config.ACCESS_CONTROLS.items():
            if ':' not in pattern:
                pattern = '*:{command}'.format(command=pattern)
            if ciglob(cmd_str, (pattern,)):
                acl.update(acls)
                break

        self.log.info("Matching ACL %s against username %s for command %s" % (acl, usr, cmd_str))

        if 'allowusers' in acl and not glob(usr, acl['allowusers']):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)
        if 'denyusers' in acl and glob(usr, acl['denyusers']):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)
        if msg.is_group:
            if not isinstance(msg.frm, RoomOccupant):
                raise Exception('msg.frm is not a RoomOccupant. Class of frm: %s' % msg.frm.__class__)
            room = str(msg.frm.room)
            if 'allowmuc' in acl and acl['allowmuc'] is False:
                return self.access_denied(msg, "You're not allowed to access this command from a chatroom", dry_run)

            if 'allowrooms' in acl and not glob(room, acl['allowrooms']):
                return self.access_denied(msg, "You're not allowed to access this command from this room", dry_run)

            if 'denyrooms' in acl and glob(room, acl['denyrooms']):
                return self.access_denied(msg, "You're not allowed to access this command from this room", dry_run)
        elif 'allowprivate' in acl and acl['allowprivate'] is False:
            return self.access_denied(
                    msg,
                    "You're not allowed to access this command via private message to me",
                    dry_run
            )

        self.log.info("Check if %s is admin only command." % cmd)
        if f._err_command_admin_only:
            if not glob(get_acl_usr(msg), self.bot_config.BOT_ADMINS):
                return self.access_denied(msg, "This command requires bot-admin privileges", dry_run)
            # For security reasons, admin-only commands are direct-message only UNLESS
            # specifically overridden by setting allowmuc to True for such commands.
            if msg.is_group and not acl.get("allowmuc", False):
                return self.access_denied(msg, "This command may only be issued through a direct message", dry_run)

        return msg, cmd, args
