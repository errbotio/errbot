import logging
import sys
from errbot.utils import mess_2_embeddablehtml, utf8

try:
    from PySide import QtCore, QtGui, QtWebKit
    from PySide.QtGui import QCompleter
    from PySide.QtCore import Qt, QUrl
except ImportError:
    logging.exception("Could not start the graphical backend")
    logging.fatal("""
    If you intend to use the graphical backend please install PySide:
    -> On debian-like systems
    sudo apt-get install python-software-properties
    sudo apt-get update
    sudo apt-get install python-pyside
    -> On Gentoo
    sudo emerge -av dev-python/pyside
    -> Generic
    pip install PySide
    """)
    sys.exit(-1)

import os
import config
from config import BOT_DATA_DIR, BOT_PREFIX
import errbot
from errbot.backends.base import Connection, Message, build_text_html_message_pair
from errbot.errBot import ErrBot


class CommandBox(QtGui.QPlainTextEdit, object):
    newCommand = QtCore.Signal(str)

    def reset_history(self):
        self.history_index = len(self.history)

    def __init__(self, history, commands):
        self.history_index = 0
        self.history = history
        self.reset_history()
        super(CommandBox, self).__init__()

        #Autocompleter
        self.completer = QCompleter([BOT_PREFIX + name for name in commands], self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.activated.connect(self.onAutoComplete)
        self.autocompleteStart = None

    def onAutoComplete(self, text):
        #Select the text from autocompleteStart until the current cursor
        cursor = self.textCursor()
        cursor.setPosition(0, cursor.KeepAnchor)
        #Replace it with the selected text
        cursor.insertText(text)
        self.autocompleteStart = None

    #noinspection PyStringFormat
    def keyPressEvent(self, *args, **kwargs):
        event = args[0]
        key = event.key()
        ctrl = event.modifiers() == QtCore.Qt.ControlModifier

        # don't disturb the completer behavior
        if self.completer.popup().isVisible() and key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab, Qt.Key_Backtab):
            event.ignore()
            return

        if self.autocompleteStart is not None and not event.text().isalnum() and \
                not (key == Qt.Key_Backspace and self.textCursor().position() > self.autocompleteStart):
            self.completer.popup().hide()
            self.autocompleteStart = None

        if key == Qt.Key_Space and ctrl:
            #Pop-up the autocompleteList
            rect = self.cursorRect(self.textCursor())
            rect.setSize(QtCore.QSize(100, 150))
            self.autocompleteStart = self.textCursor().position()
            self.completer.complete(rect)  # The popup is positioned in the next if block

        if self.autocompleteStart:
            prefix = self.toPlainText()
            cur = self.textCursor()
            cur.setPosition(self.autocompleteStart)

            self.completer.setCompletionPrefix(prefix)
            #Select the first one of the matches
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        if key == Qt.Key_Up and ctrl:
            if self.history_index > 0:
                self.history_index -= 1
                self.setPlainText(BOT_PREFIX + '%s %s' % self.history[self.history_index])
                key.ignore()
                return
        elif key == Qt.Key_Down and ctrl:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setPlainText(BOT_PREFIX + '%s %s' % self.history[self.history_index])
                key.ignore()
                return
        elif key == QtCore.Qt.Key_Return and ctrl:
            self.newCommand.emit(self.toPlainText())
            self.reset_history()
        super(CommandBox, self).keyPressEvent(*args, **kwargs)


class ConnectionMock(Connection, QtCore.QObject):
    newAnswer = QtCore.Signal(str, bool)

    def send_message(self, mess):
        self.send(mess)

    def send(self, mess):
        if hasattr(mess, 'getBody') and mess.getBody() and not mess.getBody().isspace():
            content, is_html = mess_2_embeddablehtml(mess)
            self.newAnswer.emit(content, is_html)


import re

urlfinder = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')


