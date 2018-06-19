class NonUniqueServiceError(Exception):
    pass


class ServiceNotFoundError(Exception):
    pass


class DeviceFolderError(Exception):
    pass


class NoDefaultInterfaceError(ConnectionError):
    pass


class ConnectionInstanceOpenError(ConnectionError):
    """ failing trying to find a connection or instance open """


class UnknownConnectionError(ConnectionError):
    """ wrong name or instance """


class UnknownUserError(Exception):
    """ wrong name or instance """


class UnknownInterfaceError(Exception):
    """ wrong name or instance """


class DuplicatedInterfaceError(Exception):
    pass


class UnknownTunnelError(Exception):
    """ wrong name or instance """


class DuplicatedTunnelError(Exception):
    pass


class DuplicatedConnectionError(ConnectionError):
    pass


class DuplicatedUserError(Exception):
    pass


class NotImplementedProtocolError(ConnectionError):
    pass


class UserAuthenticationValuesError(Exception):
    pass


class FileAlreadyOpenOnDeviceError(Exception):
    pass


class FileNotOpenOnDeviceError(Exception):
    pass