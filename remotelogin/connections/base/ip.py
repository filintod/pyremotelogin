import contextlib
import logging

from . import Connection
from .. import settings

log = logging.getLogger(__name__)


class IPConnection(Connection):

    # The default port to be defined by every connection (ssh->22, http->80, ...)
    _IANA_SVC_NAME = ''
    NEEDS_AUTHENTICATION = True

    AUTHENTICATION_KEYS = ('username', 'password')
    AUTHENTICATION_KEYS_COMBINATIONS = (('username',), ('password',), ('username', 'password'))
    ARGUMENTS_ALLOWED = Connection.ARGUMENTS_ALLOWED + ('host', 'port') + AUTHENTICATION_KEYS

    def __init__(self, host='', username=None, password=None, port=None, **kwargs):
        """
        :param str host: IP or hostname of connection
        :param int port: layer 4 port number of server

        """
        super(IPConnection, self).__init__(**kwargs)

        self.host = host
        self.port = int(port or self.get_iana_default_port())

        # user login information
        self.username = str(username)
        self.password = str(password)

    def _base_repr(self):
        base_set = super(IPConnection, self)._base_repr()
        specific = {('host', True), ('port', False), ('username', True), ('password', 'your password')}
        return base_set | specific

    def get_iana_default_port(self):
        # iana ports are found at https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv
        import csv
        with open(settings.IANA_CSV_FILE) as f:
            iana_data = csv.reader(f)
            for i, row in enumerate(iana_data):
                if i and row[0] == self._IANA_SVC_NAME:
                    return int(row[1])
        raise Exception('Did not find a IANA port for this service ' + self._IANA_SVC_NAME)

