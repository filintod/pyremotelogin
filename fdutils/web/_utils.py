# file related libraries
import bz2
import glob
import gzip
import logging
import lzma
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
# url/web libraries
import urllib.request
import zipfile

import requests
import urllib3.exceptions
from fdutils.files import get_filename_indexed

log = logging.getLogger(__name__)


def unzip_archive(local_file, local_folder, replace, filename_suffix_func):
    """ if filename is a .zip or .tar uncompress it """

    # first uncompress any .gz, .bz or .xz not done during download because of hash digest check
    filename, unzip_file_func = get_unzip_function(local_file)
    if filename != local_file:
        filename = index_file_if_exists(filename_suffix_func, filename, replace)
        with open(filename, 'wb') as f, unzip_file_func(local_file) as zf:
            shutil.copyfileobj(zf, f)
        os.remove(local_file)

    # second uncompressed/unarchive .tar and .zip files
    if filename[-4:] in ('.zip', '.tar'):
        path = index_file_if_exists(filename_suffix_func, os.path.splitext(filename)[0], replace)
        new_filename = path
        if filename.endswith('.zip'):
            with zipfile.ZipFile(filename) as zf:
                nl = zf.namelist()

                if len(nl) == 1:
                    member = nl.pop()
                    new_filename = os.path.join(local_folder, member)
                    if not replace:
                        if glob.glob(new_filename + '*'):
                            new_filename = filename_suffix_func(new_filename)
                        with tempfile.TemporaryDirectory() as tempdir:
                            zf.extract(member, path=tempdir)
                            shutil.move(os.path.join(tempdir, member), new_filename)
                    else:
                        zf.extract(member, path=path)
                else:
                    zf.extractall(path=path)

        else:
            with tarfile.TarFile(filename) as tf:
                tf.extractall(path=path)

        os.remove(filename)
        filename = new_filename

    return filename


def copyfileobj_counter(fsrc, fdst, length=16 * 1024):
    """ a clone of shutil.copyfileobj with an added counter for the number of chunks written so far """
    chunks = 0
    try:
        while 1:
            buf = fsrc.read(length)
            if not buf:
                break
            fdst.write(buf)
            chunks += 1
    except urllib3.exceptions.HTTPError as e:
        return chunks, e
    return chunks, 0


def partial_http_download(sess, response, starting_byte):
    req = response.request.copy()
    req.headers['Range'] = 'bytes={}-'.format(starting_byte)
    if not isinstance(sess, requests.Session):
        sess = requests.Session()
    new_resp = sess.send(req, stream=True)
    new_resp.raise_for_status()
    new_resp.raw.decode_content = True
    return new_resp


def save_response_to_file(resource, local_folder, raw_response, content_type, chunk_size, unzip, replace,
                          headers, filename_suffix_func, delete_on_bad_hash,
                          sess=None, sess_response=None, partial_download_max_retries=10):
    filename = resource.filename

    if not filename:
        filename = get_http_filename_in_content_disposition(resource.url, headers)

    if headers.get('Accept-Ranges', 'none') != 'none':
        partial_download = partial_http_download
    else:
        partial_download = None

    # ftp does not have content_type so we send filename instead
    filename, unzip_file_func = get_unzip_function(filename, content_type=content_type or filename, unzip=unzip,
                                                   digest=resource.digest)

    local_file = index_file_if_exists(filename_suffix_func, os.path.join(local_folder, filename), replace)

    stream_to_file_with_retry(chunk_size, local_file, partial_download, partial_download_max_retries, raw_response,
                              sess_response, sess, unzip_file_func)

    if resource.digest:
        try:
            resource.check_digest(local_file)
        except FileHashError:
            if delete_on_bad_hash:
                os.remove(local_file)
            raise

    if unzip:
        local_file = unzip_archive(local_file, local_folder, replace, filename_suffix_func)

    return local_file


