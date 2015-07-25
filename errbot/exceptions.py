class ACLViolation(Exception):
    """Exceptions raised when user is not allowed to execute given command due to ACLs"""


class RoomError(Exception):
    """General exception class for MUC-related errors"""


class RoomNotJoinedError(RoomError):
    """Exception raised when performing MUC operations
    that require the bot to have joined the room"""


class RoomDoesNotExistError(RoomError):
    """Exception that is raised when performing an operation
    on a room that doesn't exist"""


class UserDoesNotExistError(Exception):
    """Exception that is raised when performing an operation
    on a user that doesn't exist"""


class SlackAPIResponseError(RuntimeError):
    """Slack API returned a non-OK response"""

    def __init__(self, *args, error, **kwargs):
        """
        :param response:
            The 'error' key from the API response data
        """
        self.error = error
        super().__init__(*args, **kwargs)


class IncompatiblePluginException(Exception):
    pass


class PluginConfigurationException(Exception):
    pass


class StoreException(Exception):
    pass


class StoreAlreadyOpenError(StoreException):
    pass


class StoreNotOpenError(StoreException):
    pass


class ValidationException(Exception):
    pass
