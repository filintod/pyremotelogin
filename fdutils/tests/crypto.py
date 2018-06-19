from fdutils.crypto import *
import pytest


def test_encrypt_with_cipher():
    salt = create_salt()
    cipher = create_cipher('my password', salt)
    text = 'my text'
    encrypted = encrypt(text, cipher=cipher)
    assert encrypted != text
    assert decrypt(encrypted, cipher=cipher) == text


def test_encrypt_with_password():
    salt = create_salt()
    text = 'my text'
    password = 'my password'
    encrypted = encrypt(text, password, salt=salt)
    assert encrypted != text
    assert decrypt(encrypted, password, salt=salt) == text


def test_bad_password_raises_invalid_token():
    salt = create_salt()
    text = 'my text'
    password = 'my password'
    password2 = 'my password2'
    encrypted = encrypt(text, password, salt=salt)
    assert encrypted != text
    with pytest.raises(InvalidKey):
        assert decrypt(encrypted, password2, salt=salt) != text


def test_encrypt_with_class_SecuredText():
    st = SecuredTextEngine(create_salt(), password='my pass')
    text = 'my text'
    encrypted = st.encrypt(text)
    assert encrypted != text
    assert st.decrypt(encrypted) == text


def test_SecuredText_bad_password_raises_invalid_token():
    salt = create_salt()
    st = SecuredTextEngine(salt, password='my pass')
    st2 = SecuredTextEngine(salt, password='my pass2')
    text = 'my text'
    encrypted = st.encrypt(text)
    assert encrypted != text
    with pytest.raises(InvalidKey):
        assert st2.decrypt(encrypted)
