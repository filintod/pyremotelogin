import json

from sqlalchemy import TypeDecorator, types

from fdutils.crypto import SecuredTextEngine, DEFAULT_HASH_ALGORITHM
from fdutils.func import default_json


class ToJSONCapable(TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = types.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value, default=default_json)

    def process_result_value(self, value, dialect):
        return json.loads(value) if value is not None else None


class Encrypted(TypeDecorator):
    """ stores data encrypted with its salt
        whenever we change the data we recreate the salt and hash
    """
    impl = types.LargeBinary

    def __init__(self, salt=None, password=None, recreate_on_save=False, **kwargs):
        self.crypto = None
        self.clear = None
        self.password = password
        self.salt = salt
        self.recreate_on_save = recreate_on_save
        super().__init__(**kwargs)

    def _create_crypto(self, force=False):
        if not self.crypto:
            self.crypto = SecuredTextEngine(salt=self.salt, password=self.password)
        elif force:
            self.crypto.recreate_cipher()

    def process_bind_param(self, value, dialect):
        self._create_crypto(force=(self.clear and self.clear != value))
        return self.crypto.encrypt(value) + self.crypto.salt

    def process_result_value(self, value, dialect):
        self.salt = value[-DEFAULT_HASH_ALGORITHM.digest:]
        self._create_crypto(force=True)
        return self.crypto.decrypt(value[:DEFAULT_HASH_ALGORITHM.digest])