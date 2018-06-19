import collections
import hashlib
import os
import urllib.parse
from concurrent import futures
from http import HTTPStatus

import requests

from fdutils.files import get_filename_indexed, get_filename_timestamped
from ._utils import (convert_url_to_hashedurlresource, ftp_download_hashed_resource,
                     http_download_hashed_resource, protocol_not_implemented, FileHashError)

import logging
log = logging.getLogger(__name__)

HASH_AVAILABLE = {h: getattr(hashlib, h) for h in dir(hashlib) if h in hashlib.algorithms_available}


def upload_file_to_site(local_file_path, site_upload_url, **req_kwargs):
    """ uploads a file using requests (not using chunks so don't use for very large files)

    :param local_file_path:
    :return:
    """
    data = dict(upload=os.path.basename(local_file_path))
    files = dict(upload=open(local_file_path, 'rb'))

    r = requests.post(site_upload_url, files=files, data=data, **req_kwargs)

    return r.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.NO_CONTENT)


def download_resource(url, local_file_name='', hash_digest='', hash_algorithm='md5', **kwargs):
    """ single file version of download_resources but it allows to pass some of the hash information directly
        instead of having to create a HashedURLResource object to pass that information """
    return download_resources(
        convert_url_to_hashedurlresource(url, local_file_name, hash_digest, hash_algorithm, True),
        **kwargs)


def download_resources(*urls, local_folder='', chunk_size=1 << 15, session=None, replace=False, threads_count=10,
                       unzip=False, split_requests=False, timestamp=False, delete_on_bad_hash=True,
                       **request_kwargs):
    """ downloads one or more web/ftp resources, it also unzip them if they are archived in some known forms
        (gzip, bz2, zip, or tar.gz) and unzip=True, it will also check hash values of the downloaded files if specified.

        The downloads and unzipping are down in parallel using threads.
        For HTTP downloads it also supports HTTP Bytes range header to do partial downloads in case a failure occurs
        in the middle of a download

    Args:
        urls (*str or *HashURLResource): each should start with http(s):// or ftp://
        local_folder (str):
        chunk_size (int):
        session (requests.Session):
        replace (bool): whether to replace the file if same name or add index to it
        threads_count (int):
        unzip (bool): whether to unzip the file after received
        split_requests (bool): whether to use HTTP Byte Range header and do concurrent retrieval of its parts
        **request_kwargs: requests parameters if needed

    Returns:

    """
    url_resources = set(convert_url_to_hashedurlresource(url, assign_filename=(len(urls) == 1)) for url in urls)
    file_suffix_func = get_filename_indexed if not timestamp else get_filename_timestamped

    futures_res = {}
    ret = {}
    with futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
        for url_resource in url_resources:

            if url_resource.is_ftp():
                log.debug('Download FTP: {}'.format(url_resource.url))
                submitted = executor.submit(ftp_download_hashed_resource, url_resource, local_folder, chunk_size,
                                            unzip, replace, file_suffix_func, delete_on_bad_hash)
            else:
                log.debug('Download HTTP(s): {}'.format(url_resource.url))
                submitted = executor.submit(http_download_hashed_resource, url_resource, local_folder, session,
                                            chunk_size, unzip, split_requests, replace, file_suffix_func,
                                            delete_on_bad_hash, **request_kwargs)

            futures_res[submitted] = url_resource

        for executed_future in futures.as_completed(futures_res):
            response = executed_future.result()
            if response:
                status_code, filename = response
                ret[futures_res[executed_future]] = dict(status_code=status_code, local_filename=filename)
            else:
                print('Problems with {}'.format(futures_res[executed_future]))

    return ret


