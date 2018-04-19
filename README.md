# FileSystemScan

File system scanner in Python. <br />
Creates SQLite snapshots of file system for later processing. <br />

Walks top-down the root directory and finds all subfolders and files. <br />
Calculates MD5 checksum for files (optionally). <br />
Saves file system info to SQLite database. <br />
Table 'Folders' contains the list of subfolders. <br />
Table 'Files' contains the list of files (folderId, file name, file size, create time, write time). <br />
Table 'FilesMD5' contains the list of MD5 checksums. <br />

You can scan all your HDD and FLASH drives. <br />
You can scan some folder only. <br />

Developed in 2011. <br />