def linkify(text):
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = chr(url)

        imglink = ''
        for a in ['png', '.gif', '.jpg', '.jpeg', '.svg']:
            if text.lower().endswith(a):
                imglink = '<br /><img src="' + url + '" />'
                break
        return '<a href="' + url + '" target="_blank" rel="nofollow">' + text + '<img class="imglink" src="/images/linkout.png"></a>' + imglink

    return urlfinder.sub(replacewithlink, text)


def htmlify(text, is_html, receiving):
    tag = 'div' if is_html else 'pre'
    if not is_html:
        text = linkify(text)
    style = 'background-color : rgba(251,247,243,0.5); border-color:rgba(251,227,223,0.5);' if receiving else 'background-color : rgba(243,247,251,0.5); border-color: rgba(223,227,251,0.5);'
    return '<%s style="margin:0px; padding:20px; border-style:solid; border-width: 0px 0px 1px 0px; %s"> %s </%s>' % (tag, style, text, tag)

INIT_PAGE = """<html><head><link rel="stylesheet" type="text/css" href="%s/style/style.css" /></head>
<body style=" background-image: url('%s'); background-repeat: no-repeat; background-position:center center; background-attachment:fixed; background-size: contain; margin:0;">"""


class GraphicBackend(ErrBot):
    conn = ConnectionMock()

    def send_command(self, text):
        self.new_message(text, False)
        msg = Message(text)
        msg.setFrom(config.BOT_ADMINS[0])  # assume this is the admin talking
        msg.setTo(self.jid)  # To me only
        self.callback_message(self.conn, msg)
        self.input.clear()

    def new_message(self, text, is_html, receiving=True):
        self.buffer += htmlify(text, is_html, receiving)
        self.output.setHtml(self.buffer)

    def scroll_output_to_bottom(self):
        self.output.page().mainFrame().scroll(0, self.output.page().mainFrame().scrollBarMaximum(QtCore.Qt.Vertical))

    def build_message(self, text):
        txt, node = build_text_html_message_pair(text)
        msg = Message(txt, html=node) if node else Message(txt)
        msg.setFrom(self.jid)
        return msg  # rebuild a pure html snippet to include directly in the console html

    def serve_forever(self):
        self.jid = 'Err@localhost'
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured

        # create window and components
        app = QtGui.QApplication(sys.argv)
        self.mainW = QtGui.QWidget()
        self.mainW.setWindowTitle('Err...')
        icon_path = os.path.dirname(errbot.__file__) + os.sep + 'err.svg'
        bg_path = os.path.dirname(errbot.__file__) + os.sep + 'err-bg.svg'
        self.mainW.setWindowIcon(QtGui.QIcon(icon_path))
        vbox = QtGui.QVBoxLayout()
        help = QtGui.QLabel("CTRL+Space to autocomplete -- CTRL+Enter to send your message")
        self.input = CommandBox(self.cmd_history, self.commands)
        self.output = QtWebKit.QWebView()

        # init webpage
        self.buffer = INIT_PAGE % (BOT_DATA_DIR, bg_path)
        self.output.setHtml(self.buffer)

        # layout
        vbox.addWidget(self.output)
        vbox.addWidget(self.input)
        vbox.addWidget(help)
        self.mainW.setLayout(vbox)

        # setup web view to open liks in external browser
        self.output.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)

        # connect signals/slots
        self.output.page().mainFrame().contentsSizeChanged.connect(self.scroll_output_to_bottom)
        self.output.page().linkClicked.connect(QtGui.QDesktopServices.openUrl)
        self.input.newCommand.connect(self.send_command)
        self.conn.newAnswer.connect(self.new_message)

        self.mainW.show()
        try:
            app.exec_()
        finally:
            self.disconnect_callback()
            self.shutdown()
            exit(0)

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
        return self.conn

    def join_room(self, room, username=None, password=None):
        pass  # just ignore that

    def shutdown(self):
        super(GraphicBackend, self).shutdown()

    @property
    def mode(self):
        return 'graphic'
