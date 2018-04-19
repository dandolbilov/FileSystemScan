# -*- coding: utf-8 -*-
"""
    File:    helpers.py
    Author:  Daniil Dolbilov
    Created: 12-Feb-2011
"""

import logging
import sys
import os
import hashlib
import time


def initLogs(fileName, fileAppend=True, fileLevel=logging.DEBUG, consoleLevel=logging.INFO):
    """Creates two loggers: 1) to file, 2) to console.
    """
    # log messages format
    outFormat = "%(asctime)s %(levelname)-8s %(message)s"
    # output stream for console handler
    outStream = sys.stderr

    # 1) set up logging to file
    # ~~~~~~~~~~~~~~~~~~~~~~~~~
    mode = "a" if fileAppend else "w"
    logging.basicConfig(level=fileLevel, filename=fileName, format=outFormat, filemode=mode)

    # 2) set up logging to console
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # define a Handler
    # which writes [consoleLevel] messages or higher to [outStream]
    console = logging.StreamHandler(outStream)
    console.setLevel(consoleLevel)
    # set a format for console
    formatter = logging.Formatter(outFormat)
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger("").addHandler(console)


def normpathEx(path):
    """ Normalize a pathname and convert backward slashes to forward slashes.
    """
    return os.path.normpath(path).replace('\\', '/').rstrip('/') + '/'  # ---


def calcMD5(data):
    """Calculates MD5 checksum for data.

    Returns:
        Hex string in uppercase with MD5 checksum of data.
    """
    return hashlib.md5(str(data)).hexdigest().upper()


def calcFileMD5(fname):
    """Calculates MD5 checksum for file.

    Returns:
        Hex string in uppercase with MD5 checksum of file.
    """
    try:
        f = open(fname, "rb")
        buf = f.read(1)  # first chunk
        sum_ = hashlib.md5(buf)
        while len(buf) > 0:
            buf = f.read(1024*100)  # next chunk
            sum_.update(buf)
        f.close()
        return sum_.hexdigest().upper()
    except IOError:
        return ""


def getFileTimes(fname, gmt=True, checkMT=True):
    """Gets timestamps of file (creation time, modification time).

    Args:
        gmt: If True, return timestamps in UTC.
        checkMT: If True, fix timestamps if creation_time > modification_time.

    Returns:
        Tuple of two strings (creation time, modification time).
        If failed returns ('1970-01-01 05:00:00', '1970-01-01 05:00:00').
    """
    try:
        fs = "%Y-%m-%d %H:%M:%S"  # datetime string format
        os.stat_float_times(False)
        if gmt:
            ct = time.gmtime(os.path.getctime(fname))
            mt = time.gmtime(os.path.getmtime(fname))
        else:
            ct = time.localtime(os.path.getctime(fname))
            mt = time.localtime(os.path.getmtime(fname))
        if checkMT:
            # TODO(dan.dolbilov): Fix timestamps if creation_time > modification_time (creation_time is overwritten).
            # datetime.strptime(ctime,self.dateFormat) > datetime.strptime(mtime,self.dateFormat)
            pass  # --- if ct > mt: ct = mt
        return time.strftime(fs, ct), time.strftime(fs, mt)
    except OSError:
        return '1970-01-01 05:00:00', '1970-01-01 05:00:00'
