# -*- coding: utf-8 -*-
"""
    File:    doScan.py
    Author:  Daniil Dolbilov
    Created: 02-Jun-2011
"""

import logging
import sys
import os
from datetime import datetime
from helpers import initLogs
from FileSystemImage import FileSystemImage


if __name__ == '__main__':
    """Scan your HDD and FLASH drives.
    """
    initLogs(u"doScan.log", fileAppend=False, fileLevel=logging.INFO, consoleLevel=logging.INFO)

    scans = {}
    scans['asus1win7-%date%.sqlite'] = {'StorageName':u'ASUS-sda2-ntfs-58GB',    'RootDirWin32':u'C:/', 'RootDirLinux':u'/media/OS/',       'ExcludePath1':u'/RECYCLER/', 'ExcludePath2':u'/$RECYCLE.BIN/'}
    scans['asus2data-%date%.sqlite'] = {'StorageName':u'ASUS-sda5-ntfs-100GB',   'RootDirWin32':u'D:/', 'RootDirLinux':u'/media/DATA/',     'ExcludePath4':u'/list-files/', 'ExcludePath3':u'/.svn/', 'ExcludePath1':u'/RECYCLER/', 'ExcludePath2':u'/$RECYCLE.BIN/'}
    scans['flash4gb-%date%.sqlite']  = {'StorageName':u'FLASH4GB-sdb1-ntfs-4GB', 'RootDirWin32':u'F:/', 'RootDirLinux':u'/media/FLASH4GB/', 'ExcludePath1':u'/RECYCLER/', 'ExcludePath2':u'/$RECYCLE.BIN/'}

    saveDir = 'D:/list-files/' if sys.platform == "win32" else '/media/DATA/list-files/'
    if not os.path.exists(saveDir):
        os.mkdir(saveDir)

#   for name in ['asus1win7-%date%.sqlite', 'asus2data-%date%.sqlite', 'flash4gb-%date%.sqlite']:
    for name in ['asus2data-%date%.sqlite']:
        if name not in scans.keys():
            logging.error('scans has no "%s"' % name)
            continue

        dbname = saveDir + name.replace('%date%', datetime.now().strftime("%Y.%m.%d"))
        params = scans[name]

        FileSystemImage(dbname).createImage(params)
        FileSystemImage(dbname).calcMD5forFiles("fname like '%'", True)  # "fsize < 100*1024*1024"
