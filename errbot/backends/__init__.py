class SimpleIdentifier(object):
    """ This is an identifier just represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
        use self.build_identifier(identifier_as_string) instead.
    """

    def  __init__(self, usr):
       self._person = usr

    @property
    def person(self):
        """This needs to return the part of the identifier pointing to a person.
        For example for XMPP it is node@domain without the resource that actually maps to a device."""
        return self._person

    def __unicode__(self):
        return self._person
    __str__ = __unicode__


class SimpleMUCOccupant(SimpleIdentifier):
    """ This is a MUC occupant represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
    """
    def  __init__(self, idd):
       person, room = idd.split('@')
       super().__init__(person)
       self._room = room

    @property
    def room(self):
       return self._room

    def __unicode__(self):
        return self._person + '@' + self._room
