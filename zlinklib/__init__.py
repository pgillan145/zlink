import argparse
import curses
import datetime
import logging
import minorimpact
import os
import os.path
import pyperclip
import re
import subprocess
import sys

import globalvars

#######
# CLASSES
#######

class InvalidNoteException(Exception):
    def __init__(self, message):
        super().__init__(message)

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

        #logging.debug(f"LINES:{curses.LINES}, COLS:{curses.COLS}")
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
            #logging.debug(f"{i}({len(s)}):{s}")
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

            self.cursesoutput(stdscr, top)

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
                highlight(stdscr, select_y, select_x, mark_y, mark_x)

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
            elif (command == "\n"):
                if (select):
                    if (mark_x is not None):
                        text = highlight(stdscr, select_y, select_x, mark_y, mark_x)
                        link = Link(self.filename)
                        globalvars.copy = Reference(link, text)
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
                logging.debug(f"setting cwd to {cwd}")
            else:
                filename = os.path.normpath(os.path.join(cwd, filename))
            try:
                logging.debug(f"using {filename}")
                file = File(filename)
            except:
                file = None

        files = loadfiles(cwd)

        select = False

        mark_y = None
        mark_x = None
        search = ""
        select_y = 0
        select_x = 0
        selected = 0
        top = 0
        while (command != ""):
            stdscr.clear()

            status = ""
            if (file is not None):
                newfile = file.view(stdscr)
                if (newfile is not None):
                    #logging.debug(f"newfile:{newfile}")
                    file = None
                    newselected = selected
                    while (file is None):
                        if (newfile == "PREV"):
                            logging.debug("back one")
                            newselected -= 1
                            if (newselected < 0):
                                newselected = len(files) - 1
                        elif (newfile == "NEXT"):
                            logging.debug("forward one")
                            newselected += 1
                            if (newselected > len(files) - 1):
                                newselected = 0
                        elif (isinstance(newfile, Reference)):
                            return newfile
                        else:
                            break
                        #logging.debug(f"selected:{selected}")

                        filename = os.path.join(cwd,files[newselected])
                        if (os.path.isdir(filename) and newselected != selected):
                            logging.debug("this is a directory, go again")
                            continue
                        else:
                            file = File(filename)
                            selected = newselected
                else:
                    file = None
                continue
            else:
                top = gettop(selected, top, len(files)-1)
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

            if (status is True and mark_x is not None):
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
                highlight(stdscr, select_y, select_x, mark_y, mark_x)

            stdscr.refresh()
            command = stdscr.getkey()
            if (command == "KEY_DOWN" or command == "KEY_RIGHT"):
                selected += 1
                if (selected > len(files)-1):
                    selected = 0
            elif (command == "KEY_UP" or command == "KEY_LEFT"):
                selected -= 1
                if (selected < 0):
                    selected = len(files)-1
            elif (command == "q"):
                sys.exit()
            elif (command == "\n"):
                f = files[selected]
                filename = os.path.normpath(os.path.join(cwd,f))
                logging.debug(f"viewing {f}")
                if (os.path.isdir(filename)):
                    cwd = filename
                    logging.debug(f"cwd is now {cwd}")
                    files = loadfiles(cwd)
                    selected = 0
                else:
                    file = File(filename)
        
# A text and a url.
class Link():
    def __init__(self, url, text=None):
        self.url = url
        if (text is None):
            self.text = url
        else:
            self.text = text

    def __str__(self):
        return f"[{self.text}]({self.url})"

# A link that also contains a bit of text for context.
class Reference():
    def __init__(self, link, text = None):
        self.text = text
        self.link = link

    def __str__(self):
        str = f"{self.link}"
        if (self.text is not None):
            str = str + f"\n> {self.text}"
        return str

    def search(self, search_string):
        if (self.text is not None):
            m = re.search(search_string, self.text.lower())
            if (m): return True

