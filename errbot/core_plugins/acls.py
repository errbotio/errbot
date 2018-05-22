import fnmatch
from errbot import BotPlugin, cmdfilter
from errbot.backends.base import RoomOccupant

BLOCK_COMMAND = (None, None, None)


def get_acl_usr(msg):
    """Return the ACL attribute of the sender of the given message"""
    if hasattr(msg.frm, 'aclattr'):  # if the identity requires a special field to be used for acl
        return msg.frm.aclattr
    return msg.frm.person  # default


def glob(text, patterns):
    """
    Match text against the list of patterns according to unix glob rules.
    Return True if a match is found, False otherwise.
    """
    if isinstance(patterns, str):
        patterns = (patterns,)
    if not isinstance(text, str):
        text = str(text)
    return any(fnmatch.fnmatchcase(text, str(pattern)) for pattern in patterns)


def ciglob(text, patterns):
    """
    Case-insensitive version of glob.

    Match text against the list of patterns according to unix glob rules.
    Return True if a match is found, False otherwise.
    """
    if isinstance(patterns, str):
        patterns = (patterns,)
    return glob(text.lower(), [p.lower() for p in patterns])


class ACLS(BotPlugin):
    """
    This plugin implements access controls for commands, allowing them to be
    restricted via various rules.
    """

    def access_denied(self, msg, reason, dry_run):
        if not dry_run and not self.bot_config.HIDE_RESTRICTED_ACCESS:
            self._bot.send_simple_reply(msg, reason)
        return BLOCK_COMMAND

    @cmdfilter
    def acls(self, msg, cmd, args, dry_run):
        """
        Check command against ACL rules as defined in the bot configuration.

        :param msg: The original chat message.
        :param cmd: The command name itself.
        :param args: Arguments passed to the command.
        :param dry_run: True when this is a dry-run.
        """
        self.log.debug('Check %s for ACLs.', cmd)
        f = self._bot.all_commands[cmd]
        cmd_str = f'{f.__self__.name}:{cmd}'

        usr = get_acl_usr(msg)
        acl = self.bot_config.ACCESS_CONTROLS_DEFAULT.copy()
        for pattern, acls in self.bot_config.ACCESS_CONTROLS.items():
            if ':' not in pattern:
                pattern = f'*:{pattern}'
            if ciglob(cmd_str, (pattern,)):
                acl.update(acls)
                break

        self.log.info('Matching ACL %s against username %s for command %s.', acl, usr, cmd_str)

        if 'allowusers' in acl and not glob(usr, acl['allowusers']):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)
        if 'denyusers' in acl and glob(usr, acl['denyusers']):
            return self.access_denied(msg, "You're not allowed to access this command from this user", dry_run)
        if msg.is_group:
            if not isinstance(msg.frm, RoomOccupant):
                raise Exception(f'msg.frm is not a RoomOccupant. Class of frm: {msg.frm.__class__}')
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

        self.log.info('Check if %s is admin only command.', cmd)
        if f._err_command_admin_only:
            if not glob(get_acl_usr(msg), self.bot_config.BOT_ADMINS):
                return self.access_denied(msg, 'This command requires bot-admin privileges', dry_run)
            # For security reasons, admin-only commands are direct-message only UNLESS
            # specifically overridden by setting allowmuc to True for such commands.
            if msg.is_group and not acl.get('allowmuc', False):
                return self.access_denied(msg, 'This command may only be issued through a direct message', dry_run)

        return msg, cmd, args
