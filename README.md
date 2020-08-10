# zlink
A command line script for navigating and editing Zettelkasten files.

## Usage
```
usage: zlink [-h] [--addlink ADDLINK] [--nobacklink] [--defrag] [filename]

Peruse and maintain a collection of Zettelkasten files in the current
directory.

positional arguments:
  filename

optional arguments:  
  -h, --help         show this help message and exit
  --addlink ADDLINK  add a link to ADDLINK to filename
  --nobacklink       when adding a link, don't create a backlink from filename
                     to ADDLINK
  --defrag           update the zettelkasten files to remove any gaps between
                     entries
```