# Each note is a separate file.
class Note():
    def __init__(self, filename):
        self.filename = filename
        self.order, self.id, self.title = self.parseurl()
        self.tags = []

        self.parsed = self.parsefile()

        self.default = self.parsed['default']
        self.links = self.parselinks()
        self.backlinks = self.parselinks("backlinks")
        self.references = self.parsereferences()

    def __str__(self):
        str = ""
        #if (self.id is not None):
        #    str = str + f"[_metadata_:id]:- {self.id}\n"
        if (len(self.tags) > 0):
            str = str + f"[_metadata_:tags]:- " + ",".join(self.tags) + "\n"

        if (len(str) > 0): str = str + "\n"
        for i in self.default:
            str = str + i + "\n"
        str = str + "\n"

        str = str + "### Links\n"
        for i in self.links:
            str = f"{str}{i}\n"
        str = str + "\n"
                
        str = str + "### Backlinks\n"
        for i in self.backlinks:
            str = f"{str}{i}\n"
        str = str + "\n"
                
        str = str + "### References\n"
        for i in self.references:
            str = f"{str}{i}\n\n"
        str = str + "\n"

        return str

    def addbacklink(self, link):
        if (link is not None):
            self.backlinks.append(link)

    def addlink(self, link):
        if (link is not None):
            self.links.append(link)

    def addnotebacklink(self, note):
        l = Link(note.filename, note.title)
        self.addbacklink(l)

    def addnotelink(self, note):
        l = Link(note.filename, note.title)
        self.addlink(l)

    def addreference(self, reference):
        self.references.append(reference)

    def cursesoutput(self, stdscr, selected = 0, top = 0):
        #stdscr.scrollok(True)
        output = []
        current = 0
        output.append(f"__BOLD__{self.title}")
        if (len(self.tags) > 0):
            output.append(f"tags: #" + ",#".join(self.tags) + "")
            output.append("")

        if (len(self.tags) > 0 or self.id is not None): 
            output.append("")
        for i in self.default:
            foo = minorimpact.splitstringlen(i,curses.COLS - 2)
            for f in foo:
                output.append(f"{f}")
        output.append("")

        output.append("### Links")
        for i in self.links:
            current += 1
            if (selected == 0 and current == 1 and len(output) < curses.LINES -2):
                selected = 1
            if (selected == current):
                output.append(f"__REVERSE__{i.text}")
                if (len(output) > curses.LINES + top - 2):
                    top = len(output) - curses.LINES + 5
            else:
                output.append(f"{i.text}")
        output.append("")

        output.append("### Backlinks")
        for i in self.backlinks:
            current += 1
            if (selected == 0 and current == 1 and len(output) < curses.LINES -2):
                selected = 1
            if (selected == current):
                output.append(f"__REVERSE__{i.text}")
                if (len(output) > curses.LINES + top - 2):
                    top = len(output) - curses.LINES + 5
            else:
                output.append(f"{i.text}")
        output.append("")

        output.append("### References")
        for i in self.references:
            current += 1
            if (selected == 0 and current == 1 and len(output) < curses.LINES -2):
                selected = 1

            if (selected == current or selected == 0):
                output.append(f"__REVERSE__{i.link}")
                if (len(output) > top + curses.LINES - 2):
                    top = len(output) - curses.LINES + 5
            else:
                output.append(f"{i.link}")

            if (i.text is not None):
                foo = minorimpact.splitstringlen(i.text,curses.COLS - 2)
                for f in foo:
                    output.append(f"> {f}")
            output.append("")

        for i in range(0, len(output)):
            s = output[i]
 
            attr = 0
            if (re.match("^__REVERSE__", output[i])):
                s = s.replace("__REVERSE__", "")
                attr = curses.A_REVERSE
            elif (re.match("^__BOLD__", output[i])):
                s = s.replace("__BOLD__", "")
                attr = curses.A_BOLD

            if (i < top): continue
            if (i >= top + curses.LINES - 2): continue

            s = s[:curses.COLS-1]
            stdscr.addstr(f"{s}\n", attr)

        return selected

    def delete(self):
        os.remove(self.filename)

    def deletelink(self, selected):
        link = self.getlink(selected)
        if (link is None):
            logging.debug("no link passed to deletelink")
            return

        try:
            self.links.remove(link)
        except ValueError:
            pass

        try:
            self.backlinks.remove(link)
        except ValueError:
            pass

        logging.debug(f"looking for {link} in references")
        for r in self.references:
            if (r.link == link):
                try:
                    self.references.remove(r)
                except ValueError:
                    pass

    # Return a particular link.  This will return the links from reference
    #   objects, so if you're looking for this link later you need to dig into
    #   each item in the references array.
    def getlink(self, selected):
        current = 1
        logging.debug(f"{selected} of {self.linkcount()}")
        if (selected < 1 or selected > self.linkcount()):
            return
        for i in self.links:
            if (selected == current):
                return i
            current += 1
                
        for i in self.backlinks:
            if (selected == current):
                return i
            current += 1

        for i in self.references:
            if (selected == current):
                return i.link
            current += 1

    def linkcount(self):
        count = 0
        count += len(self.links)
        count += len(self.backlinks)
        count += len(self.references)
        return count

    def parsefile(self):
        lines = {}
        try:
            with open(self.filename, "r") as f:
                lines = [line.rstrip() for line in f]
        except FileNotFoundError:
            pass
        data = {"default": [] }
        section = "default"
        for l in lines:
            # collect metadata
            m = re.search("^\[_metadata_:(.+)\]:- +(.+)$", l)
            if (m):
                key = m.group(1)
                value = m.group(2)
                if (key == "id"): 
                    #self.id = value
                    pass
                elif (key == "tags"):
                    for tag in value.split(","):
                        self.tags.append(tag.strip())
                continue

            m = re.search("^#+ (.+)$", l)
            if (m):
                section = m.group(1).lower()
                if (section not in data):
                    #print(f"adding new section {section}")
                    data[section] = []
                continue

            if len(data[section]) == 0 and len(l) == 0:
                continue

            data[section].append(l)
           
        # get rid of trailing blank lines
        for section in data:
            if (len(data[section]) > 0):
                while len(data[section][-1]) == 0:
                    data[section].pop(-1)
        return data

    def parselinks(self, section="links"):
        data = []
        if (section not in self.parsed):
            return data

        for l in self.parsed[section]:
            m = re.search("\[(.+)\]\((.+)\)", l)
            if (m):
                data.append(Link(m.group(2),m.group(1)))
        return data

    def parsereferences(self, section="references"):
        data = []
        if (section not in self.parsed):
            return data
        text = None
        link = None
        for l in self.parsed[section]:
            if (len(l) == 0 or (link is not None and text is not None)):
                if (link):
                    data.append(Reference(link, text))
                text = None
                link = None
                continue

            m = re.search("\[(.+)\]\((.+)\)", l)
            if (m):
                link = Link(m.group(2), m.group(1))
            m = re.search("^> (.+)$", l)
            if (m):
                text = m.group(1)
            
        if (link):
            data.append(Reference(link, text))
        return data

    def parseurl(self):
        order = None
        title = self.filename
        id = None
        m = re.match("(\d+) - (.+) - (.*)\.md$", title)
        if (m):
            order = int(m.group(1))
            id = m.group(2)
            title = m.group(3)
        else:
            raise(InvalidNoteException(f"{self.filename} is not a valid Note"))
        return order, id, title

    def reload(self):
        self.__init__(self.filename)

    def search(self, search_string):
        m = re.search(search_string, self.title.lower())
        if (m): return True
        m = re.search(search_string, self.id.lower())
        if (m): return True
        for t in self.tags:
            m = re.search(search_string, t.lower())
            if (m): return True
        for l in self.default:
            m = re.search(search_string, l.lower())
            if (m): return True

        for r in self.references:
            if (r.search(search_string) is True):
                return True

    # Change the order value of the current note.
    def updateorder(self, new_order):
        original_file = self.filename
        self.order = new_order
        self.filename = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        os.rename(original_file, self.filename)

    def updatetags(self, new_tags):
        tags = new_tags.split(",")
        for i,t in enumerate(tags):
            tags[i] = t.strip()
        self.tags = tags
        self.write()

    def updatetitle(self, new_title):
        original_file = self.filename
        self.title = new_title
        self.filename = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        os.rename(original_file, self.filename)

    def updatelinks(self, url, new_url):
        new_note = None
        if (new_url is not None):
            new_note = Note(new_url)

        for i in self.links:
            if (i.url == url):
                if (new_note is None):
                    self.links.remove(i)
                else:
                    i.url = new_note.filename
                    i.text = new_note.title
                
        for i in self.backlinks:
            if (i.url == url):
                if (new_note is None):
                    self.backlinks.remove(i)
                else:
                    i.url = new_note.filename
                    i.text = new_note.title
        self.write()
        
    def view(self, stdscr):
        newnote = None
        stdscr.clear()

        command = None
        select = False

        link_note = None
        mark_y = None
        mark_x = None
        search = ""
        select_y = 0
        select_x = 0
        selected = 0
        top = 0

        while (True):
            stdscr.clear()

            status = ""
            selected = self.cursesoutput(stdscr, top=top, selected=selected)
            #status = f"{file_index + 1} of {len(files)}"

            if (status is True and mark_x is not None):
                status = f"{status} SELECTING2"
            elif (select is True):
                status = f"{status} SELECTING1"

            if (status):
                # Make sure a long status doesn't push 
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            if (select is True):
                #c = stdscr.inch(select_y, select_x)
                #stdscr.insch(select_y, select_x, c, curses.A_REVERSE)
                highlight(stdscr, select_y, select_x, mark_y, mark_x)
            stdscr.refresh()
            command = stdscr.getkey()

            if (command == "KEY_DC" or command == ""):
                confirm = getstring(stdscr, "Are you sure you want to delete this link? (y/N):", 1)
                if (confirm == "y"):
                    self.deletelink(selected)
                    self.write()
            elif (command == "KEY_DOWN"):
                if (select is True):
                    if (mark_y is not None):
                        if (mark_y < curses.LINES-2):
                            mark_y += 1
                    else:
                        if (select_y < curses.LINES-2):
                            select_y += 1
                    continue

                selected += 1
                if (selected > self.linkcount()):
                    selected = 1
            elif (command == "KEY_UP"):
                if (select is True):
                    if (mark_y is not None):
                        if (mark_y > 0):
                            mark_y -= 1
                    else:
                        if (select_y > 0):
                            select_y -= 1
                    continue

                selected -= 1
                if (selected < 1):
                    selected = self.linkcount()
                # stdscr.getyx()
                # stdscr.move(y, x)
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
            elif (command == "c"):
                # select text
                if (select is False):
                    # TODO: This is dumb, convert this into some kind of "state" variable
                    #  so I can just cancel everything with a single command.
                    select = True
                    move = False
                    select_y = 0
                    select_x = 0
                    mark_y = None
                    mark_x = None
                else:
                    mark_y = select_y
                    mark_x = select_x
            elif (command == "e"):
                # Edit note
                curses.def_prog_mode()
                subprocess.call([os.environ['EDITOR'], self.filename])
                curses.reset_prog_mode()
                self.reload()
                continue
            elif (command == "f"):
                f = FileBrowser()
                ref = f.browse(stdscr)
                if (ref):
                    self.addreference(ref)
                    self.write()
            elif (command == "l"):
                # Link a note to this note
                if (globalvars.link_note is None):
                    globalvars.link_note = self
                else:
                    self.addnotelink(globalvars.link_note)
                    self.write()
                    globalvars.link_note.addnotebacklink(self)
                    globalvars.link_note.write()
                    globalvars.link_note = None
            elif (command == "p"):
                if (globalvars.copy is not None):
                    self.addreference(globalvars.copy)
                    self.write()
            elif (command == "r"):
                # get new name
                new_title = getstring(stdscr, "New Title: ", 80)
                original_file = self.filename
                self.updatetitle(new_title)
                globalvars.reload = True
                self.reload()
                files = loadnotes()
                for f in files:
                    note = Note(f)
                    note.updatelinks(original_file, self.filename)
            elif (command == 't'):
                new_tags = getstring(stdscr, "Tags: ")
                self.updatetags(new_tags)
            elif (command == "\n"):
                if (select is True):
                    if (mark_x is not None):
                        text = highlight(stdscr, select_y, select_x, mark_y, mark_x)
                        link = Link(self.filename, self.title)
                        globalvars.copy = Reference(link, text)
                        #pyperclip.copy(copy.__str__())
                        select = False
                    else:
                        mark_y = select_y
                        mark_x = select_x
                else:
                    link = self.getlink(selected)
                    if (link is not None and not re.search("^[^ ]+:", link.url)):
                        try:
                            n = Note(link.url)
                        except InvalidNoteException as e:
                            logging.debug(e)
                            logging.debug(f"opening {link.url}")
                            #f=FileBrowser()
                            #f.browse(stdscr, filename=link.url)
                            file = File(link.url)
                            file.view(stdscr)
                        else:
                            # TODO: Just return the note object
                            return n.filename
                    elif (link is not None and re.search("^[^ ]+:", link.url)):
                        subprocess.run(['open', link.url], check=True)
            elif (command == ''):
                if (select is True):
                    if (mark_x is not None):
                        mark_x = None
                        mark_y = None
                    else:
                        select = False
                    continue

                return
            elif (command == "?"):
                stdscr.clear()
                stdscr.addstr("Editing Commands\n\n", curses.A_BOLD)
                stdscr.addstr("e            - open this note in the external editor (set the EDITOR environment variable)\n")
                stdscr.addstr("l            - press once to set this note as the target.  Navigate to another note and press\n")
                stdscr.addstr("               'l' again to add a link to the first note from the second note.\n")
                stdscr.addstr("q            - quit\n")
                stdscr.addstr("r            - rename note\n")
                stdscr.addstr("t            - edit tags\n")
                stdscr.addstr("\n")
                stdscr.addstr("Navigation Commands\n\n", curses.A_BOLD)
                stdscr.addstr("<up>/<down>  - cycle through the links on this note\n")
                stdscr.addstr("<enter>      - follow the selected link\n")
                stdscr.addstr("<left>       - previous note\n")
                stdscr.addstr("<right>      - next note\n")
                stdscr.addstr("<esc>        - return to note list\n")
                stdscr.addstr("?            - this help screen\n")

                stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                stdscr.refresh()
                command = stdscr.getkey()

    def write(self):
        with open(self.filename, "w") as f:
            f.write(self.__str__())
            f.close()

