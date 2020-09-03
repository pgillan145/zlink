import argparse
import curses
import datetime
import minorimpact
#import logging
import os
import os.path
import pyperclip
import re
import subprocess
import sys

import zlink
import zlink.globalvars

#######
# CLASSES
#######

class File():
    def __init__(self, filename):
        self.filename = filename
        self.data = []
        if (re.search("^\/", filename) is None):
            filename = os.path.abspath(self.filename)

        self.filename = filename
        with open(self.filename, "r") as f:
            for line in f:
                line = line.rstrip()
                self.data.append(line)

    def cursesoutput(self, stdscr, top = 0):
        stdscr.clear()
        output = []
        output.append(f"__BOLD__{self.filename}")
        for l in self.data:
            if (len(l) > 0):
                for i in minorimpact.splitstringlen(l, curses.COLS-2):
                    output.append(i)
            else:
                output.append(l)

        for i in range(0, len(output)):
            if (i < top): continue
            if (i >= (top + curses.LINES - 2 )): continue

            s = output[i]
            attr = 0
            if (re.match("^__REVERSE__", s)):
                s = s.replace("__REVERSE__", "")
                attr = curses.A_REVERSE
            elif (re.match("^__BOLD__", s)):
                s = s.replace("__BOLD__", "")
                attr = curses.A_BOLD

            s = s[:curses.COLS-1]
            stdscr.addstr(f"{s}\n", attr)

        return

    def lines(self, width=0):
        output = []
        for l in self.data:
            if (width > 0 and len(l)>0):
                for i in minorimpact.splitstringlen(l, width):
                    output.append(i)
            else:
                output.append(l)
        return len(output)

    def view(self, stdscr):
        command = None

        select = False
        file = None

        mark_y = None
        mark_x = None
        search = ""
        select_y = 0
        select_x = 0
        selected = 0
        top = 0
        while (True):
            stdscr.clear()

            # TODO: Add some kind of header that stays resident at the top of the screen.
            self.cursesoutput(stdscr, top)
            # TODO: Add some kind of header that stays resident at the top of the screen.

            status = ""
            if (select is True and mark_x is not None):
                status = f"{status} SELECTING2"
            elif (select is True):
                status = f"{status} SELECTING1"

            if (len(status) > 0):
                # Make sure a long status doesn't push
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            if (select is True):
                #c = stdscr.inch(select_y, select_x)
                #stdscr.insch(select_y, select_x, c, curses.A_REVERSE)
                zlink.zlink.highlight(stdscr, select_y, select_x, mark_y, mark_x)

            stdscr.refresh()
            command = stdscr.getkey()

            if (command == "q"):
                sys.exit()

            if (command == "KEY_DOWN"):
                if (select is True):
                    if (mark_y is not None):
                        if (mark_y < curses.LINES-2):
                            mark_y += 1
                    else:
                        if (select_y < curses.LINES-2):
                            select_y += 1
                    continue

                if (top < (self.lines(curses.COLS-2) - curses.LINES + 2)):
                    top += 1
            elif (command == "KEY_LEFT"):
                if (select is True):
                    if (mark_x is not None):
                        if (mark_x > 0):
                            mark_x -= 1
                    else:
                        if (select_x > 0):
                            select_x -= 1
                    continue
                return "PREV"
            elif (command == "KEY_RIGHT"):
                if (select is True):
                    if (mark_x is not None):
                        if (mark_x < curses.COLS-2):
                            mark_x += 1
                    else:
                        if (select_x < curses.COLS-2):
                            select_x += 1
                    continue
                return "NEXT"
            elif (command == "KEY_UP"):
                if (select is True):
                    if (mark_y is not None):
                        if (mark_y > 0):
                            mark_y -= 1
                    else:
                        if (select_y > 0):
                            select_y -= 1
                    continue
                if (top > 0):
                    top -= 1
            elif (command == "c"):
                # select text
                if (select is False):
                    select = True
                    select_y = 0
                    select_x = 0
                    mark_y = None
                    mark_x = None
                else:
                    mark_y = select_y
                    mark_x = select_x
            elif (command == "?"):
                stdscr.clear()
                stdscr.addstr("Editing Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" c              - enter selection mode to copy text to save the clipboard as a reference\n")
                stdscr.addstr(" q              - quit\n")
                stdscr.addstr(" ?              - this help screen\n")
                stdscr.addstr("\n")
                stdscr.addstr("Selection Mode Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" Use the arrow keys to move the cursor to the start of the text you want to select.  Press\n")
                stdscr.addstr(" <enter> to start highlighting; use the arrow keys to move the cursor to the end of the text\n")
                stdscr.addstr(" you want to select.  Press <enter> again to copy the text to the clipboard, along with a link\n")
                stdscr.addstr(" to this note\n")
                stdscr.addstr("\n")
				# TODO: Add pgup/pgdn/etc
                stdscr.addstr("Navigation Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" f              - open the file browser\n")
                stdscr.addstr(" <up>/<down>    - scroll through this file\n")
                stdscr.addstr(" <left>         - previous file\n")
                stdscr.addstr(" <right>        - next file\n")
                stdscr.addstr(" <esc>          - return to the previous page\n")

                stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                stdscr.refresh()
                command = stdscr.getkey()
            elif (command == "\n"):
                if (select):
                    if (mark_x is not None):
                        zlink.globalvars.link_filename = self.filename
                        zlink.globalvars.link_text = zlink.zlink.highlight(stdscr, select_y, select_x, mark_y, mark_x)
                        #pyperclip.copy(copy.__str__())
                        select = False
                        select_y = 0
                        select_x = 0
                        mark_y = None
                        mark_x = None
                        #return copy
                    else:
                        mark_y = select_y
                        mark_x = select_x
            elif (command == ''):
                if (select is True):
                    if (mark_x is not None):
                        mark_x = None
                        mark_y = None
                    else:
                        select = False
                    continue
                return
        return 

class FileBrowser():
    def browse(self, stdscr, filename=None):
        cwd = os.getcwd()
        command = None
        file = None

        if (filename is not None):
            if (re.search("^\/", filename)):
                cwd = os.path.dirname(filename)
            else:
                filename = os.path.normpath(os.path.join(cwd, filename))
            try:
                file = File(filename)
            except:
                file = None

        files = loadfiles(cwd)

        search = ""
        selected = 0
        top = 0
        while (command != ""):
            stdscr.clear()

            status = ""
            if (file is not None):
                newfile = file.view(stdscr)
                if (newfile is not None):
                    file = None
                    newselected = selected
                    while (file is None):
                        if (newfile == "PREV"):
                            newselected -= 1
                            if (newselected < 0):
                                newselected = len(files) - 1
                        elif (newfile == "NEXT"):
                            newselected += 1
                            if (newselected > len(files) - 1):
                                newselected = 0
                            break

                        filename = os.path.join(cwd,files[newselected])
                        if (os.path.isdir(filename) and newselected != selected):
                            continue
                        else:
                            file = File(filename)
                            selected = newselected
                else:
                    file = None
                continue
            else:
                for i in range(0,len(files)):
                    if (i < top): continue
                    if (i > (top + curses.LINES - 2 )): continue
                    f = files[i]
                    filename = os.path.normpath(os.path.join(cwd, f))
                    if (os.path.isdir(filename)):
                        f = f"{f}/"
                    max_width = curses.COLS - 2
                    if (i == selected):
                        stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f), curses.A_REVERSE)
                    else:
                        stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f))
                status = f"{selected+1} of {len(files)}"

            if (len(status) > 0):
                # Make sure a long status doesn't push
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            stdscr.refresh()
            command = stdscr.getkey()
            if (command == "KEY_DOWN" or command == "KEY_RIGHT"):
                selected += 1
                if (selected > top + (curses.LINES - 2)):
                    top = selected - (curses.LINES - 2)
                if (selected > len(files)-1):
                    selected = 0
                    top = 0
            elif (command == "KEY_UP" or command == "KEY_LEFT"):
                selected -= 1
                if (selected < top):
                    top = selected
                if (selected < 0):
                    selected = len(files)-1
                    top = 0
                    if (selected > top + (curses.LINES - 2)):
                        top = selected - (curses.LINES - 2)
            elif (command == "q"):
                sys.exit()
            elif (command == "?"):
                stdscr.clear()
                stdscr.addstr("\n")
                stdscr.addstr("Commands\n\n", curses.A_BOLD)
                # TODO: Add these navigation commands.
                #stdscr.addstr("<home>           - first note\n")
                #stdscr.addstr("<pgup> or ^u     - move the curser up one screen\n")
                #stdscr.addstr("<pgdown> or ^d   - move the curser up one screen\n")
                #stdscr.addstr("<end> or G       - last note\n")
                stdscr.addstr(" <up>/<down>    - next/previous file\n")
                stdscr.addstr(" <enter>        - open the selected file\n")
                stdscr.addstr(" <esc>          - return to the previous screen list\n")
                stdscr.addstr(" ?              - this help screen\n")

                stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                stdscr.refresh()
                command = stdscr.getkey()
            elif (command == "\n"):
                f = files[selected]
                filename = os.path.normpath(os.path.join(cwd,f))
                if (os.path.isdir(filename)):
                    cwd = filename
                    files = loadfiles(cwd)
                    selected = 0
                else:
                    file = File(filename)

def loadfiles(dir):
    dirs = []
    if (os.path.dirname(dir) != "/"):
        dirs.append("..")

    dirs.extend([f for f in os.listdir(dir) if(os.path.isdir(os.path.join(dir, f)))])
    dirs.sort()
    files = [f for f in os.listdir(dir) if(os.path.isfile(os.path.join(dir, f)) and re.search("\.(md|txt|html)$",f))]
    files.sort()
    dirs.extend(files)
    return dirs 

