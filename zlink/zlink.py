#!/usr/bin/env python3

import argparse
import curses
#import logging
import minorimpact
import os
import sys

import zlink.note

def highlight(stdscr, select_y, select_x, mark_y, mark_x):
    selected = ""
    if (mark_y is not None and mark_x is not None):
        sy = select_y
        sx = select_x
        my = mark_y
        mx = mark_x
        if (my < sy):
            foo = sy
            sy = my
            my = foo
            foo = sx
            sx = mx
            mx = foo
        elif (mark_y == select_y):
            if (mark_x < select_x):
                foo = select_x
                sx = mark_x
                mx = foo

        if (my == sy):
            for x in range(sx, mx+1):
                stdscr.chgat(sy, x, 1, curses.A_REVERSE)
                #selected += str(stdscr.inch(sy, x))
                selected += chr(stdscr.inch(sy, x) & 0xFF)
        else:
            for y in range(sy, my+1):
                if (y==sy):
                    for x in range(sx, curses.COLS-2):
                        stdscr.chgat(y, x, 1, curses.A_REVERSE)
                        #selected += str(stdscr.inch(y, x))
                        selected += chr(stdscr.inch(y, x) & 0xFF)
                elif (y > sy and y < my):
                    for x in range(0, curses.COLS-2):
                        stdscr.chgat(y, x, 1, curses.A_REVERSE)
                        #selected += str(stdscr.inch(y, x))
                        selected += chr(stdscr.inch(y, x) & 0xFF)
                elif (y > sy and y==my):
                    for x in range(0, mx+1):
                        stdscr.chgat(y, x, 1, curses.A_REVERSE)
                        #selected += str(stdscr.inch(y, x))
                        selected += chr(stdscr.inch(y, x) & 0xFF)
                if (y < my):
                    selected = f"{selected}\n"
    else:
        stdscr.chgat(select_y, select_x, 1, curses.A_REVERSE)
        selected = chr(stdscr.inch(select_y, select_x) & 0xFF)
    return selected

def zl(stdscr):
    stdscr.clear()
    n = zlink.note.NoteBrowser()
    n.browse(stdscr)

def main():
    # I like 'vi', so that's the default editor.
    if ('EDITOR' not in os.environ):
        os.environ.setdefault('EDITOR', 'vi')

    # Hitting escape bungs everything up for a second; this reduces the delay.
    os.environ.setdefault('ESCDELAY', '15')

    #logging.basicConfig(level=logging.DEBUG, filename="./zlink.log")
    #logging.debug("-------")

    parser = argparse.ArgumentParser(description="Peruse and maintain a collection of Zettelkasten files in the current directory.")
    parser.add_argument('filename', nargs="?")
    parser.add_argument('--addlink', help = "add a link to ADDLINK to filename")
    parser.add_argument('--nobacklink', help = "when adding a link, don't create a backlink from filename to ADDLINK", action='store_true')
    parser.add_argument('--defrag', help = "update the zettelkasten files to remove any gaps between entries", action='store_true')
    args = parser.parse_args()

    if (args.addlink is not None and args.filename is not None):
        # Don't look at anything, just create a link from one file to another.
        note1 = zlink.note.Note(args.filename)
        note2 = zlink.note.Note(args.addlink)
        note1.addnotelink(note2)
        note1.write()
        print(f"Added link {note2.title} to {note1.title}")
        if (args.nobacklink is False):
            note2.addnotebacklink(note1)
            note2.write()
            print(f"Added backlink {note1.title} to {note2.title}")
        stdscr.refresh()
        sys.exit()
    elif (args.defrag is True):
        # Make this fix all the files so that there are no duplicate orders
        #  and no holes
        files = zlink.note.loadnotes()
        for i in range(0, len(files)):
            n = None
            try:
                n = zlink.note.Note(files[i])
            except:
                raise Exception(f"Can't open '{files[i]}'")

            if (n.order != i+1):
                original_file = n.filename
                n.updateorder(i+1)
                print(f"Moved {original_file} to {n.filename}")
                files[i] = n.filename

                for file in files:
                    scannote = zlink.note.Note(file)
                    scannote.updatelinks(original_file, n.filename)
        sys.exit()

    curses.wrapper(zl)


if __name__ == "__main__":
    main()
