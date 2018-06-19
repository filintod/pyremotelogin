__author__ = 'Filinto Duran (duranto@gmail.com)'

# make use of calledprocesserror for execution exceptions even if coming from ssh, telnet, etc.
from subprocess import CalledProcessError
import socket


RECV_EXIT_STATUS_UNKNOWN = '---1'


class ExpectLoginError(ConnectionError):
    pass


class ExpectNotFound(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ExpectListNameConflict(Exception):
    pass


class PromptNotFoundError(Exception):
    pass



class ConnectionNotOpenError(ConnectionError):
    pass


class ConnectionOpenError(ConnectionError):
    pass


class AuthenticationException(ConnectionError):
    pass


class CommandNotProvidedError(Exception):
    pass


class UnknownKeyToServerError(Exception):
    """
        Exception raised if we receive a request to allow a key not found in the server and we are not allowing new keys
    """


class PermissionDeniedError(ConnectionError):
    """
        wrong authentication
    """


class ConnectionExpectTimeoutError(socket.timeout):
    """

    """


class BadSshKeyPasswordError(ConnectionError):
    pass


class NoDefaultUserError(ConnectionError):
    pass


class FileTransferError(ConnectionError):
    pass