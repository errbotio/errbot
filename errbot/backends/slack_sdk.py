from time import sleep
import logging
import sys

from errbot.core import ErrBot
from errbot.core_plugins import flask_app

from slack_rtm import slack_markdown_converter, SlackAPIResponseError, SlackPerson, SlackBackendBase

log = logging.getLogger(__name__)

try:
    from slackeventsapi import SlackEventAdapter
    from slack.errors import BotUserAccessError
    from slack import WebClient
except ImportError:
    log.exception("Could not start the SlackRTM backend")
    log.fatal(
        "You need to install slackclient in order to use the Slack backend.\n"
        "You can do `pip install errbot[slack-events]` to install it."
    )
    sys.exit(1)


class SlackEventsBackend(SlackBackendBase, ErrBot):

    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get('token', None)
        self.signing_secret = identity.get('signing_secret', None)
        self.proxies = identity.get('proxies', None)
        if not self.token:
            log.fatal(
                'You need to set your token (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this token I '
                'cannot connect to Slack.'
            )
            sys.exit(1)
        if not self.signing_secret:
            log.fatal(
                'You need to set your signing_secret (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this secret I '
                'cannot receive events from Slack.'
            )
            sys.exit(1)
        self.sc = None  # Will be initialized in serve_once
        self.slack_events_adapter = None  # Will be initialized in serve_once
        self.webclient = None
        self.bot_identifier = None
        compact = config.COMPACT_OUTPUT if hasattr(config, 'COMPACT_OUTPUT') else False
        self.md = slack_markdown_converter(compact)
        self._register_identifiers_pickling()

    def _setup_event_callbacks(self):
        # List of events obtained from https://api.slack.com/events
        slack_event_types = [
            'app_home_opened',
            'app_mention',
            'app_rate_limited',
            'app_requested',
            'app_uninstalled',
            'call_rejected',
            'channel_archive',
            'channel_created',
            'channel_deleted',
            'channel_history_changed',
            'channel_left',
            'channel_rename',
            'channel_shared',
            'channel_unarchive',
            'channel_unshared',
            'dnd_updated',
            'dnd_updated_user',
            'email_domain_changed',
            'emoji_changed',
            'file_change',
            'file_comment_added',
            'file_comment_deleted',
            'file_comment_edited',
            'file_created',
            'file_deleted',
            'file_public',
            'file_shared',
            'file_unshared',
            'grid_migration_finished',
            'grid_migration_started',
            'group_archive',
            'group_close',
            'group_deleted',
            'group_history_changed',
            'group_left',
            'group_open',
            'group_rename',
            'group_unarchive',
            'im_close',
            'im_created',
            'im_history_changed',
            'im_open',
            'invite_requested',
            'link_shared',
            'member_joined_channel',
            'member_left_channel',
            'message',
            'message.app_home',
            'message.channels',
            'message.groups',
            'message.im',
            'message.mpim',
            'pin_added',
            'pin_removed',
            'reaction_added',
            'reaction_removed',
            'resources_added',
            'resources_removed',
            'scope_denied',
            'scope_granted',
            'star_added',
            'star_removed',
            'subteam_created',
            'subteam_members_changed',
            'subteam_self_added',
            'subteam_self_removed',
            'subteam_updated',
            'team_domain_change',
            'team_join',
            'team_rename',
            'tokens_revoked',
            'url_verification',
            'user_change',
            'user_resource_denied',
            'user_resource_granted',
            'user_resource_removed',
            'workflow_step_execute'
        ]
        for t in slack_event_types:
            self.slack_events_adapter.on(t, self._generic_wrapper)

        self.connect_callback()

    def serve_forever(self):
        self.sc = WebClient(token=self.token, proxy=self.proxies)
        self.webclient = self.sc
        self.slack_events_adapter = SlackEventAdapter(self.signing_secret, "/slack/events", flask_app)

        log.info('Verifying authentication token')
        self.auth = self.sc.auth_test()
        log.debug(f"Auth response: {self.auth}")
        if not self.auth['ok']:
            raise SlackAPIResponseError(error=f"Couldn't authenticate with Slack. Server said: {self.auth['error']}")
        log.debug("Token accepted")
        self._setup_event_callbacks()

        self.bot_identifier = SlackPerson(self.sc, self.auth['user_id'])

        log.debug(self.bot_identifier)

        # Inject bot identity to alternative prefixes
        self.update_alternate_prefixes()

        log.debug('Initialized, waiting for events')
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            log.info("Interrupt received, shutting down..")
            return True
        except Exception:
            log.exception("Error reading from RTM stream:")
        finally:
            log.debug("Triggering disconnect callback")
            self.disconnect_callback()

    def _generic_wrapper(self, event_data):
        """Calls the event handler based on the event type"""
        log.debug('Recived event: {}'.format(str(event_data)))
        event = event_data['event']
        event_type = event['type']

        try:
            event_handler = getattr(self, f"_{event_type}_event_handler")
            return event_handler(self.sc, event)
        except AttributeError:
            log.info(f'Event type {event_type} not supported')
