import logging

from .db import SQLDB

SQLITE_CONNECT_STRING = 'sqlite://{file_path}'

log = logging.getLogger(__name__)


class OracleDB(SQLDB):

    DATABASE_NAME = 'oracle'
    PORT = 1521
    DRIVER = ''

    def __init__(self, *args, **kwargs):
        self.service_name = kwargs.pop('service_name', None)
        super(OracleDB, self).__init__(*args, **kwargs)

    def __repr__(self, **kwargs):
        return super(OracleDB, self).__repr__(', {sid_or_service}="{db}"'.format(
            sid_or_service=('sid' if not self.service_name else 'service_name'), db=self.db))

    def get_connect_string(self, template=None):
        if not template and self.service_name is not None:
            # create the multi address url for clusters
            address_template = '(ADDRESS = (PROTOCOL = TCP)(HOST = {host})(PORT = {port}))'
            hosts_info = ''.join(address_template.format(host=host, port=port or self.port)
                                 for (host,port) in self.cluster)
            # https://docs.oracle.com/database/121/HABPT/config_fcf.htm#HABPT5381
            template = ("oracle+cx_oracle://{username}:{password}@(DESCRIPTION = "
                        "(FAILOVER=ON) " +
                        "(ADDRESS_LIST=" +
                        "(LOAD_BALANCE=on)" +
                        "(CONNECT_TIMEOUT=3)(RETRY_COUNT=3)" +
                        hosts_info +
                        ")" + # from address_list
                        "(CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = {db})))")
        else:
            template = template
        return super(OracleDB, self).get_connect_string(template=template)


class MySQLDB(SQLDB):

    DATABASE_NAME = 'mysql'
    DRIVER = 'pymysql'  # other could be 'mysqldb' that is c-based
    PORT = 3306

    def __repr__(self, **kwargs):
        return super(MySQLDB, self).__repr__(', dbname="{}"'.format(self.db))


class PostgresDB(SQLDB):

    DATABASE_NAME = 'postgresql'
    DRIVER = 'psycopg2'
    PORT = 5432

    def __repr__(self, **kwargs):
        return super(PostgresDB, self).__repr__(', dbname="{}"'.format(self.db))


class SQLite(SQLDB):

    DATABASE_NAME = 'sqlite'
    DRIVER = ''
    TEMPLATE = 'sqlite:///{db}'

    def __repr__(self, **kwargs):
        return 'SQLite(db_file_path={})'.format(self.db)


def create_from_vendor(vendor='', host='', db='', port=0, username='', password='', **db_kwargs):
    """ Creates an instance of a subclass of SQLDB given the type as string

        Arguments:
          - dbtype (str): the type of DB we want (sqllite, oracle or postgres)

    """

    vendor = vendor.lower()
    if vendor in ('sqllite', 'sqlite'):
        sqldb = SQLite
    elif vendor.startswith('postgres'):
        sqldb = PostgresDB
    elif vendor == 'oracle':
        sqldb = OracleDB
    elif vendor == 'mysql':
        sqldb = MysqlDB
    else:
        raise NotImplementedError('We have only implemented this method for sqllite, oracle and postgresql')

    return sqldb(username=username, password=password, host=host, port=port, db=db, **db_kwargs)
