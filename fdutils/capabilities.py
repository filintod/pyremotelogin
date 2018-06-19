__author__ = 'Filinto Duran (duranto@gmail.com)'


class WithCapabilities:
    """ Class to add a capabilities information to a class.
        Capabilities are expected to be binary (1,2,4,8,...)

    """
    def __init__(self, capabilities=0):
        self.capabilities = capabilities
        self.capabilities_disabled = 0

    def can(self, capabilities):
        return not capabilities or self.capabilities & capabilities and not (self.capabilities_disabled & capabilities)

    def cannot(self, capabilities):
        return not self.can(capabilities)

    def disable_capability(self, capabilities):
        self.capabilities_disabled |= capabilities

    def enable_capability(self, capabilities):
        self.capabilities_disabled &= ~capabilities
        self.capabilities |= capabilities

    def remove_capability(self, capabilities):
        self.capabilities_disabled &= ~capabilities
        self.capabilities &= ~capabilities

    def add_capability(self, capabilities):
        self.capabilities |= capabilities


class WithCapabilitiesGral:
    """ Class to add a capabilities information where the capability is a general value

    """
    def __init__(self, can_do=None):
        self.can_do = set()
        if can_do is not None:
            self.add_capability(can_do)
        self.capabilities_disabled = set()

    def can(self, *capabilities):
        return all([(c in self.can_do and not c in self.capabilities_disabled) for c in capabilities])

    def cannot(self, *capabilities):
        return not self.can(*capabilities)

    def disable_capability(self, *capabilities):
        self.capabilities_disabled -= set([c for c in capabilities if c in self.can_do])

    def remove_capability(self, *capabilities):
        self.capabilities_disabled -= set(capabilities)
        self.can_do -= set(capabilities)

    def add_capability(self, *capabilities):
        self.can_do |= set(capabilities)

    def enable_capability(self, *capabilities):
        self.capabilities_disabled |= set([c for c in capabilities if c in self.can_do])