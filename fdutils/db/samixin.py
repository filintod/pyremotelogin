"""The MIT License (MIT)

Copyright (c) 2017 Oleksandr Lytvynenko <litvinenko1706@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE."""
from sqlalchemy.orm import Session, scoped_session, Query


class classproperty(object):
    """
    @property for @classmethod
    taken from http://stackoverflow.com/a/13624858
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class NoDBSessionError(RuntimeError):
    pass


class SessionMixin:
    _session = None

    @classmethod
    def set_session(cls, session):
        """
        :type session: scoped_session | Session
        """
        cls._session = session

    @classproperty
    def dbsession(cls):
        """
        :rtype: scoped_session | Session
        """
        if cls._session is not None:
            return cls._session
        else:
            raise NoDBSessionError('Can\'t get session. Provide the config environment information')

    @classproperty
    def query(cls):
        """
        :rtype: Query
        """
        return cls.dbsession.query(cls)


