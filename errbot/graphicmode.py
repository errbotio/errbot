import logging
import os
import config
import sys
from PySide import QtCore, QtGui, QtWebKit
from PySide.QtGui import QCompleter
from PySide.QtCore import Qt, QUrl

class CommandBox(QtGui.QLineEdit, object):
    history_index = 0

    def reset_history(self):
        self.history_index = len(self.history)

    def __init__(self, history, commands):
        self.history = history
        self.reset_history()
        super(CommandBox, self).__init__()
        completer = QCompleter(['!' + name for name in commands])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(completer)

    #noinspection PyStringFormat
    def keyPressEvent(self, *args, **kwargs):
        key = args[0].key()
        if key == Qt.Key_Up:
            if self.history_index > 0:
                self.history_index -= 1
                self.setText('!%s %s' % self.history[self.history_index])
                return
        elif key == Qt.Key_Down:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setText('!%s %s' % self.history[self.history_index])
                return
        super(CommandBox, self).keyPressEvent(*args, **kwargs)
        if key == QtCore.Qt.Key_Return:
            self.reset_history()



class JIDMock():
    domain = 'meuh'
    resource = 'bidon'

    def __init__(self, node):
        self.node = node

    def getNode(self):
        return self.node

    def bareMatch(self, whatever):
        return False

    def getStripped(self):
        return self.node


class MessageMock():
    def __init__(self, body):
        self.body = body

    def getType(self):
        return 'chat'

    def getFrom(self):
        return JIDMock(config.BOT_ADMINS[0])

    def getProperties(self):
        return {}

    def getBody(self):
        return self.body

    def getThread(self):
        return None


class ConnectionMock(QtCore.QObject):
    def __init__(self):
        super(ConnectionMock, self).__init__()

    newAnswer = QtCore.Signal(str)

    def send(self, mess):
        if hasattr(mess, 'getBody') and len(mess.getBody()) > 0 and not mess.getBody().isspace():
            self.newAnswer.emit(mess.getBody())


def patch_jabberbot():
    from errbot import jabberbot

    conn = ConnectionMock()

    def send_command(self):
        self.receive_message(self.input.text())
        self.callback_message(conn, MessageMock(self.input.text()))
        self.input.clear()

    def htmlify(text):
        import re

        urlfinder = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')

        def linkify(text):
            def replacewithlink(matchobj):
                url = matchobj.group(0)
                text = unicode(url)
                if text.startswith('http://'):
                    text = text.replace('http://', '', 1)
                elif text.startswith('https://'):
                    text = text.replace('https://', '', 1)

                if text.startswith('www.'):
                    text = text.replace('www.', '', 1)

                imglink = ''
                for a in ['png', '.gif', '.jpg', '.jpeg', '.svg']:
                    if text.lower().endswith(a):
                        imglink = '<br /><img src="' + url + '" />'
                        break
                return '<a class="comurl" href="' + url + '" target="_blank" rel="nofollow">' + text + '<img class="imglink" src="/images/linkout.png"></a>' + imglink

            return urlfinder.sub(replacewithlink, text)

        return '<pre>' + linkify(text) + '</pre>'

    def receive_message(self, text):
        self.buffer += htmlify(text)
        self.output.setHtml(self.buffer)

    def scroll_output_to_bottom(self):
        self.output.page().mainFrame().scroll(0, self.output.page().mainFrame().scrollBarMaximum(QtCore.Qt.Vertical))

    def fake_serve_forever(self):
        self.jid = JIDMock('blah') # whatever
        self.connect() # be sure we are "connected" before the first command

        # create window and components
        app = QtGui.QApplication(sys.argv)
        self.mainW = QtGui.QWidget()
        self.mainW.setWindowTitle('Err...')
        icon_path = os.path.dirname(__file__) + os.sep + 'err.svg'
        bg_path = os.path.dirname(__file__) + os.sep + 'err-bg.svg'
        self.mainW.setWindowIcon(QtGui.QIcon(icon_path))
        vbox = QtGui.QVBoxLayout()
        self.input = CommandBox(self.cmd_history, self.commands)
        self.output = QtWebKit.QWebView()

        # init webpage
        self.buffer = """<html>
                           <head>
                                <link rel="stylesheet" type="text/css" href="%s/style/style.css" />
                           </head>
                           <body style=" background-image: url('%s'); background-repeat: no-repeat; background-position:center center;">
                           """ % (QUrl.fromLocalFile(config.BOT_DATA_DIR).toString(), QUrl.fromLocalFile(bg_path).toString())
        self.output.setHtml(self.buffer)

        # layout
        vbox.addWidget(self.output)
        vbox.addWidget(self.input)
        self.mainW.setLayout(vbox)

        # setup web view to open liks in external browser
        self.output.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)

        # connect signals/slots
        self.output.page().mainFrame().contentsSizeChanged.connect(self.scroll_output_to_bottom)
        self.output.page().linkClicked.connect(QtGui.QDesktopServices.openUrl)
        self.input.returnPressed.connect(self.send_command)
        self.conn.newAnswer.connect(self.receive_message)

        self.mainW.show()
        app.exec_()

    def fake_connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
            self.activate_non_started_plugins()
            logging.info('Notifying connection to all the plugins...')
            self.signal_connect_to_all_plugins()
            logging.info('Plugin activation done.')
        return self.conn

    jabberbot.JabberBot.send_command = send_command
    jabberbot.JabberBot.receive_message = receive_message
    jabberbot.JabberBot.serve_forever = fake_serve_forever
    jabberbot.JabberBot.scroll_output_to_bottom = scroll_output_to_bottom
    jabberbot.JabberBot.connect = fake_connect