import argparse
import curses
import datetime
import minorimpact
import logging
import os
import os.path
import re
import subprocess
import sys

from minorimpact.curses import getstring, highlight

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

        self.backlinks = self.parselinks("backlinks")
        self.default = self.parsed['default']
        self.links = self.parselinks()
        self.references = self.parsereferences()

    def __str__(self):
        str = ""
        #if (self.id is not None):
        #    str = str + f"[_metadata_:id]:- {self.id}\n"
        if (len(self.tags) > 0):
            str = str + f'[_metadata_:tags]:- "' + ','.join(self.tags) + '"\n'

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
            m = re.search('^\[_metadata_:(.+)\]:- +"?([^"]+)"?$', l)
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
        # TODO: Make it so any string that starts with '#' will also match tags, even though
        #       they don't have a 'hashtag' in their raw form.
        search_string = search_string.lower()
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
        return False

    # Change the order value of the current note.
    def updateorder(self, new_order):
        original_file = self.filename
        self.order = new_order
        self.filename = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        logging.debug(f"Moved {original_file} to {self.filename}")
        os.rename(original_file, self.filename)
        files = loadnotes()
        for f in files:
            n = Note(f)
            n.updatelinks(original_file, self.filename)

    def updatetags(self, new_tags):
        tags = new_tags.split(",")
        for i,t in enumerate(tags):
            tags[i] = t.strip()
        self.tags = tags
        self.write()

    def updatetitle(self, new_title):
        # TODO: Should this just use the write() method?  Does that method know how handle changes that would result in an 
        #       altered filename?  If it doesn't, it really, really should.
        original_file = self.filename
        self.title = new_title
        self.filename = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        os.rename(original_file, self.filename)

    # Change any links for this note from 'url' to 'new_url'.
    def updatelinks(self, url, new_url):
        # TODO: Make this work with actual link objects, as opposed to just passing around ghetto urls.
        new_note = None
        if (new_url is not None):
            new_note = Note(new_url)

        for l in self.links:
            if (l.url == url):
                if (new_note is None):
                    self.links.remove(l)
                else:
                    logging.debug('changing link from %s:"%s" to %s:"%s"', l.url, l.text, new_note.filename, new_note.title) 
                    l.url = new_note.filename
                    l.text = new_note.title
                
        for b in self.backlinks:
            if (b.url == url):
                if (new_note is None):
                    self.backlinks.remove(b)
                else:
                    logging.debug('changing backlink from %s:"%s" to %s:"%s"', b.url, b.text, new_note.filename, new_note.title) 
                    b.url = new_note.filename
                    b.text = new_note.title

        for r in self.references:
            if (r.link == url):
                if (new_url is None):
                    self.references.remove(r);
                else:
                    r.link = new_url

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
                filebrowser.browse(stdscr)
            elif (command == 'l'):
                if (zlink.globalvars.link_note is None):
                    # store this note for linking later
                    zlink.globalvars.link_note = self
                else:
                    # link the previous note to the current note
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
                        text = highlight(stdscr, select_y, select_x, mark_y, mark_x)
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
                stdscr.addstr("                  'l' again to add a link to the target note to the current note\n")
                stdscr.addstr(" p              - paste a reference from the clipboard to the current note\n")
                stdscr.addstr(" q              - quit\n")
                stdscr.addstr(" r              - rename note\n")
                stdscr.addstr(" t              - edit tags\n")
                stdscr.addstr(" <del> or       - delete the currently selected link or backlink\n")
                stdscr.addstr(" <backspace>\n")
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
        # TODO: Make this compare the filename in the object with the filename that would be generated from the object
        #       data, and if they don't match, you know... fucking fix it.  This shouldn't be happening in updateTitle() or 
        #       updateOrder().
        # NOTE: I think i may have looked into this before, but see if there's a way for an object to detect changes to itself and 
        #       perform actions if something is different.  That could be a thing, right?
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
                    max_width = curses.COLS - 6
                    menu_item = "{:" + str(max_width) + "." + str(max_width) + "s}\n"
                    note = Note(f)
                    
                    menu_item = menu_item.format(f)
                    if (i == selected):
                        stdscr.addstr(menu_item, curses.A_REVERSE)
                    else:
                        stdscr.addstr(menu_item)
                status = f"{selected+1} of {len(files)}"

            if (move):
                status = f"{status} MOVING"
            if (zlink.globalvars.link_note is not None):
                status = f"{status} LINKING"
            if (zlink.globalvars.filter != ""):
                status = f"{status} FILTERED:'{zlink.globalvars.filter}'"

            if (status):
                # Make sure a long status doesn't push 
                status = minorimpact.splitstringlen(status, curses.COLS-2)[0]
                stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)

            stdscr.refresh()
            command = stdscr.getkey()

            if (command == "KEY_UP"):
                original_selected = selected
                selected -= 1
                if (selected < 0):
                    selected = len(files)-1
                if (move is True):
                    files = swapnotes(files, original_selected,selected)
            elif (command == "KEY_DOWN"):
                original_selected = selected
                selected += 1
                if (selected > len(files)-1):
                    selected = 0
                if (move is True):
                    files = swapnotes(files, original_selected, selected)
            #elif (command == "KEY_LEFT"):
            #    note = Note(files[selected])
            #elif (command == "KEY_RIGHT"):
            #    note = Note(files[selected])
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
            elif (command == 'a' or command == 'o'):
                if (zlink.globalvars.filter != ""):
                    continue
                move = False
                new_title = getstring(stdscr, "New Note: ", 80)
                if (new_title == ""):
                    continue
                new_order = makehole(files, selected+1)
                new_note = newNote(new_order, new_title)
                files = loadnotes()
                note1 = new_note
                selected = files.index(note1.filename)
            elif (command == 'A' or command == 'O'):
                if (zlink.globalvars.filter != ""):
                    continue
                move = False
                new_title = getstring(stdscr, "New Note: ", 80)
                if (new_title == ""):
                    continue
                new_order = makehole(files, selected-1)
                new_note = newNote(new_order, new_title)
                files = loadnotes()
                note1 = new_note
                selected = files.index(note1.filename)
            elif (command == "KEY_DC" or command == 'd' or command == '^?'):
                if (zlink.globalvars.filter != ""):
                    continue
                if (move is True or zlink.globalvars.link_note is not None):
                    move = False
                    zlink.globalvars.link_note = None
                    continue
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
            elif (command == 'F'):
                original_selected = selected
                note = Note(files[selected])
                new_filter = getstring(stdscr, "filter for: ").lower()
                if (new_filter != ""):
                    zlink.globalvars.filter = new_filter
                if (zlink.globalvars.filter == ""):
                    continue

                move = False
                zlink.globalvars.link_note = None
                files = loadnotes()
                if (len(files) == 0):
                    zlink.globalvars.filter = ""
                    files = loadnotes()
                    selected = files.index(note.filename)
                    status = f"{status} NOT FOUND"
                    continue
                try:
                    selected = files.index(note.filename)
                except ValueError:
                    selected = 0

            elif (command == "l"):
                move = False
                note = Note(files[selected])
                if (zlink.globalvars.link_note is None):
                    # store this note for linking later
                    zlink.globalvars.link_note = note
                elif (note is not None):
                    # link the previous note to the current note
                    note.addnotelink(zlink.globalvars.link_note)
                    note.write()
                    zlink.globalvars.link_note.addnotebacklink(note)
                    zlink.globalvars.link_note.write()
                    zlink.globalvars.link_note = None
            elif (command == 'm'):
                # TODO: moving a note down from the last position to reposition it back a the top ends up swapping the first and last item...
                #       I think that's wrong, but it's not immediately clear what the desired behavior would be.  Would it just become the new first item
                #       and force everything else to move down?  Or would it become the *second* item, because it would still technically be swapping
                #       with the item below it, and we want to the current first item to stay first?  It seems like the more intuitive method would be to
                #       treat the first and last items as connected, but also anchored to their respective positions in the list.  So moving the last item
                #       'down' would move it to the number 2 slot, and moving the first item 'up' would move it to the max-1 spot.
                if(zlink.globalvars.filter != ""):
                    continue
                if (move is True):
                    move = False
                else:
                    move = True
                    zlink.globalvars.link_note = None
            elif (command == '/'):
                original_selected = selected
                #move = False
                #zlink.globalvars.link_note = None
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
                if (move is True or zlink.globalvars.link_note is not None):
                    # clear any 'special' modes.
                    move = False
                    note = Note(files[selected])
                    if (note is not None):
                        if (zlink.globalvars.link_note is not None):
                            # link the previous note to the current note
                            note.addnotelink(zlink.globalvars.link_note)
                            note.write()
                            zlink.globalvars.link_note.addnotebacklink(note)
                            zlink.globalvars.link_note.write()
                            zlink.globalvars.link_note = None
                    continue
                    
                note1 = Note(files[selected])
                #selected = 0
                #top = 0
            elif (command == ''):
                # clear any 'special' modes.
                if (move == True or zlink.globalvars.link_note != None):
                    move = False
                    zlink.globalvars.link_note = None
                elif (zlink.globalvars.filter != ""):
                    zlink.globalvars.filter = ""
                    f = files[selected]
                    files = loadnotes()
                    try:
                        selected = files.index(f)
                    except ValueError:
                        selected = 0
            elif (command == "?"):
                stdscr.clear()
                stdscr.addstr("Editing Commands\n", curses.A_BOLD)
                stdscr.addstr("A or O           - add a new note before the selected note.*\n")
                stdscr.addstr("a or o           - add a new note after the selected note.*\n")
                stdscr.addstr("d or <del>       - delete the currently selected note.*\n")
                stdscr.addstr("l                - will set the current note to the target and activate 'link' mode.  Navigating to any other\n")
                stdscr.addstr("                   note and pressing 'l' (or <enter>) again will link the current note to the target note.\n")
                stdscr.addstr("m                - change to 'move' mode.  <up>/<down> will move the selected note. <esc> to cancel.*\n")
                stdscr.addstr("q                - quit\n")
                stdscr.addstr("?                - this help screen\n")

                stdscr.addstr("\n")
                stdscr.addstr("Navigation Commands\n", curses.A_BOLD)
                stdscr.addstr("F                - create a filter that limits visible notes to only those that match the entered string. <esc>\n")
                stdscr.addstr("                   to cancel.\n")
                stdscr.addstr("/                - enter a string and press <enter> to jump to the next matching record.  Uses the same \n")
                stdscr.addstr("                   syntax as filter.\n")
                stdscr.addstr("f                - open the file browser\n")
                stdscr.addstr("<home>           - first note\n")
                stdscr.addstr("<up>             - previous/next note\n")
                stdscr.addstr("<pgup> or ^u     - move the curser up one screen\n")
                stdscr.addstr("<pgdown> or ^d   - move the curser up one screen\n")
                stdscr.addstr("<down>           - next note\n")
                stdscr.addstr("<end> or G       - last note\n")
                stdscr.addstr("<enter>          - open the selected note (or turn off 'move' or 'link'  mode)\n")
                stdscr.addstr("<esc>            - cancel 'move' mode, 'link' mode, clear the current filter")
                stdscr.addstr("\n")
                stdscr.addstr("\n")
                stdscr.addstr("* these commands do NOT work while a filter is engaged\n")
                # NOTE: the problem is that all of these commands basically just walk through the list and do their things
                #       based on what they find.  If that list is incomplete, a lot of things (like pruning links to deleted notes
                #       or shuffling all of the existing notes to make room for a new one) won't happen for any of the filtered 
                #       filtered results.  I need to make the global list some kind of dynamic object (rather than a simple array)
                #       or add a flag to "loadnotes()" that can tell it to ignore global filter when it runs, and these commands can
                #       all work on a local copy.  Or I can clear the filter, load the results, process them, and then put the filter
                #       back... it's not hard, I'm just not going to do it now.

                stdscr.addstr(curses.LINES-1,0,"Press any key to continue", curses.A_BOLD)
                stdscr.refresh()
                command = stdscr.getkey()

