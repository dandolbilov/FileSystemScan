# -*- coding: utf-8 -*-
"""
    File:    FileSystemImage.py
    Author:  Daniil Dolbilov
    Created: 02-Jun-2011
"""

import logging
import sys
import os
from datetime import datetime
from helpers import initLogs, normpathEx, calcMD5, calcFileMD5, getFileTimes
from GateSQLite import GateSQLite


class FileSystemImage:
    """File system scanner.
    Walks top-down the root directory and finds all subfolders and files.
    Calculates MD5 checksum for files (optionally).
    Saves file system info to SQLite database.
    Table 'Folders' contains the list of subfolders.
    Table 'Files' contains the list of files (folderId, file name, file size, create time, write time).
    Table 'FilesMD5' contains the list of MD5 checksums.

    Attributes:
       dbgate: GateSQLite database connection.
       rootDir: The root directory to scan.
       excludeList: The list of subfolders to exclude from scan list.
    """

    def __init__(self, dbname):
        """Inits FileSystemImage object with database file name or ':memory:'.
        """
        self.dbgate = GateSQLite(dbname)
        self.dbgate.needTables(['Folders', 'Files', 'FilesMD5', 'ScanParams'])

        self.rootDir = ''
        self.excludeList = []

    def loadScanParams(self):
        """Loads scan parameters from 'ScanParams' table.
        Used by createImage() and calcMD5forFiles().

        Returns:
            True or False.
        """

        # load the root directory
        rootName = 'RootDirWin32' if sys.platform == "win32" else 'RootDirLinux'
        q = self.dbgate.query("select value from ScanParams where name = '%s'" % rootName.replace("'", "''"))
        if not q or len(q) != 1:
            logging.error('load param [%s] failed' % rootName)
            return False
        self.rootDir = normpathEx(q[0][0])

        # load the exclude list
        q = self.dbgate.query("select value from ScanParams where name like 'ExcludePath%'")
        if q is None:
            logging.error('load params [ExcludePath] failed')
            return False
        for row in q:
            self.excludeList.append(row[0].replace('\\', '/').lower())

        return True

    def createImage(self, scanParams):
        """Creates SQLite image of the root directory without MD5 checksums.

        Args:
            scanParams: Dict of parameters ('RootDirWin32', 'RootDirLinux', 'StorageName', 'ExcludePath1'..'ExcludePath%').

        Returns:
            True or False.
        """

        # define database schema
        self.dbgate.defineTable('Folders', 'foId integer primary key AUTOINCREMENT, path text, scanTime text')
        self.dbgate.defineTable('Files',
                                'fileId integer primary key AUTOINCREMENT, foId integer, fname text, fsize integer, ctime text, wtime text')
        self.dbgate.defineTable('FilesMD5', 'fileId integer primary key, md5 text, calcTime text')
        self.dbgate.defineTable('ScanParams', 'name text, value text')

        # connect to database and validate/create database schema
        if not self.dbgate.openConn():
            return False

        # check that all the tables are empty
        for tableName in self.dbgate.ntables:
            q = self.dbgate.query("select count(1) from %s" % tableName)
            if not q:
                logging.error('createImage, tables empty validate failed')
                return False
            if q[0][0]:
                logging.error('createImage, table [%s] is not empty' % tableName)
                return False

        # save scan parameters to database
        for pname in scanParams.keys():
            q = self.dbgate.query("insert into ScanParams (name, value) select '%s', '%s'" % (pname, scanParams[pname]))
            if q is None:
                logging.error('createImage, save scanParams to database failed')
                return False

        # load scan parameters from database
        if not self.loadScanParams():
            return False

        self.dbgate.trace('create-image-start', 'root=[%s], ignore=%s' % (self.rootDir, str(self.excludeList)))

        nScaned = 0
        nDirs = 1  # it's root dir
        nFiles = 0

        # scan directory tree
        for root, dirs, files in os.walk(self.rootDir):

            # TODO(dan.dolbilov): Do ignore symlinks.
            # if os.path.islink(root):
            #    self.dbgate.trace('dir-ignored-islink', '[%s]' % normpathEx(root) )
            #    continue

            curDir = normpathEx(root)

            curDirId, curPath = self.onFolderScanBegin(curDir)
            if curDirId < 0:
                continue

            # save subfolders
            if not self.addFolders(curPath, dirs):
                self.dbgate.trace('error', 'addFolders for path "%s" (id = %i) failed' % (curPath, curDirId))
                return False

            # save files
            if not self.addFiles(curDirId, curDir, files):
                self.dbgate.trace('error', 'addFiles for path "%s" (id = %i) failed' % (curPath, curDirId))
                return False

            # increment counters
            nScaned += 1
            nDirs += len(dirs)
            nFiles += len(files)

            # find subfolders to ignore
            ignored = []
            for dirName in dirs:
                dirFull = normpathEx(curDir + dirName).lower()
                for excPath in self.excludeList:
                    if dirFull.find(excPath) != -1:
                        ignored.append(dirName)
                        break
            # exclude ignored subfolders from scan list
            for dir_ in ignored:
                dirs.remove(dir_)  # don't visit directories
                self.dbgate.trace('dir-ignored', '[%s]' % normpathEx(curDir + dir_))

        self.dbgate.trace('create-image-done', 'dirs=%i, files=%i, dirs-scaned=%i' % (nDirs, nFiles, nScaned))

        return True

    def onFolderScanBegin(self, curDir):
        """For internal usage.
        """
        timeStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # not GMT

        # check that curDir begins with rootDir
        if curDir.find(self.rootDir) != 0:
            self.dbgate.trace('error', 'curDir "%s" must begins with rootDir' % curDir)
            return -1, ''

        # remove rootDir from curDir (work with relative path)
        curPath = curDir[len(self.rootDir) - 1:]

        # do initial insert for the root directory
        if curPath == '/':
            q = self.dbgate.query("insert into Folders (path) select '/'")
            if q is None:
                self.dbgate.trace('error', 'insert rootDir failed')

        # find folder id for curDir
        q = self.dbgate.query("select foId from Folders where path = '%s'" % curPath.replace("'", "''"))
        if not q or len(q) != 1:
            self.dbgate.trace('error', 'path "%s" not found in Folders' % curPath)
            return -2, curPath

        curDirId = q[0][0]

        # set scanTime for curDir
        q = self.dbgate.query("update Folders set scanTime = '%s' where foId = %i" % (timeStr, curDirId))
        if q is None:
            self.dbgate.trace('warning', 'update Folders for path "%s" (id = %i) failed' % (curPath, curDirId))

        return curDirId, curPath

    def addFolders(self, curPath, dirs):
        """For internal usage.
        """
        sql = ''
        qsz = 0
        for dirName in dirs:
            path_ = normpathEx(curPath + dirName)
            sql += (" union all " if sql else " insert into Folders (path) ")
            sql += " select '%s' " % path_.replace("'", "''")
            qsz += 1

            # insert 100 rows at a time to prevent overflow ("too many terms in compound SELECT")
            if qsz >= 100:
                if self.dbgate.query(sql) is None:
                    return False
                sql = ''
                qsz = 0

        if sql:
            return self.dbgate.query(sql) is not None

        return True

    def addFiles(self, curDirId, curDir, files):
        """For internal usage.
        """
        sql = ''
        qsz = 0
        for fname in files:
            fullName = curDir + fname

            fsize = 0
            try:
                fsize = os.path.getsize(fullName)
            except OSError:
                self.dbgate.trace('error', 'getsize() failed for file "%s"' % fullName)

            ctime, wtime = getFileTimes(fullName, gmt=False)  # not GMT
            sql += (" union all " if sql else " insert into Files (foId, fname, fsize, ctime, wtime) ")
            sql += " select %i, '%s', %i, '%s', '%s' " % (curDirId, fname.replace("'", "''"), fsize, ctime, wtime)
            qsz += 1

            # insert 100 rows at a time to prevent overflow ("too many terms in compound SELECT")
            if qsz >= 100:
                if self.dbgate.query(sql) is None:
                    return False
                sql = ''
                qsz = 0

        if sql:
            return self.dbgate.query(sql) is not None

        return True

    def calcMD5forFiles(self, whereSql, addOnly):
        """Calculates MD5 checksum for files.

        Args:
            whereSql: A filter for files (for example, use "fname like '%'" to calculate MD5 for all files).
            addOnly: If True, do not recalculate existing MD5 checksums (calculate MD5 for files without MD5).

        Returns:
            True or False.
        """

        # connect to database
        if not self.dbgate.openConn():
            return False

        # load scan parameters from database
        if not self.loadScanParams():
            return False

        self.dbgate.trace('calc-md5-start', 'where=[%s], add-only=%s' % (whereSql, str(addOnly)))

        # fetch timestamps of existing MD5 checksums
        hasMD5 = {}
        q0 = self.dbgate.query("select fileId, calcTime from FilesMD5")
        if q0 is None:
            self.dbgate.trace('error', 'select md5 timestamps failed')
            return False
        for row in q0:
            fileId = int(row[0])
            hasMD5[fileId] = row[1]

        # fetch the list of files to calculate MD5 checksums for
        q = self.dbgate.query("select ff.fileId, ff.fsize, ff.fname, fo.path "
                              " from Files ff, Folders fo where ff.foId = fo.foId "
                              " and (" + whereSql + ")")
        if q is None:
            self.dbgate.trace('error', 'select files for md5 calc failed')
            return False

        nFiles = len(q)
        nHasMD5 = nCalcMD5 = 0

        bytes_ = 0
        time1 = datetime.now()

        for row in q:
            fileId = int(row[0])
            fsize = int(row[1])
            fname = normpathEx(self.rootDir + row[3]) + row[2]

            if fileId in hasMD5.keys():
                nHasMD5 += 1
                if addOnly:
                    continue

            # check/update file size
            fsize2 = 0
            try:
                fsize2 = os.path.getsize(fname)
            except OSError:
                self.dbgate.trace('error', 'getsize() failed for file "%s"' % fname)
            if fsize2 != fsize:
                self.dbgate.trace('fsize-changed', '[%s], %i => %i' % (fname, fsize, fsize2))
                q2 = self.dbgate.query("update Files set fsize = %i where fileId = %i" % (fsize2, fileId))
                if q2 is None:
                    self.dbgate.trace('warning', 'fsize for "%s" not updated' % fname)

            # calculate MD5
            md5 = calcFileMD5(fname) if fsize2 > 0 else calcMD5('')

            timeStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # not GMT

            logging.debug('%5i %8s   %s   %s' % (fileId, fsize, md5, fname))

            # save MD5 to database
            sql = "insert into FilesMD5 (fileId, md5, calcTime) select %i, '%s', '%s'" % (fileId, md5, timeStr)
            if fileId in hasMD5.keys():
                sql = "update FilesMD5 set md5 = '%s', calcTime = '%s' where fileId = %i" % (md5, timeStr, fileId)
            if self.dbgate.query(sql) is None:
                self.dbgate.trace('warning', 'md5 for "%s" not saved' % fname)

            nCalcMD5 += 1
            bytes_ += fsize2

        # calculate MD5 speed (MB/s, megabyte per second)
        dt = datetime.now() - time1
        ms = float(dt.seconds) * 1000.0 + float(dt.microseconds) / 1000.0
        kb = float(bytes_) / 1024.0
        rate = int(kb / ms)
        # TODO(dan.dolbilov): Fix MD5 speed calculation (it's not MB/s and not MiB/s now).

        self.dbgate.trace('calc-md5-done',
                          'files=%i, has-md5=%i, calc-md5=%i, rate=%iMB/s' % (nFiles, nHasMD5, nCalcMD5, rate))

        return True


def test_FileSystemImage():
    """Simple test.
    """
    initLogs(u"test_FileSystemImage.log", fileAppend=False, fileLevel=logging.DEBUG, consoleLevel=logging.INFO)

    params = {'RootDirWin32': u'F:\\', 'RootDirLinux': u'/media/FLASH4GB/', 'StorageName': u'FLASH4GB',
              'ExcludePath1': u'/RECYCLER/', 'ExcludePath2': u'/$RECYCLE.BIN/', 'ExcludePath3': u'/.svn/'}

    FileSystemImage('test_FileSystemImage.sqlite').createImage(params)

    FileSystemImage('test_FileSystemImage.sqlite').calcMD5forFiles("fname like '%'", True)


if __name__ == '__main__':
    """Run Simple test.
    """
    test_FileSystemImage()
