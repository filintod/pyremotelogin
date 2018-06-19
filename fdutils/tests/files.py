from fdutils.files import get_filename_indexed
import os


def test_name_get_filename_index_incremented():
    assert get_filename_indexed(os.path.join('files', 'hello.txt')) == os.path.join('files', 'hello_01.txt')
    assert get_filename_indexed(os.path.join('files', 'hello1.txt')) == os.path.join('files', 'hello1_01.txt')
    assert get_filename_indexed(os.path.join('files', 'hello2.txt')) == os.path.join('files', 'hello2_02.txt')
    assert get_filename_indexed(os.path.join('files', 'hello12_12.txt')) == os.path.join('files', 'hello12_13.txt')
    assert get_filename_indexed(os.path.join('files', 'hello_.txt')) == os.path.join('files', 'hello_01.txt')
    assert get_filename_indexed(os.path.join('files', 'hello_a.txt')) == os.path.join('files', 'hello_a_01.txt')