def stream_to_file_with_retry(chunk_size, local_file, partial_download, partial_download_max_retries, raw_response,
                              sess_response, sess, unzip_file_func):
    """ saves stream from response to file if a http exception we will try to do a partial download """
    partial_download_tries = total_chunks = 0
    while partial_download_tries < partial_download_max_retries:
        mode = 'wb' if not partial_download_tries else 'rb+'
        with open(local_file, mode) as f, unzip_file_func(raw_response) as zf, raw_response:
            if partial_download_tries:
                f.seek(total_chunks * chunk_size)
            chunks, exception = copyfileobj_counter(zf, f, chunk_size)
            if exception:
                if partial_download and (partial_download_tries + 1) < partial_download_max_retries:
                    total_chunks += chunks
                    total_bytes = total_chunks * chunk_size
                    log.debug('Retrying a partial download from byte {}'.format(total_bytes))
                    partial_download_tries += 1
                    sess_response = partial_download(sess, sess_response, total_bytes)
                    raw_response = sess_response.raw
                else:
                    raise exception
            else:
                break


def index_file_if_exists(filename_suffix_func, filename, replace):
    if not replace and glob.glob(filename + '*'):
        filename = filename_suffix_func(filename)
    return filename


def get_http_filename_in_content_disposition(url, headers):
    content_disposition = headers.get('Content-Disposition', None)

    if content_disposition:
        filename = re.findall('filename="?(.+)"?', content_disposition)[0]
    else:
        from fdutils.web.web import parse_http_url

        parsed = parse_http_url(url)
        filename = parsed.path.rsplit('/', maxsplit=1)[1]

    return filename


def get_unzip_function(filename, content_type='', unzip=True, digest=False):
    """ used in streaming web download to uncompress on the fly for simple compression schemes """
    if unzip and not digest:
        if content_type == "application/gzip" or filename.endswith('.gz'):
            return filename[:-3], lambda f: gzip.GzipFile(fileobj=f)

        elif content_type == "application/bz2" or filename.endswith('.bz'):
            return filename[:-3], lambda f: bz2.BZ2File(f)

        elif content_type == "application/x-xz" or filename.endswith('.xz'):
            return filename[:-3], lambda f: lzma.LZMAFile(f)

    return filename, lambda f: f


def ftp_download_hashed_resource(resource, local_folder='', chunk_size=1 << 15, unzip=False, replace=False,
                                 filename_suffix_func=get_filename_indexed, delete_on_bad_hash=True):
    filename = resource.filename
    try:
        response = urllib.request.urlopen(resource.url)
        local_file = save_response_to_file(resource, local_folder, response, '',
                                           chunk_size, unzip, replace, response.info(), filename_suffix_func,
                                           delete_on_bad_hash)
        return response.getcode(), local_file
    except urllib.error.HTTPError as e:
        return e.getcode(), filename


def http_download_hashed_resource(resource, local_folder='', session=None, chunk_size=1 << 15, unzip=False,
                                  split_requests=False, replace=False, filename_suffix_func=get_filename_indexed,
                                  delete_on_bad_hash=True, **request_kwargs):
    sess = session or requests
    request_kwargs['stream'] = True
    r = sess.get(resource.url, **request_kwargs)
    r.raise_for_status()
    r.raw.decode_content = True
    status_code = r.status_code
    local_file = save_response_to_file(resource, local_folder, r.raw, r.headers['Content-Type'],
                                       chunk_size, unzip, replace, r.headers, filename_suffix_func,
                                       delete_on_bad_hash, sess, r)

    return status_code, local_file


def protocol_not_implemented(url):
    return not (url.startswith('https://') or url.startswith('http://') or url.startswith('ftp://'))


def convert_url_to_hashedurlresource(url, local_file_name='', hash_digest='', hash_algorithm='md5',
                                     assign_filename=False):
    from fdutils.web.web import HashedURLResource

    if isinstance(url, str):
        url = HashedURLResource(url, hash_digest, hash_algorithm)
        if assign_filename:
            url.filename = local_file_name
    elif not isinstance(url, HashedURLResource):
        raise ValueError("The URLs can only be string or HashURLResource instances. This ({}) is not.".format(url))
    return url


class FileHashError(Exception):
    """ raise when the digest provided is different to the hash calculated for a file """
