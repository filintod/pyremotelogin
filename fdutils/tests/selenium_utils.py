from fdutils.selenium_util.locator_utils import locator
from fdutils.selenium_util.pageobject import PageObject

__author__ = 'Filinto Duran (duranto@gmail.com)'
import unittest

from fdutils.selenium_util import *


class Google(PageObject):

    q = locator('id=lst-ib')
    button = locator('name=btnk')

    def __init__(self):
        super().__init__(url='http://www.google.com', headless=True, driver='firefox')


class DownloadChrome(PageObject):
    download_button = locator("//a[contains(@class, 'button') and . = 'Download Chrome']")
    eula_accept_button = locator('id=eula-accept')

    def __init__(self):
        super().__init__(url='https://www.google.com/chrome/browser/desktop/#')


class DownloadPutty(PageObject):
    """class DownloadChrome(PageObject):
    download_button = locator("//a[contains(@class, 'button') and . = 'Download Chrome']")
    eula_accept_button = locator('id=eula-accept')

    def __init__(self):
        super(PageObject, self).__init__('https://www.google.com/chrome/browser/desktop/#')
https://the.earth.li/~sgtatham/putty/latest/x86/putty.exe"""
    download_link = locator("xp=(//a[.='putty.zip'])[1]")

    def __init__(self, **kwargs):
        super(PageObject, self).__init__('http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html', **kwargs)


import os
os.environ['PATH'] += r';c:\Users\duran\Downloads'

class TestSelenium(unittest.TestCase):

    def test_rg(self):
        with Google() as g:
            g.q = 'hello world\n'
            print('hello')

    def test_download(self):
        with DownloadPutty() as g:  # type: DownloadPutty
            g.download_link.click()
            print('hello')

        with DownloadPutty(driver=ChromeDriver) as g:  # type: DownloadPutty
            g.download_link.click()
            print('hello')






