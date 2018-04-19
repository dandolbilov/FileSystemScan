# -*- coding: utf-8 -*-
"""
    File:    GateSQLite.py
    Author:  Daniil Dolbilov
    Created: 12-Feb-2011
"""

import logging
import sqlite3
from datetime import datetime


class GateSQLite:
    """SQLite database connection wrapper.

    Attributes:
       dbname: The name of SQLite database file.
       con: SQLite database connection (sqlite3.Connection).
       ntables: List of table names (need tables).
       dtables: Dict of table schema sql strings (define tables).
    """

    def __init__(self, dbname):
        """Inits GateSQLite object with database file name or ':memory:'.
        """
        self.dbname = dbname
        self.con = None

        self.ntables = []
        self.dtables = {}

        # database always has 'History' table for trace records
        self.ntables.append('History')
        self.defineTable('History', 'timestamp text, event text, msg text')

    def needTables(self, tableNames):
        """Sets list of used tables.
        """
        logging.debug('need tables: %s' % str(tableNames))
        self.ntables = tableNames
        self.ntables.append('History')

    def defineTable(self, tableName, columnsStr):
        """Sets columns for table.
        """
        tableSql = "create table " + tableName + " (" + columnsStr + ")"
        self.dtables[tableName] = tableSql

    def trace(self, event, msg):
        """Logs some message to logging and to 'History' table.
        """
        timeStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # not GMT

        if event == 'error':
            logging.error(msg)
        elif event == 'warning':
            logging.warning(msg)
        else:
            logging.info(event + ', ' + msg)

        v = " select '%s', '%s', '%s' " % (timeStr, event.replace("'", "''"), msg.replace("'", "''"))
        q = self.query("insert into History (timestamp, event, msg) " + v)
        if q is None:
            pass  # TODO(dan.dolbilov): Handle query error.

    def openConn(self):
        """Connects to database and validates/creates database schema.

        Returns:
            True or False.
        """

        # connect to database
        logging.debug('sqlite3 open(%s)' % self.dbname)
        if not self.open():
            logging.error('sqlite3 open failed')
            return False
        logging.debug('sqlite3 open OK')

        # validate database schema
        for tableName in self.ntables:
            # get expected table schema
            sql2 = self.dtables[tableName] if tableName in self.dtables.keys() else ""

            # check if table already exists in database
            q = self.query("select sql from sqlite_master where name = '" + tableName + "'")
            if not q:
                pass  # TODO(dan.dolbilov): Handle query error.

            if len(q) > 0:
                # if table already exists in database => get existing table schema
                sql1 = str(q[0][0])
                # compare expected and existing table schemas
                if len(sql2) > 0 and sql1.lower() != sql2.lower():
                    logging.error('schema mismatch, "%s" <> "%s"' % (sql1, sql2))
                    return False
            else:
                # if table not exists in database => create table with expected table schema
                if not sql2:
                    logging.error('create table, table "%s" is not defined' % tableName)
                    return False
                q2 = self.query(sql2)
                if q2 is None:
                    logging.error('create table, "%s"' % sql2)
                    return False
        return True

    def query(self, queryStr):
        """Executes SQL query and fetches all rows of a query result.

        Returns:
            List of rows or None.
        """
        try:
            logging.debug('query = "%s"' % queryStr)
            cur = self.con.cursor()
            cur.execute(queryStr)
            rows = cur.fetchall()
            logging.debug("rowcount = " + str(len(rows)))
            return rows
        except sqlite3.Error, e:
            logging.exception(e.args[0])
            return None  # --- return []

    def open(self):
        """Opens sqlite3 connection.

        Returns:
            True or False.
        """
        try:
            self.con = sqlite3.connect(self.dbname)
            self.con.text_factory = unicode  # --- str
            self.con.isolation_level = None
            return True
        except sqlite3.Error, e:
            logging.exception(e.args[0])
            return False

    def close(self):
        """Closes sqlite3 connection.
        """
        try:
            self.con.close()
        except sqlite3.Error, e:
            logging.exception(e.args[0])