class NoteBrowser():
    def browse(self, stdscr):

        stdscr.clear()

        files = loadnotes()
        note1 = None
        if (args.filename is not None):
            note1 = Note(args.filename)

        command = None

        move = False
        select = False

        copy = None
        globalvars.link_note = None
        mark_y = None
        mark_x = None
        search = ""
        select_y = 0
        select_x = 0
        selected = 0
        top = 0

        while (command != "q"):
            stdscr.clear()

            status = ""
            if (note1 is not None):
                selected = note1.cursesoutput(stdscr, top=top, selected=selected)
                # left, PREV
                notes = loadnotes()
                selected = 0
                top = 0
                try:
                    note_index = notes.index(self.filename)
                except:
                    return

                note_index -= 1

                if (note_index < 0):
                    note_index = len(notes) - 1

                note1 = Note(files[file_index])
                # right, NEXT
                selected = 0
                top = 0
                try:
                    file_index = files.index(note1.filename)
                except:
                    note1 = None
                    continue

                file_index += 1

                if (file_index >= len(files)):
                    file_index = 0
                note1 = Note(files[file_index])

                file_index = 0
                try:
                    file_index = files.index(note1.filename)
                except:
                    note1 = None
                    selected = 0
                    continue
                status = f"{file_index + 1} of {len(files)}"
            else:
                top = gettop(selected, top, len(files)-1)
                for i in range(0,len(files)):
                    if (i < top): continue
                    if (i > (top + curses.LINES - 2 )): continue
                    f = files[i]
                    max_width = curses.COLS - 2
                    if (i == selected):
                        stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f), curses.A_REVERSE)
                    else:
                        stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f))
                status = f"{selected+1} of {len(files)}"

            if (status is True and mark_x is not None):
                status = f"{status} SELECTING2"
            elif (select is True):
                status = f"{status} SELECTING1"

            if (status is not None):
                # Make sure a long status doesn't push 
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            if (select is True):
                #c = stdscr.inch(select_y, select_x)
                #stdscr.insch(select_y, select_x, c, curses.A_REVERSE)
                highlight(stdscr, select_y, select_x, mark_y, mark_x)
            stdscr.refresh()
            command = stdscr.getkey()

            if (self is not None):
                if (command == "KEY_DC" or command == ""):
                    confirm = getstring(stdscr, "Are you sure you want to delete this link? (y/N):", 1)
                    if (confirm == "y"):
                        note1.deletelink(selected)
                        note1.write()
                elif (command == "KEY_DOWN"):
                    if (select is True):
                        if (mark_y is not None):
                            if (mark_y < curses.LINES-2):
                                mark_y += 1
                        else:
                            if (select_y < curses.LINES-2):
                                select_y += 1
                        continue

                    selected += 1
                    if (selected > note1.linkcount()):
                        selected = 1
                elif (command == "KEY_UP"):
                    if (select is True):
                        if (mark_y is not None):
                            if (mark_y > 0):
                                mark_y -= 1
                        else:
                            if (select_y > 0):
                                select_y -= 1
                        continue

                    selected -= 1
                    if (selected < 1):
                        selected = note1.linkcount()
                    # stdscr.getyx()
                    # stdscr.move(y, x)
                    elif (command == "KEY_LEFT"):
                        if (select is True):
                            if (mark_x is not None):
                                if (mark_x > 0):
                                    mark_x -= 1
                            else:
                                if (select_x > 0):
                                    select_x -= 1
                            continue
                        selected = 0
                        top = 0
                        try:
                            file_index = files.index(note1.filename)
                        except:
                            note1 = None
                            continue

                        file_index -= 1

                        if (file_index < 0):
                            file_index = len(files) - 1

                        note1 = Note(files[file_index])
                    elif (command == "KEY_RIGHT"):
                        if (select is True):
                            if (mark_x is not None):
                                if (mark_x < curses.COLS-2):
                                    mark_x += 1
                            else:
                                if (select_x < curses.COLS-2):
                                    select_x += 1
                            continue

                        selected = 0
                        top = 0
                        try:
                            file_index = files.index(note1.filename)
                        except:
                            note1 = None
                            continue

                        file_index += 1

                        if (file_index >= len(files)):
                            file_index = 0
                        note1 = Note(files[file_index])
                    elif (command == "c"):
                        # select text
                        if (select is False):
                            # TODO: This is dumb, convert this into some kind of "state" variable
                            #  so I can just cancel everything with a single command.
                            select = True
                            move = False
                            select_y = 0
                            select_x = 0
                            mark_y = None
                            mark_x = None
                        else:
                            mark_y = select_y
                            mark_x = select_x
                    elif (command == "e"):
                        # Edit note
                        curses.def_prog_mode()
                        subprocess.call([os.environ['EDITOR'], self.filename])
                        curses.reset_prog_mode()
                        self.reload()
                    elif (command == "f"):
                        f = FileBrowser()
                        ref = f.browse(stdscr)
                        if (ref):
                            self.addreference(ref)
                            self.write()
                    elif (command == "l"):
                        # Link a note to this note
                        if (globalvars.link_note is None):
                            globalvars.link_note = self
                        else:
                            self.addnotelink(globalvars.link_note)
                            self.write()
                            globalvars.link_note.addnotebacklink(self)
                            globalvars.link_note.write()
                            globalvars.link_note = None
                    elif (command == "p"):
                        if (globalvars.copy is not None):
                            self.addreference(globalvars.copy)
                            self.write()
                    elif (command == "r"):
                        # get new name
                        new_title = getstring(stdscr, "New Title: ", 80)
                        original_file = self.filename
                        self.updatetitle(new_title)
                        files = loadnotes()
                        for f in files:
                            note = Note(f)
                            note.updatelinks(original_file, self.filename)
                    elif (command == 't'):
                        new_tags = getstring(stdscr, "Tags: ")
                        self.updatetags(new_tags)
                    elif (command == "\n"):
                        if (select is True):
                            if (mark_x is not None):
                                text = highlight(stdscr, select_y, select_x, mark_y, mark_x)
                                link = Link(self.filename, self.title)
                                copy = Reference(link, text)
                                pyperclip.copy(copy.__str__())
                                select = False
                            else:
                                mark_y = select_y
                                mark_x = select_x
                        else:
                            link = self.getlink(selected)
                            # TODO: Have this detect files, rather than notes, and call FileBrowser with a filename to
                            #   bypass the selection screen and open the file directly.
                            if (link is not None and not re.search("^[^ ]+:", link.url)):
                                try:
                                    n = Note(link.url)
                                except InvalidNoteException as e:
                                    logging.debug(e)
                                    f=FileBrowser()
                                    logging.debug(f"opening {link.url}")
                                    f.browse(stdscr, filename=link.url)
                                else:
                                    return n
                            elif (link is not None and re.search("^[^ ]+:", link.url)):
                                subprocess.run(['open', link.url], check=True)
                    elif (command == ''):
                        if (select is True):
                            if (mark_x is not None):
                                mark_x = None
                                mark_y = None
                            else:
                                select = False
                            continue
                        else:
                            return

                    elif (command == "?"):
                        stdscr.clear()
                        stdscr.addstr("Editing Commands\n\n", curses.A_BOLD)
                        stdscr.addstr("e            - open this note in the external editor (set the EDITOR environment variable)\n")
                        stdscr.addstr("l            - press once to set this note as the target.  Navigate to another note and press\n")
                        stdscr.addstr("               'l' again to add a link to the first note from the second note.\n")
                        stdscr.addstr("q            - quit\n")
                        stdscr.addstr("r            - rename note\n")
                        stdscr.addstr("t            - edit tags\n")
                        stdscr.addstr("\n")
                        stdscr.addstr("Navigation Commands\n\n", curses.A_BOLD)
                        stdscr.addstr("<up>/<down>  - cycle through the links on this note\n")
                        stdscr.addstr("<enter>      - follow the selected link\n")
                        stdscr.addstr("<left>       - previous note\n")
                        stdscr.addstr("<right>      - next note\n")
                        stdscr.addstr("<esc>        - return to note list\n")
                        stdscr.addstr("?            - this help screen\n")

                        stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                        stdscr.refresh()
                        command = stdscr.getkey()
                else:
                    if (command == "KEY_DOWN" or command == "KEY_RIGHT"):
                        original_selected = selected
                        selected += 1
                        if (selected > len(files)-1):
                            selected = 0
                        if (move is True):
                            files = swapnotes(files, original_selected, selected)
                    elif (command == "KEY_UP" or command == "KEY_LEFT"):
                        original_selected = selected
                        selected -= 1
                        if (selected < 0):
                            selected = len(files)-1
                        if (move is True):
                            files = swapnotes(files, original_selected,selected)
                    elif (command == "KEY_END" or command == "G"):
                        move = False
                        selected = len(files) - 1
                    elif (command == "KEY_HOME"):
                        move = False
                        selected = 0
                    elif (command == "KEY_NPAGE" or command == ""):
                        move = False
                        selected += curses.LINES - 2  
                        if (selected > len(files)-1):
                            selected = len(files)-1
                    elif (command == "KEY_PPAGE" or command == ""):
                        move = False
                        selected -= curses.LINES - 2
                        if (selected < 0):
                            selected = 0
                    elif (command == "a"):
                        move = False
                        new_title = getstring(stdscr, "New Note: ", 80)
                        if (new_title == ""):
                            continue
                        # based on the selected note, figure out how many notes we have to adjust to make a hole
                        if (len(files) == 0):
                            next_order = 1
                        elif (selected < len(files)-1):
                            note = Note(files[selected+1])
                            next_order = note.order + 1
                            for f in files[selected:]:
                                n = Note(f)
                                if (n.order > next_order):
                                    break
                                next_order = n.order + 1

                            # now that we have the first free spot, move everything up one
                            tmp_files = files[selected+1:]
                            tmp_files.reverse()
                            for f in tmp_files:
                                n = Note(f)
                                if (n.order < next_order):
                                    original_file = n.filename
                                    n.updateorder(next_order)
                                    files = loadnotes()
                                    for f2 in files:
                                        n2 = Note(f2)
                                        n2.updatelinks(original_file, n.filename)
                                    next_order -= 1
                        else:
                            note = Note(files[-1])
                            next_order = note.order + 1
                        today = datetime.datetime.now()
                        date = today.strftime("%Y-%m-%d %H-%M")
                        filename = "{:04d} - {} - {}.md".format(next_order, date, new_title)
                        new_note = Note(filename)
                        new_note.write()
                        files = loadnotes()
                        self = new_note
                    elif (command == "KEY_DC" or command == "d"):
                        move = False
                        note = Note(files[selected])
                        original_file = note.filename
                        confirm = getstring(stdscr, "Are you sure you want to delete this note? (y/N):", 1)
                        if (confirm == "y"):
                            note.delete()
                            files = loadnotes()
                            for f in files:
                                note = Note(f)
                                note.updatelinks(original_file, None)
                    elif (command == "f"):
                        f = FileBrowser()
                        copy = f.browse(stdscr)
                    elif (command == "m"):
                        if (move is True):
                            move = False
                        else:
                            move = True
                    elif (command == "/"):
                        original_selected = selected
                        move = False
                        new_search = getstring(stdscr, "Search for: ")
                        if (new_search != ""):
                            search = new_search
                        if (search == ""):
                            continue
                        search = search.lower()
                        for f in files[selected+1:]:
                            n = Note(f)
                            if (n.search(search)):
                                selected = files.index(f)
                                break

                        if (selected != original_selected):
                            continue

                        for f in files[:selected]:
                            n = Note(f)
                            if (n.search(search)):
                                selected = files.index(f)
                                break
                    elif (command == "\n"):
                        move = False
                        self = Note(files[selected])
                        selected = 0
                        top = 0
                    elif (command == ""):
                        move = False
                        link_note = None
                    elif (command == "?"):
                        stdscr.clear()
                        stdscr.addstr("Editing Commands\n", curses.A_BOLD)
                        stdscr.addstr("a                - add a new note after the selected note\n")
                        stdscr.addstr("d or <del>       - delete the currently selected note\n")
                        stdscr.addstr("m                - change to 'move' mode.  <up>/<down> will move the selected note. <esc> to cancel\n")
                        stdscr.addstr("q                - quit\n")
                        stdscr.addstr("/                - enter a string to search for\n")
                        stdscr.addstr("?                - this help screen\n")

                        stdscr.addstr("\n")
                        stdscr.addstr("Navigation Commands\n", curses.A_BOLD)
                        stdscr.addstr("<home>           - first note\n")
                        stdscr.addstr("<up>             - previous/next note\n")
                        stdscr.addstr("<pgup> or ^u     - move the curser up one screen\n")
                        stdscr.addstr("<pgdown> or ^d   - move the curser up one screen\n")
                        stdscr.addstr("<down>           - next note\n")
                        stdscr.addstr("<end> or G       - last note\n")
                        stdscr.addstr("<enter>          - open the selected note\n")
                        stdscr.addstr("<esc>            - cancel 'move' mode, link mode")

                        stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                        stdscr.refresh()
                        command = stdscr.getkey()

