# FileSystemScan

File system scanner in Python.
Creates SQLite snapshots of file system for later processing.

Walks top-down the root directory and finds all subfolders and files.
Calculates MD5 checksum for files (optionally).
Saves file system info to SQLite database.
Table 'Folders' contains the list of subfolders.
Table 'Files' contains the list of files (folderId, file name, file size, create time, write time).
Table 'FilesMD5' contains the list of MD5 checksums.

You can scan all your HDD and FLASH drives.
You can scan some folder only.

Developed in 2011.
