import logging
import sys

PY3 = sys.version_info[0] == 3
PY2 = not PY3

__all__ = ['BotPlugin', 'webhook', 'webroute', 'webview']

# Import some stuff here so that it's easier to access them
from errbot.decorators import botcmd, re_botcmd, webhook
from errbot.botplugin import BotPlugin
from errbot.builtins.wsview import route, view


webroute = route  # this allows plugins to expose dynamic webpages on err embedded webserver
webview = view  # this allows to use the templating system


