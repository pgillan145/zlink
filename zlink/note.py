import argparse
import curses
import datetime
import minorimpact
#import logging
import os
import os.path
import re
import subprocess
import sys

import zlink
import zlink.globalvars

from zlink.file import FileBrowser, File

class InvalidNoteException(Exception):
    def __init__(self, message):
        super().__init__(message)

class Link():
    def __init__(self, url, text=None):
        self.url = url
        if (text is None):
            if (re.search("^\/", url)):
                text = os.path.basename(url)
            else:
                text = url
        self.text = text

    def __str__(self):
        return f"[{self.text}]({self.url})"

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
        output = self.output()

        header = f"{self.title}"
        stdscr.addstr( f"{header}\n", curses.A_BOLD)
                
        for i in range(0, len(output)):
            s = output[i]
 
            current = 0
            m = re.search("^__(\d+)__", s)
            if (m):
                current = int(m.group(1))
                if (current == 1 and selected == 0):
                    selected = 1
                s = re.sub(f"__{current}__", "", s)
                if (current == selected):
                    s = f"__REVERSE__{s}"
                    if (len(output) > curses.LINES + top - 3):
                        top = len(output) - curses.LINES + 7
                output[i] = s

        for i in range(0, len(output)):
            s = output[i]
 
            current = 0
            attr = 0
            if (re.match("^__REVERSE__", s)):
                s = s.replace("__REVERSE__", "")
                attr = curses.A_REVERSE
            elif (re.match("^__BOLD__", s)):
                s = s.replace("__BOLD__", "")
                attr = curses.A_BOLD

            if (i < top): continue
            if (i >= top + curses.LINES - 3): continue

            s = s[:curses.COLS-1]
            stdscr.addstr(f"{s}\n", attr)

        return selected

    def delete(self):
        os.remove(self.filename)

    def deletelink(self, selected):
        link = self.getlink(selected)
        if (link is None):
            return

        try:
            self.links.remove(link)
        except ValueError:
            pass

        try:
            self.backlinks.remove(link)
        except ValueError:
            pass

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

    def output(self):
        output = []
        current = 0

        if (len(self.tags) > 0):
            output.append(f"tags: #" + ",#".join(self.tags) + "")
            output.append("")

        if (len(self.tags) > 0 or self.id is not None): 
            output.append("")
        for i in self.default:
            if (i):
                foo = []
                foo = minorimpact.splitstringlen(i,curses.COLS - 2)
                for f in foo:
                    output.append(f"{f}")
        output.append("")

        output.append("### Links")
        for i in self.links:
            current += 1
            output.append(f"__{current}__{i.text}")
        output.append("")

        output.append("### Backlinks")
        for i in self.backlinks:
            current += 1
            output.append(f"__{current}__{i.text}")
        output.append("")

        output.append("### References")
        for i in self.references:
            current += 1
            output.append(f"__{current}__{i.link}")

            if (i.text is not None):
                foo = minorimpact.splitstringlen(i.text,curses.COLS - 2)
                for f in foo:
                    output.append(f"> {f}")
            output.append("")
        return output

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
        filebrowser = FileBrowser()

        while (True):
            stdscr.clear()

            status = ""
            # TODO: Figure out if we really need to have selected passed back to us.  It had
            #   something to do with having it set to zero (no link selected), and then having the 
            #   function reset it to '1' so a link is always accepted, but that might not be
            #   needed now that browsing and viewing aren't sharing a loop.
            selected = self.cursesoutput(stdscr, top=top, selected=selected)
            #status = f"{file_index + 1} of {len(files)}"


            if (status is True and mark_x is not None):
                status = f"{status} SELECTING END"
            elif (select is True):
                status = f"{status} SELECTING START"

            if (status):
                # Make sure a long status doesn't push 
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            if (select is True):
                #c = stdscr.inch(select_y, select_x)
                #stdscr.insch(select_y, select_x, c, curses.A_REVERSE)
                zlink.zlink.highlight(stdscr, select_y, select_x, mark_y, mark_x)
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
                filebrowser.browse(stdscr)
            elif (command == "l"):
                # Link a note to this note
                if (zlink.globalvars.link_note is None):
                    zlink.globalvars.link_note = self
                else:
                    self.addnotelink(zlink.globalvars.link_note)
                    self.write()
                    zlink.globalvars.link_note.addnotebacklink(self)
                    zlink.globalvars.link_note.write()
                    zlink.globalvars.link_note = None
            elif (command == "p"):
                if (zlink.globalvars.link_filename and zlink.globalvars.link_text):
                    link = Link(zlink.globalvars.link_filename)
                    ref = Reference(link, zlink.globalvars.link_text)
                    self.addreference(ref)
                    self.write()
                elif(zlink.globalvars.copy):
                    self.addreference(zlink.globalvars.copy)
                    self.write()
            elif (command == "q"):
                sys.exit()
            elif (command == "r"):
                # get new name
                new_title = getstring(stdscr, "New Title: ", 80)
                original_file = self.filename
                self.updatetitle(new_title)
                zlink.globalvars.reload = True
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
                        text = zlink.zlink.highlight(stdscr, select_y, select_x, mark_y, mark_x)
                        link = Link(self.filename, self.title)
                        zlink.globalvars.copy = Reference(link, text)
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
                            # TODO: hitting the arrow keys when viewing a linked file brings us back here; not
                            #   sure what the most intuitive action is.  Go to the next file? or go the next note?
                            #   Going to the next file means making sure FileBrowser sets the correct 'cwd' variable so
                            #   it knows what the files are, and going to the next note means reproducing the right/left code.
                            f = File(link.url)
                            f.view(stdscr)
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
                # TODO: If the window is smaller than the help text, the thing crashes.
                stdscr.clear()
                stdscr.addstr("Editing Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" c              - enter selection mode to copy text to save the clipboard as a reference\n")
                stdscr.addstr(" e              - open this note in the external editor (set the EDITOR environment variable)\n")
                stdscr.addstr(" l              - press once to set this note as the target.  Navigate to another note and press\n")
                stdscr.addstr("                  'l' again to add a link to the first note from the second note.\n")
                stdscr.addstr(" p              - paste a reference from the clipboard to the current note\n")
                stdscr.addstr(" q              - quit\n")
                stdscr.addstr(" r              - rename note\n")
                stdscr.addstr(" t              - edit tags\n")
                stdscr.addstr(" ?              - this help screen\n")
                stdscr.addstr("\n")
                stdscr.addstr("Selection Mode Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" Use the arrow keys to move the cursor to the start of the text you want to select.  Press\n")
                stdscr.addstr(" <enter> to start highlighting; use the arrow keys to move the cursor to the end of the text\n")
                stdscr.addstr(" you want to select.  Press <enter> again to copy the text to the clipboard, along with a link\n")
                stdscr.addstr(" to this note\n")
                stdscr.addstr("\n")
                stdscr.addstr("Navigation Commands\n\n", curses.A_BOLD)
                stdscr.addstr(" f              - open the file browser\n")
                stdscr.addstr(" <up>/<down>    - cycle through the links on this note\n")
                stdscr.addstr(" <enter>        - follow the selected link\n")
                stdscr.addstr(" <left>         - previous note\n")
                stdscr.addstr(" <right>        - next note\n")
                stdscr.addstr(" <esc>          - return to note list\n")

                stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                stdscr.refresh()
                command = stdscr.getkey()

    def write(self):
        with open(self.filename, "w") as f:
            f.write(self.__str__())
            f.close()

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

class NoteBrowser():
    def browse(self, stdscr, filename=None):

        stdscr.clear()

        files = loadnotes()
        note1 = None
        if (filename is not None):
            note1 = Note(filename)

        command = None

        move = False

        search = ""
        selected = 0
        top = 0
        filebrowser = FileBrowser()

        while (command != "q"):
            stdscr.clear()

            status = ""


            if (note1 is not None):
                newnote = note1.view(stdscr)
                if (zlink.globalvars.reload):
                    files = loadnotes()
                    selected = 0
                    try:
                        selected = files.index(note1.filename)
                    except:
                        pass
                    zlink.globalvars.reload = False
                #selected = note1.cursesoutput(stdscr, top=top, selected=selected)
                if (newnote):
                    if (newnote == "PREV"):
                        selected -= 1
                        if (selected < 0):
                            selected = len(files) - 1
                        note1 = Note(files[selected])
                    elif (newnote == "NEXT"):
                        selected += 1
                        if (selected >= len(files)):
                            selected = 0
                        note1 = Note(files[selected])
                    else:

                        try:
                            note1 = Note(newnote)
                            selected = files.index(note1.filename)
                        except Exception as e:
                            selected = 0
                            note1 = None
                    continue
                note1 = None
                continue
                #status = f"{file_index + 1} of {len(files)}"
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

            if (move):
                status = f"{status} MOVING"

            if (status):
                # Make sure a long status doesn't push 
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            stdscr.refresh()
            command = stdscr.getkey()

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
                # TODO: Does pgup/pgdown/home/end have to kill the "move" command? or does
                #   it make sense for me to be able to move a note a vast difference, rather than
                #   forcing it to be one at a time.  
                #   Pro: it's faster to move a note a long distance
                #   Con: if the user accidentally moves it a long distance, it's going to be hard to get it
                #     back into the correct place.  If there are a ton of notes, shuffling them all could
                #     take a long time.  Probably need to make sure traversing all the files scales before
                #     implementing this.
                move = False
                selected = len(files) - 1
            elif (command == "KEY_HOME"):
                move = False
                selected = 0
            elif (command == "KEY_NPAGE" or command == ""):
                move = False
                selected += curses.LINES - 2  
                if (selected > len(files) - 1):
                    selected = len(files) - 1
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
                note1 = new_note
                selected = files.index(note1.filename)
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
                #f = FileBrowser()
                filebrowser.browse(stdscr)
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
                note1 = Note(files[selected])
                #selected = 0
                #top = 0
            elif (command == ""):
                move = False
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
                stdscr.addstr("f                - open the file browser\n")
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
            n = Note(f)
            if (n.order > next_order):
                break
            next_order = n.order + 1
    else:
         note = Note(files[-1])
         next_order = note.order + 1
    return next_order

# Request a string from the user.
def getstring(stdscr, prompt_string, maxlength=40):
    curses.echo()
    stdscr.addstr(curses.LINES-1, 0, prompt_string)
    stdscr.refresh()
    input = stdscr.getstr(curses.LINES-1, len(prompt_string), maxlength).decode(encoding='utf-8')
    curses.noecho()
    return input

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

# Read the list of notes from the disk.
def loadnotes():
    files = [f for f in os.listdir(".") if(os.path.isfile(os.path.join(".", f)) and re.search("^\d+ - .+\.md$",f))]
    files.sort()
    return files

def swapnotes(files, original_pos, new_pos):
    n1 = Note(files[original_pos])
    n1_file = n1.filename

    n2 = Note(files[new_pos])
    n2_file = n2.filename
    new_order = n1.order
    if (n2.order == n1.order and new_pos < original_pos):
        new_order = gethole(files, new_pos)
    n1.updateorder(n2.order)
    n2.updateorder(new_order)
    files = loadnotes()
    for f in files:
        note = Note(f)
        note.updatelinks(n1_file, n1.filename)
        note.updatelinks(n2_file, n2.filename)
    return files
