#!/usr/bin/env python

# vim: ts=4:sw=4
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import logging
import curses

import os

# makes it compatible with tmux under iterm2
if os.environ['TERM'] == 'screen-256color':
    os.environ['TERM'] = 'xterm-256color'

from npyscreen import *  # noqa
from errbot.wizard.gce import API  # noqa

log = logging.getLogger(__name__)


BLURB = """This is a simple wizard to configure Errbot.

If you need advanced features like an external backend,
    please use the manual installation procedure.
"""

GCE_BLURB = 'Please authorize the access to your GCE project from your import browser.'

BACKENDS = ['Slack', 'Hipchat', 'Telegram', 'XMPP', 'IRC']

BACKEND_BLURBS = {
    'Slack': """
In Order to get your token:

From the main chatting page (https://$TEAM.slack.com/messages/general/,
  with $TEAM is the name of your team.)

  - click on the left menu, select 'Configure Integrations',
  - under the section 'DIY Integrations & Customization': 'Bots' click View,
  - Enter a Username for your Bot and click 'Add Bot Integration'.

  You will see an API Token in Integration settings starting by 'xoxb-',
  copy paste it here.
""",
    'Hipchat': """
In Order to get a user, password and API token for the bot:

From the admin page (https://$TEAM.hipchat.com/admin/,
  with $TEAM is the name of your team.)

  - click on the top menu 'Group Admin',
  - Under the 'Users' section click Add,

  From there put an email so so can finish up the setup of the user for the bot.

  The username will be in the form 24926_143886@chat.hipchat.com where 24926
  can be found by clicking on a room in Rooms, this is the first part of the XMPP JID
  (for example 24926_err@conf.hipchat.com)

  143886 can be found in the url when you click on the user of the bot in the User section
  (for example https://err.hipchat.com/admin/user/143886)

  Full name must be exactly what you find in the Full name field on that page.

  Then, on the API section, Create a new Token of type Admin.
  It will look like b2325324f189f9929027a37f6c99aa3.
  """}


Form.FIX_MINIMUM_SIZE_WHEN_CREATED = False


class ActionFormHelp(ActionForm):
    def create(self):
        super().create()
        self.help = '[TAB] next field\n[shift-TAB] prev field\n[Return] to select\n[q or ESC] Quit'

    def set_up_handlers(self):
        super().set_up_handlers()
        self.handlers['q'] = self.quit
        self.handlers[curses.ascii.ESC] = self.quit

    def quit(self, ev=None):
        if notify_ok_cancel(title='Quit?', message='Do you really want to quit?'):
            self.parentApp.switchForm(None)


class ServiceChoiceForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Next'
    CANCEL_BUTTON_TEXT = 'Prev'

    def create(self):
        super().create()
        self.name = 'Welcome to Errbot setup wizard'
        self.cycle_widgets = True

        self.backends = self.add(TitleSelectOne,
                                 name='Select the chatting service you want to use',
                                 values=BACKENDS,
                                 scroll_exit=True, value=[0])

    def on_ok(self):
        self.parentApp.switchForm('SECRET')

    def on_cancel(self):
        self.quit()

    @property
    def backend(self):
        return self.backends.values[self.backends.value[0]]


class SecretForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Next'
    CANCEL_BUTTON_TEXT = 'Prev'

    def create(self):
        backend = self.parentApp.getForm('SERVICE').backend
        self.name = 'Enter your credentials for %s' % backend
        self.cycle_widgets = True

        blurb = BACKEND_BLURBS[backend]

        self.add(MultiLineEdit, value=blurb, max_height=self.curses_pad.getmaxyx()[0] - 10, editable=False)
        self.nextrely += 2

        if backend == 'Slack':
            self.token = self.add(TitleText, name='Token', value='xoxb-')
        elif backend == 'Hipchat':
            self.fullname = self.add(TitleText, name='Full Name', value='')
            self.username = self.add(TitleText, name='Username', value='#####_######@chat.hipchat.com')
            self.password = self.add(TitleText, name='Password', value='')
            self.token = self.add(TitleText, name='API Token', value='')

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

