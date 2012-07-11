import logging
import config
import sys
from PySide import QtCore, QtGui, QtWebKit

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
        vbox = QtGui.QVBoxLayout()
        self.input = QtGui.QLineEdit()
        self.output = QtWebKit.QWebView()
        
        # init webpage
        self.buffer = '<html><head><link rel="stylesheet" type="text/css" href="%s/style/style.css" /></head><body>' %\
          (QtCore.QUrl.fromLocalFile(config.BOT_DATA_DIR).toString())
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