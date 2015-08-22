from errbot import BotPlugin, cmdfilter
from errbot.backends.base import ACLViolation


def get_acl_usr(msg):
    if hasattr(msg.frm, 'aclattr'):  # if the identity requires a special field to be used for acl
        return msg.frm.aclattr
    return msg.frm.person  # default


class ACLS(BotPlugin):
    """ This checks commands for potential ACL violations.
    """
    @cmdfilter
    def acls(self, msg, cmd, args):
        """
        Check command against ACL rules

        Raises ACLViolation() if the command may not be executed in the given context
        """
        self.log.info("Check %s for ACLs." % cmd)

        usr = get_acl_usr(msg)
        typ = msg.type

        if cmd not in self.bot_config.ACCESS_CONTROLS:
            self.bot_config.ACCESS_CONTROLS[cmd] = self.bot_config.ACCESS_CONTROLS_DEFAULT

        if ('allowusers' in self.bot_config.ACCESS_CONTROLS[cmd] and
           usr not in self.bot_config.ACCESS_CONTROLS[cmd]['allowusers']):
            raise ACLViolation("You're not allowed to access this command from this user")
        if ('denyusers' in self.bot_config.ACCESS_CONTROLS[cmd] and
           usr in self.bot_config.ACCESS_CONTROLS[cmd]['denyusers']):
            raise ACLViolation("You're not allowed to access this command from this user")
        if typ == 'groupchat':
            if not hasattr(msg.frm, 'room'):
                raise Exception('msg.frm is not a MUCIdentifier as it misses the "room" property. Class of frm : %s'
                                % msg.frm.__class__)
            room = str(msg.frm.room)
            if ('allowmuc' in self.bot_config.ACCESS_CONTROLS[cmd] and
               self.bot_config.ACCESS_CONTROLS[cmd]['allowmuc'] is False):
                raise ACLViolation("You're not allowed to access this command from a chatroom")
            if ('allowrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and
               room not in self.bot_config.ACCESS_CONTROLS[cmd]['allowrooms']):
                raise ACLViolation("You're not allowed to access this command from this room")
            if ('denyrooms' in self.bot_config.ACCESS_CONTROLS[cmd] and
               room in self.bot_config.ACCESS_CONTROLS[cmd]['denyrooms']):
                raise ACLViolation("You're not allowed to access this command from this room")
        else:
            if ('allowprivate' in self.bot_config.ACCESS_CONTROLS[cmd] and
               self.bot_config.ACCESS_CONTROLS[cmd]['allowprivate'] is False):
                raise ACLViolation("You're not allowed to access this command via private message to me")

        return msg, cmd, args

    @cmdfilter
    def admin(self, msg, cmd, args):
        self.log.info("Check if %s is admin only command." % cmd)
        f = self._bot.commands[cmd] if cmd in self._bot.commands else self._bot.re_commands[cmd]

        if f._err_command_admin_only:
            if msg.type == 'groupchat':
                raise ACLViolation("You cannot administer the bot from a chatroom, message the bot directly")

            if get_acl_usr(msg) not in self.bot_config.BOT_ADMINS:
                raise ACLViolation("This command requires bot-admin privileges")
        return msg, cmd, args