class HashedURLResource:
    """ an object to specify information of URL Resources that are going to be downloaded """
    __slots__ = ('_url', 'digest', '_algorithm', '_algorithm_function', 'filename')

    def __init__(self, url, digest='', algorithm='md5', filename=''):
        self.url = url
        self.filename = filename
        self.digest = digest
        self.algorithm = algorithm

    def is_ftp(self):
        return self.url.startswith('ftp://')

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        if protocol_not_implemented(url):
            raise ValueError('Resource URL ({}) should start with http:// or https:// or ftp://'.format(url))
        self._url = url

    @property
    def algorithm(self):
        return self._algorithm

    @algorithm.setter
    def algorithm(self, algo):
        algo_lower = algo.lower()
        if algo_lower not in HASH_AVAILABLE:
            raise ValueError('This Hash algorithm ({}) is not one of the availables ({})'
                             ''.format(algo, ', '.join(HASH_AVAILABLE)))
        self._algorithm = algo_lower
        self._algorithm_function = HASH_AVAILABLE[algo_lower]

    def check_digest(self, filepath, chunk_size=1 << 14):
        if self.digest:
            hash = self._algorithm_function()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash.update(chunk)
            file_hash = hash.hexdigest()
            if file_hash != self.digest:
                raise FileHashError('When downloading URL ({url}) the file downloaded ({filename}) '
                                    'hash "{hash_algorithm} digest ({file_hash}) '
                                    'is different to the expected ({expected_hash})'
                                    ''.format(url=self.url, filename=filepath, hash_algorithm=self.algorithm,
                                              file_hash=file_hash, expected_hash=self.digest))

    def __hash__(self):
        # so we can use as key in sets/dicts
        return hash(self.url)


def parse_http_url(url):
    """ reformats urllib.parse.urlparse to use in our selenium utils

        we join scheme and hostname from urlparse, also add an is_ssl part and check that we have scheme (http, https, etc)

        Returns:
            ParseURLResult: a named tuple with attributes baseurl, port, is_ssl, path, params, query and fragment
    """
    ParseURLResult = collections.namedtuple(
        'ParseURLResult', 'baseurl port is_ssl path params query fragment')

    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        raise AttributeError('URL {} is not well formed we need the protocol (http/https/ftp/etc...)'.format(url))

    return ParseURLResult(parsed.scheme + '://' + parsed.hostname, parsed.port, parsed.scheme == 'https', parsed.path,
                          parsed.params, parsed.query, parsed.fragment)


def get_requests_session_for_encrypted_cert(prefix, certfile, keyfile, password, *args, **kwargs):
    """ creates a requests HTTPAdapter that can handle encrypted private keys

    Args:
        prefix (str): prefix of the url as the adapter checks for the url.startswith(prefix) to return the correct adapter
        certfile (str): path to public cert file (it should include all the chain)
        keyfile (str): path to the private key file
        password (str or bytes): password of private key
        *args:
        **kwargs: HTTPAdapter kwargs to pass.  We pop two keys (session and verify) in case people pass a requests
                  Session object so we don't create a new one, and verify to set the verify flag in the session

    Returns:

    """

    from urllib3.util.ssl_ import create_urllib3_context
    from requests.adapters import HTTPAdapter

    session = kwargs.pop('session', requests.Session())
    verify = kwargs.pop('verify', False)

    class SSLAdapter(HTTPAdapter):
        def __init__(self, certfile, keyfile, password, *args, **kwargs):
            self._certfile = certfile
            self._keyfile = keyfile
            self._password = password
            super().__init__(*args, **kwargs)

        def init_poolmanager(self, *args, **kwargs):
            return super().init_poolmanager(*args, **self._encrypted_cert_kwargs(kwargs))

        def proxy_manager_for(self, *args, **kwargs):
            return super().proxy_manager_for(*args, **self._encrypted_cert_kwargs(kwargs))

        def _encrypted_cert_kwargs(self, kwargs):
            context = create_urllib3_context()
            context.load_cert_chain(certfile=self._certfile, keyfile=self._keyfile, password=self._password)
            kwargs['ssl_context'] = context
            return kwargs

    try:
        prefix_parsed = parse_http_url(prefix)
    except AttributeError:
        prefix_parsed = parse_http_url('https://' + prefix)

    prefix_host = prefix_parsed.baseurl + (prefix_parsed.port if prefix_parsed.port else '')
    session.mount(prefix_host, SSLAdapter(certfile, keyfile, password, *args, **kwargs))
    session.verify = verify
    return session
