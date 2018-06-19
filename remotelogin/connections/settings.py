import os

# #############################          SOCKETS CONFIG          #########################

# socket operation timeout. This will be the minimum granularity for SimpleTimer timeouts
SOCKET_TIMEOUT = 30

# time to complete a login use in expect login into another account like telnet -> telnet -> telnet
SOCKET_TIMEOUT_FOR_LOGIN = 8

TIMEOUT_FOR_PROMPT = 0.7
# time to complete a login use in expect login into another account like telnet -> telnet -> telnet
SOCKET_TIMEOUT_FOR_LOGIN_TELNET = 8

# period to send keep alives set it to 0 to disable keepalives
SOCKET_KEEPALIVE_PERIOD = 0

BUFFER_SIZE = 4096          # socket buffer size
BUFFER_SIZE_TO_RETURN_WHEN_ERROR = 200

SOCKET_TIME_SLEEP_NO_DATA_SELECT = 0.01
FLUSH_RECV_TIMEOUT = 0.05

DEFAULT_TRANSPORT_WINDOW_SIZE = 1 << 21      # Paramiko defaults = 2MB
DEFAULT_TRANSPORT_MAX_PACKET_SIZE = 1 << 15  # Paramiko defaults = 32K

TELNET_TIMEOUT_RECV = .01
SSH_RECV_READY_SLEEP = 0.002

ENCODE_ERROR_ARGUMENT_VALUE = 'ignore'
DECODE_ERROR_ARGUMENT_VALUE = 'ignore'   # possible 'strict', 'replace'
ENCODE_ENCODING_TYPE = 'utf-8'
DECODE_ENCODING_TYPE = 'utf-8'

TEMP_FILE_EXTENSION = '.tmp'

NON_BLOCKING_JOIN_TIMEOUT = 5

# #############################          LOCAL CONNECTIONS CONFIG          #########################

CONNECTION_LOCAL_TIMEOUT = 0.05
CONNECTION_LOGIN_LOCAL_TIMEOUT = 0.05

NON_BLOCKING_RECEIVED_DATA_TIMEOUT = 0.05
TIMEOUT_FOR_EXPECT = 0      # time to wait for the whole expected list to complete
SHELL_COLS = 16000            # interactive shell width
SHELL_ROWS = 3000         # interactive shell height

IANA_CSV_FILE = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'service-names-port-numbers.csv')

KEEP_CONNECTIONS_DB = True

# message to show for hidden text like passwords
HIDDEN_DATA_MSG = 'PROTECTED/HIDDEN DATA'

SFTP_SCP_WINDOW_SIZE = DEFAULT_TRANSPORT_WINDOW_SIZE
SFTP_SCP_MAX_PACKET_SIZE = DEFAULT_TRANSPORT_MAX_PACKET_SIZE
SFTP_SCP_BUFFER_SIZE = DEFAULT_TRANSPORT_MAX_PACKET_SIZE

DISABLE_HISTORY_RECORDING = None # None means to relay to os default value for can_disable_history

# ENV_TO_VARS = {}


def after_update():
    from .base import Connection

    Connection.NON_BLOCKING_JOIN_TIMEOUT = NON_BLOCKING_JOIN_TIMEOUT

# update settings with environment settings
from fdutils.config import register_settings
register_settings(globals(), 'connections')
