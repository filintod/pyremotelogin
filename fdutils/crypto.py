import base64
import getpass
import os

from fdutils.config import environment_settings, update_settings_with_user_settings

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DEFAULT_HASH_ALGORITHM_NAME = 'SHA256'

update_settings_with_user_settings(locals(), 'crypto')

DEFAULT_HASH_ALGORITHM = getattr(hashes, DEFAULT_HASH_ALGORITHM_NAME)


class InvalidKey(InvalidToken):
    pass


def create_salt(hash_algorithm=DEFAULT_HASH_ALGORITHM):
    return os.urandom(hash_algorithm.digest_size)


def create_cipher(password, salt, iterations=1000, length=32, hash_algorithm=DEFAULT_HASH_ALGORITHM):
    kdf = PBKDF2HMAC(
        algorithm=hash_algorithm(),
        length=length,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(password)))


def encrypt(plaintext, password, salt, cipher=None, encoding='utf-8'):
    salt = salt or create_salt()
    password = password or getpass.getpass()
    cipher = cipher or create_cipher(password, salt)
    return cipher.encrypt(bytes(plaintext, encoding=encoding)), salt


def decrypt(encrypted, password, salt, cipher=None, encoding='utf-8'):
    try:
        cipher = cipher or create_cipher(password, salt)
        return cipher.decrypt(encrypted).decode(encoding)
    except InvalidToken as e:
        raise InvalidKey from e


def get_password_from_script(script):
    import subprocess
    return subprocess.check_output(script)


def get_password_from_file(filepath):
    with open(filepath, 'rb') as f:
        return f.read()


class SecuredTextEngine:

    def __init__(self, salt=None, password=None, encoding='utf-8', hash_algorithm=DEFAULT_HASH_ALGORITHM):

        self.hash = hash_algorithm
        self.salt = self.cipher = None

        if not password and 'vault' in environment_settings:
            password_file = environment_settings['vault'].get('password_file', None)
            password_script = environment_settings['vault'].get('password_script', None)

            if password_file:
                password = get_password_from_file(password_file)

            elif password_script:
                password = get_password_from_script(password_script)

            else:
                import getpass
                password = getpass.getpass("Password to encrypt/decrypt credentials in DB: ").encode()

            salt_file = environment_settings['vault'].get('salt_file', None)
            if salt_file:
                salt = get_password_from_file(salt_file)

        if not password:
            raise ValueError("You need to provide a password to use crypto functions")

        self.password = password
        self.recreate_cipher(password, salt)
        self.encoding = encoding

    def recreate_cipher(self, password=None, salt=None):
        self.salt = salt or create_salt(hash_algorithm=self.hash)
        self.cipher = create_cipher(password or self.password, self.salt, hash_algorithm=self.hash)

    def clone(self, salt=None, password=None):
        return SecuredTextEngine(salt or self.salt, password or self.password, self.encoding, self.hash)

    def encrypt(self, text):
        return self.cipher.encrypt(bytes(text, encoding=self.encoding))

    def decrypt(self, encrypted):
        try:
            return self.cipher.decrypt(encrypted).decode(self.encoding)
        except InvalidToken as e:
            raise InvalidKey from e


def base64_hash(message):
    from hashlib import sha256
    hash = sha256()
    hash.update(message)
    return base64.b32encode(hash.digest())


DEFAULT_CRYPTO_ENGINE = None


def get_default_crypto_engine():

    global DEFAULT_CRYPTO_ENGINE

    if DEFAULT_CRYPTO_ENGINE is None:
        DEFAULT_CRYPTO_ENGINE = SecuredTextEngine()

    return DEFAULT_CRYPTO_ENGINE
