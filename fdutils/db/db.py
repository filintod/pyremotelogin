import contextlib
import logging
import time

from sqlalchemy import text, create_engine, exc

from fdutils import strings
from fdutils.decorators import retry

log = logging.getLogger(__name__)

CONNECT_STRING = '{database}{driver}://{username}:{password}@{server_address}:{server_port}/{db}'


class TransactionConnection:

    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, *args, **kwargs):
        return self.conn.execute(parameterized_query(sql), *args, **kwargs)

    def __getattr__(self, item):
        return getattr(self.conn, item)


def parameterized_query(sql):
    """ Create a sql query with parameters in proper format expected by sqlQuery

        When we pass

            "select * from my_table where column1={c1} and column2={c2}"

        The function will return

            "select * from my_table where column1=:c1 and column2=:c2"
     """
    formatter_names = strings.get_list_of_formatter_names(sql)
    if formatter_names:
        sql = text(sql.format(**{name: (':' + name) for name in formatter_names}))
    return sql


def parse_multiple_hosts(host):
    """ A host can be given as a csv of ip:port values and this function creates the list properly """
    hosts = host.split(',')
    cluster = []
    for host in hosts:
        host, *port = host.split(':')
        cluster.append((host,port[0] if port else None))
    return cluster


class SQLDB:
    """ Base class for our database specific Classes of Database """

    DATABASE_NAME = ''
    PORT = 0
    DRIVER = ''
    TEMPLATE = CONNECT_STRING

    def __init__(self, username='', password='', host='127.0.0.1', port=0, driver='', db='', connect_timeout=10):
        """
        Args:
            driver:
            db: the database to use (sid, service name, etc.)
            connect_timeout:
        """

        self.username = username
        self.password = password
        self.host = host
        self.port = str(port or self.PORT)
        self.driver = driver or self.DRIVER
        self.db = db
        self.connect_timeout = connect_timeout
        self._conn = None
        self.cluster = parse_multiple_hosts(host) if host else ''

    @property
    def conn(self):
        """ lazier db connector """
        if self._conn is None:
            self._conn = create_engine(self.get_connect_string(), **self._get_conn_args())
        return self._conn

    def _get_conn_args(self):
        return {}

    def get_connect_string(self, template=None):
        template = template or self.TEMPLATE
        string = template.format(database=self.DATABASE_NAME,
                                 driver=('+' + self.driver) if self.driver else '',
                                 username=self.username,
                                 password=self.password,
                                 server_address=self.host,
                                 server_port=self.port,
                                 db=self.db)
        return string

    def __repr__(self, child_repr=''):
        return '{class_name}(username="{username}", password="{password}", host="{host}", port={port}{child_repr})' \
               ''.format(class_name=self.__class__.__name__,
                         username=self.username,  password=self.password, host=self.host, port=self.port,
                         child_repr=child_repr)

    def _connect(self):
        try:
            return retry(2, 5, retry_when=lambda c: not bool(c))(self.conn.connect)()
        except Exception:
            raise Exception('Could not connect to ' + str(self))

    @contextlib.contextmanager
    def conn_context(self):
        """ A context to open a connection and close it after not needed """
        conn = None
        try:
            conn = self._connect()
            yield conn
        finally:
            if conn:
                conn.close()

    @contextlib.contextmanager
    def transaction(self):
        """ context to transaction segment """
        with self.conn_context() as conn:
            with conn.begin():
                yield TransactionConnection(conn)

    def execute(self, sql, *multiparam, **params):
        """ proxy with retry sqlalchemy Connection.execute method
            http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Connection.execute

        Args:
            sql: sql statement (read doc for more info)
            *multiparam:        read doc for more info
            **params:           read doc for more info

        Returns:

        """
        ret = None

        try:
            sql = parameterized_query(sql)
            ret = self.conn.execute(sql, *multiparam, **params)

        except exc.DBAPIError as e:
            if e.connection_invalidated:
                time.sleep(.1)
                ret = self.conn.execute(sql, *multiparam, **params)

        return ret

    query = execute


