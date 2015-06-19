class SimpleIdentifier(str):
    """ This is an identifier just represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
        use self.build_identifier(identifier_as_string) instead.
    """

    @property
    def person(self):
        """This needs to return the part of the identifier pointing to a person.
        For example for XMPP it is node@domain without the resource that actually maps to a device."""
        return self


class SimpleMUCOccupant(SimpleIdentifier):
    """ This is a MUC occupant represented as a string.
        DO NOT USE THIS DIRECTLY AS IT IS NOT COMPATIBLE WITH MOST BACKENDS,
    """
