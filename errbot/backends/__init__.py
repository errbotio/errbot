import logging

log = logging.getLogger(__name__)


class DeprecationBridgeIdentifier(object):
    """This is a Deprecation bridge that will be removed.
    Originally identifier were mapped to XMPP, this emulate that with a deprecation notice.
    """
    @property
    def node(self):
        log.warn('.node is deprecated on this type of identifier, use .person instead')
        return self.person

    @property
    def domain(self):
        log.warn('.domain is deprecated on this type of identifier and should not be used')
        return ''

    @property
    def resource(self):
        log.warn('.resource on this type of identifier is deprecated, use .client instead')
        return self.client


class SimpleIdentifier(DeprecationBridgeIdentifier):
    """ This is an identifier just represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
        use self.build_identifier(identifier_as_string) instead.
    """

    def __init__(self, person, client=None):
        self._person = person
        self._client = client

    @property
    def person(self):
        """This needs to return the part of the identifier pointing to a person."""
        return self._person

    @property
    def client(self):
        """This needs to return the part of the identifier pointing to a client from which a person is sending a message from.
        Returns None is unspecified"""
        return self._client

    def __unicode__(self):
        if self.client:
            return self._person + "/" + self._client
        return self._person
    __str__ = __unicode__

    def __eq__(self, other):
        return self.person == other.person


class SimpleMUCOccupant(SimpleIdentifier):
    """ This is a MUC occupant represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
    """
    def __init__(self, person, room):
        super().__init__(person)
        self._room = room

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return self._person + '@' + self._room

    __str__ = __unicode__

    def __eq__(self, other):
        return self.person == other.person and self.room == other.room
