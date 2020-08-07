# zlink
A command line script for navigating and editing Zettelkasten files.

## Usage
```
zlink.py [-h] [--addlink ADDLINK] [--nobacklink] [filename]

Peruse and maintain a collection of Zettelkasten files.

positional arguments:
  filename

optional arguments:  
  -h, --help         show this help message and exit
  --addlink ADDLINK  add a link to ADDLINK to filename
  --nobacklink       when adding a link, don't create a backlink from filename
                     to ADDLINK
```