# Get the next available open slot in a given list of files after the 
#   given position.
def gethole(files, position=0):
    if (len(files) == 0):
        next_order = 1
    elif (position < len(files)-1):
        next_order = note.order + 1
        note = Note(files[position])
        for f in files[position:]:
            n = zlinklib.Note(f)
            if (n.order > next_order):
                break
            next_order = n.order + 1
    else:
         note = zlinklib.Note(files[-1])
         next_order = note.order + 1
    return next_order

# Return the item at the 'top' of the screen, based on what is currently selected.
def gettop(selected, current_top, maxlength, center=False):
    top = current_top
    if (selected == 0):
        top = 0
    elif (selected < current_top):
        top = selected
    elif (selected > (current_top + curses.LINES - 2)):
        top = selected - curses.LINES + 2
    if (top < 0): top = 0
    if (top > (maxlength - curses.LINES + 2)):
        top = maxlength - curses.LINES + 2
    return top

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

# Read the list of notes from the disk.
def loadnotes():
    files = [f for f in os.listdir(".") if(os.path.isfile(os.path.join(".", f)) and re.search("^\d+ - .+\.md$",f))]
    files.sort()
    return files

# Request a string from the user.
def getstring(stdscr, prompt_string, maxlength=40):
    curses.echo() 
    stdscr.addstr(curses.LINES-1, 0, prompt_string)
    stdscr.refresh()
    input = stdscr.getstr(curses.LINES-1, len(prompt_string), maxlength).decode(encoding='utf-8')
    curses.noecho()
    return input

def swapnotes(files, original_pos, new_pos):
    n1 = zlinklib.Note(files[original_pos])
    n1_file = n1.filename

    n2 = zlinklib.Note(files[new_pos])
    n2_file = n2.filename
    new_order = n1.order
    if (n2.order == n1.order and new_pos < original_pos):
        new_order = gethole(files, new_pos)
    n1.updateorder(n2.order)
    n2.updateorder(new_order)
    files = zlinklib.loadnotes()
    for f in files:
        note = zlinklib.Note(f)
        note.updatelinks(n1_file, n1.filename)
        note.updatelinks(n2_file, n2.filename)
    return files

