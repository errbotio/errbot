# -*- coding=utf-8 -*-
from errbot import BotPlugin, botcmd


class I18nTest(BotPlugin):
    """A Just a test plugin to see if it is picked up."""

    @botcmd
    def i18n_1(self, msg, args):
        return "язы́к"

    @botcmd(name="ру́сский")
    def i18n_2(self, msg, args):
        return "OK"

    @botcmd(name="prefix_ру́сский")
    def i18n_3(self, msg, args):
        return "OK"

    @botcmd(name="ру́сский_suffix")
    def i18n_4(self, msg, args):
        return "OK"