# Get the next available open slot in a given list of files after the
#   given position.
def gethole(files, position=0):
    if (len(files) == 0):
        next_order = 1
    elif (position < len(files)-1):
        note = Note(files[position])
        next_order = note.order + 1
        for f in files[position:]:
            n = Note(f)
            if (n.order > next_order):
                break
            next_order = n.order + 1
    else:
         note = Note(files[-1])
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

# Read the list of notes from the disk.
def loadnotes():
    files = []
    for f in os.listdir("."):
        if (os.path.isfile(os.path.join(".", f)) and re.search("^\d+ - .+\.md$",f)):
            if (zlink.globalvars.filter != ""):
                note = Note(f)
                logging.debug("filtering for %s", zlink.globalvars.filter)
                if (note.search(zlink.globalvars.filter) == False):
                    continue
                logging.debug("  found")
            files.append(f)
    #files = [f for f in os.listdir(".") if(os.path.isfile(os.path.join(".", f)) and re.search("^\d+ - .+\.md$",f))]
    files.sort()
    return files

def makehole(files, position):
    files = loadnotes()
    note = Note(files[position])
    hole = 1
    if (position < 0):
        position = 0
    else:
        if (position > len(files)):
            position = len(files)
        previous_note = Note(files[position-1])
        hole = previous_note.order+1

    last_order = hole
    logging.debug(f"making a hole at {hole}({position})")
    for i in range(position,len(files)):
        logging.debug(f"evaluating postion {i}")
        n = None
        try:
            n = Note(files[i])
        except:
            raise Exception(f"Can't open '{files[i]}'")

        logging.debug(f"  {n.order}:{n.filename}")
        if (n.order <= last_order):
            original_file = n.filename
            n.updateorder(last_order + 1)
            #files[i] = n.filename
            last_order = last_order + 1

    files = loadnotes()
    return hole

def swapnotes(files, original_pos, new_pos):
    n1 = Note(files[original_pos])
    n1_order = n1.order
    n2 = Note(files[new_pos])
    n2_order = n2.order
    if (n2_order == n1_order):
        if (new_pos < original_pos):
            n2.updateorder(makehole(files, original_pos))
        elif (new_pos > original_pos):
            n1.updateorder(makehole(files, new_pos))
    else:
        n1.updateorder(n2_order)
        n2.updateorder(n1_order)
    files = loadnotes()
    return files

def newNote(order, title):
    today = datetime.datetime.now()
    date = today.strftime("%Y-%m-%d %H-%M")
    filename = "{:04d} - {} - {}.md".format(order, date, title)
    new_note = Note(filename)
    new_note.write()
    return new_note