LOCAL_INSTALL = 'Local installation'
GCE_INSTALL = 'Google Compute Engine VM'
DOCKER_INSTALL = 'Docker'


class InstallationDestinationForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Next'
    CANCEL_BUTTON_TEXT = 'Exit'

    def create(self):
        super().create()
        self.name = 'Welcome to Errbot setup wizard'
        self.cycle_widgets = True

        self.add(MultiLineEdit,
                 value=BLURB,
                 max_height=5, editable=False)

        self.installations = self.add(TitleSelectOne,
                                      name='Select the type of installation',
                                      values=[LOCAL_INSTALL, GCE_INSTALL, DOCKER_INSTALL],
                                      scroll_exit=True, value=[0])

    def on_ok(self):
        if self.installation == LOCAL_INSTALL:
            self.parentApp.switchForm('SECRET')
        elif self.installation == GCE_INSTALL:
            self.parentApp.switchForm('GCE_PROJECT')
        elif self.installation == DOCKER_INSTALL:
            self.parentApp.switchForm('DOCKER1')

    def on_cancel(self):
        self.quit()

    @property
    def installation(self):
        return self.installations.values[self.installations.value[0]]


class GCEProjectForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Next'
    CANCEL_BUTTON_TEXT = 'Prev'

    def create(self):
        super().create()
        self.name = 'GCE Login'
        self.cycle_widgets = True
        self.project_field = self.add(TitleText, name='Project Name', value='')

    def on_ok(self):
        self.parentApp.switchForm('GCE_LOGIN')

    def on_cancel(self):
        self.quit()

    @property
    def project(self):
        return self.project_field.value


class GCELoginForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Prev'

    def create(self):
        super().create()
        self.name = 'Login to GCE...'
        self.cycle_widgets = True

        self.add(MultiLineEdit,
                 value=GCE_BLURB,
                 max_height=5, editable=False)
        self.status = self.add(MultiLineEdit,
                               value='Starting up authentication flow...',
                               max_height=1, editable=False, color='WARNING')
        self.keypress_timeout = 10
        self.authenticating = False

    def while_waiting(self):
        if not self.authenticating:
            self.authenticating = True
            project = self.parentApp.getForm('GCE_PROJECT').project
            self.gc = API(project)
            self.status.value = 'Requesting your account authorization from your browser...'
            self.display()
            self.gc.auth()
            self.status.value = 'Authorization successful !'
            self.display()
            self.parentApp.switchForm('GCE_REGION')

    def on_ok(self):  # this is previous
        self.parentApp.switchFormPrevious()


class GCERegionForm(ActionFormHelp):
    OK_BUTTON_TEXT = 'Next'
    CANCEL_BUTTON_TEXT = 'Prev'

    def create(self):
        super().create()
        self.name = 'GCE Region'
        self.cycle_widgets = True
        gc = self.parentApp.getForm('GCE_LOGIN').gc

        self.regions = self.add(TitleSelectOne,
                                name='Select the GCE region in which you would like to deploy the bot',
                                values=gc.get_regions(),
                                scroll_exit=True, value=[0])

    def on_ok(self):
        self.parentApp.switchForm('SERVICE')

    def on_cancel(self):
        self.parentApp.switchForm('GCE_PROJECT')

    @property
    def region(self):
        return self.regions.values[self.regions.value[0]]


class SetupWizard(NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', InstallationDestinationForm)
        self.addForm('SERVICE', ServiceChoiceForm)
        self.addForm('GCE_PROJECT', GCEProjectForm)
        self.addForm('GCE_LOGIN', GCELoginForm)
        self.addFormClass('GCE_REGION', GCERegionForm)
        self.addFormClass('SECRET', SecretForm)


def setup():
    app = SetupWizard()
    app.run()

if __name__ == '__main__':
    setup()
