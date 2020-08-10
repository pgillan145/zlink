#!/usr/bin/env python3

import argparse
import curses
import datetime
import minorimpact
import os
import os.path
import re
import subprocess
import sys

# I like 'vi', so that's the default editor.
if ('EDITOR' not in os.environ):
    os.environ.setdefault('EDITOR', 'vi')

# Hitting escape bungs everything up for a second; this reduces the delay.
os.environ.setdefault('ESCDELAY', '25')

#######
# CLASSES
#######

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
    def __init__(self, file):
        self.file = file
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
        l = Link(note.file, note.title)
        self.addbacklink(l)

    def addnotelink(self, note):
        l = Link(note.file, note.title)
        self.addlink(l)

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
                foo = minorimpact.splitstringlen(i.text,curses.COLS - 4)
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
        os.remove(self.file)

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

    # Return a particular link
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

    def linkcount(self):
        count = 0
        count += len(self.links)
        count += len(self.backlinks)
        count += len(self.references)
        return count

    def parsefile(self):
        lines = {}
        try:
            with open(self.file, "r") as f:
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
        title = self.file
        id = None
        m = re.match("(\d+) - (.+) - (.*)\.md$", title)
        if (m is not None):
            order = int(m.group(1))
            id = m.group(2)
            title = m.group(3)
        return order, id, title

    def reload(self):
        self.__init__(self.file)

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
        original_file = self.file
        self.order = new_order
        self.file = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        os.rename(original_file, self.file)

    def updatetags(self, new_tags):
        tags = new_tags.split(",")
        for i,t in enumerate(tags):
            tags[i] = t.strip()
        self.tags = tags
        self.write()

    def updatetitle(self, new_title):
        original_file = self.file
        self.title = new_title
        self.file = "{:04d} - {} - {}.md".format(self.order, self.id, self.title)
        os.rename(original_file, self.file)

    def updatelinks(self, url, new_url):
        new_note = None
        if (new_url is not None):
            new_note = Note(new_url)

        for i in self.links:
            if (i.url == url):
                if (new_note is None):
                    self.links.remove(i)
                else:
                    i.url = new_note.file
                    i.text = new_note.title
                
        for i in self.backlinks:
            if (i.url == url):
                if (new_note is None):
                    self.backlinks.remove(i)
                else:
                    i.url = new_note.file
                    i.text = new_note.title
        self.write()
        
    def write(self):
        with open(self.file, "w") as f:
            f.write(self.__str__())
            f.close()

#######
# FUNCTIONS
#######

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
def loadfiles():
    files = [f for f in os.listdir(".") if(os.path.isfile(os.path.join(".", f)) and re.search("\.md$",f))]
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
    n1 = Note(files[original_pos])
    n1_file = n1.file

    n2 = Note(files[new_pos])
    n2_file = n2.file
    new_order = n1.order
    if (n2.order == n1.order and new_pos < original_pos):
        new_order = gethole(files, new_pos)
    n1.updateorder(n2.order)
    n2.updateorder(new_order)
    files = loadfiles()
    for f in files:
        note = Note(f)
        note.updatelinks(n1_file, n1.file)
        note.updatelinks(n2_file, n2.file)
    return files

def main(stdscr):

    stdscr.clear()

    files = loadfiles()
    note1 = None
    if (args.filename is not None):
        note1 = Note(args.filename)

    command = None
    link_note = None
    move = False
    search = ""
    selected = 0
    top = 0
    while (command != "q"):
        stdscr.clear()

        status = ""
        if (note1 is not None):
            selected = note1.cursesoutput(stdscr, selected)
            file_index = 0
            try:
                file_index = files.index(note1.file)
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
                max_width = curses.COLS - 5
                if (i == selected):
                    stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f), curses.A_REVERSE)
                else:
                    stdscr.addstr(("{:" + str(max_width) + "." + str(max_width) + "s}\n").format(f))
            status = f"{selected+1} of {len(files)}"

        if (move is True):
            status = f"{status} MOVING"
        if (link_note is not None):
            status = f"{status} LINKING {link_note.title}"
        #if (command is not None and command is not "\n"):
        #    status = f"{status} {command}"

        if (status is not None):
            # Make sure a long status doesn't push 
            status = minorimpact.splitstringlen(status, curses.COLS-4)[0]
            stdscr.addstr(curses.LINES-1,0,status, curses.A_BOLD)
        stdscr.refresh()
        command = stdscr.getkey()

        if (note1 is not None):
            if (command == "KEY_DC" or command == ""):
                confirm = getstring(stdscr, "Are you sure you want to delete this link? (y/N):", 1)
                if (confirm == "y"):
                    note1.deletelink(selected)
                    note1.write()
            elif (command == "KEY_DOWN"):
                selected += 1
                if (selected > note1.linkcount()):
                    selected = 1
            elif (command == "KEY_UP"):
                selected -= 1
                if (selected < 1):
                    selected = note1.linkcount()
            elif (command == "KEY_LEFT" or command == "KEY_RIGHT"):
                selected = 0
                top = 0
                try:
                    file_index = files.index(note1.file)
                except:
                    note1 = None
                    continue

                if (command == "KEY_LEFT"):
                    file_index -= 1
                else:
                    file_index += 1

                if (file_index < 0):
                    file_index = len(files) - 1
                elif (file_index >= len(files)):
                    file_index = 0
                note1 = Note(files[file_index])
            elif (command == "e"):
                # Edit note
                curses.def_prog_mode()
                subprocess.call([os.environ['EDITOR'], note1.file])
                curses.reset_prog_mode()
                note1.reload()
            elif (command == "l"):
                # Link a note to this note
                if (link_note is None):
                    link_note = note1
                else:
                    note1.addnotelink(link_note)
                    note1.write()
                    link_note.addnotebacklink(note1)
                    link_note.write()
                    link_note = None
            elif (command == "r"):
                # get new name
                new_title = getstring(stdscr, "New Title: ", 80)
                original_file = note1.file
                note1.updatetitle(new_title)
                files = loadfiles()
                for f in files:
                    note = Note(f)
                    note.updatelinks(original_file, note1.file)
            elif (command == 't'):
                new_tags = getstring(stdscr, "Tags: ")
                note1.updatetags(new_tags)
            elif (command == "\n"):
                link = note1.getlink(selected)
                if (link is not None and not re.search("^[^ ]+:", link.url)):
                    try:
                        n = Note(link.url)
                        if (n is not None):
                            note1 = n
                    except:
                        pass
                    selected = 0
                elif (link is not None and re.search("^[^ ]+:", link.url)):
                    subprocess.run(['open', link.url], check=True)
            elif (command == ''):
                try:
                    selected = files.index(note1.file)
                except:
                    selected = 0

                #link_note = None
                note1 = None
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
                            original_file = n.file
                            n.updateorder(next_order)
                            files = loadfiles()
                            for f2 in files:
                                n2 = Note(f2)
                                n2.updatelinks(original_file, n.file)
                            next_order -= 1
                else:
                    note = Note(files[-1])
                    next_order = note.order + 1
                today = datetime.datetime.now()
                date = today.strftime("%Y-%m-%d %H-%M")
                filename = "{:04d} - {} - {}.md".format(next_order, date, new_title)
                new_note = Note(filename)
                new_note.write()
                files = loadfiles()
                note1 = new_note
            elif (command == "KEY_DC" or command == "d"):
                move = False
                note = Note(files[selected])
                original_file = note.file
                confirm = getstring(stdscr, "Are you sure you want to delete this note? (y/N):", 1)
                if (confirm == "y"):
                    note.delete()
                    files = loadfiles()
                    for f in files:
                        note = Note(f)
                        note.updatelinks(original_file, None)
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


#######
# START
#######

parser = argparse.ArgumentParser(description="Peruse and maintain a collection of Zettelkasten files in the current directory.")
parser.add_argument('filename', nargs="?")
parser.add_argument('--addlink', help = "add a link to ADDLINK to filename")
parser.add_argument('--nobacklink', help = "when adding a link, don't create a backlink from filename to ADDLINK", action='store_true')
parser.add_argument('--defrag', help = "update the zettelkasten files to remove any gaps between entries", action='store_true')
args = parser.parse_args()

if (args.addlink is not None and args.filename is not None):
    # Don't look at anything, just create a link from one file to another.
    note1 = Notes(args.filename)
    note2 = Note(args.addlink)
    note1.addnotelink(note2)
    note1.write()
    stdscr.addstr(f"Added link {note2.title} to {note1.title}\n")
    if (args.nobacklink is False):
        note2.addnotebacklink(note1)
        note2.write()
        stdscr.addstr(f"Added backlink {note1.title} to {note2.title}\n")
    sys.exit()
elif (args.defrag is True):
    # Make this fix all the files so that there are no duplicate orders
    #  and no holes
    files = loadfiles()
    for i in range(0, len(files)):
        note = None
        try:
            note = Note(files[i])
        except:
            raise Exception(f"Can't open '{files[i]}'")

        if (note.order != i+1):
            original_file = note.file
            note.updateorder(i+1)
            print(f"Moved {original_file} to {note.file}")
            files[i] = note.file

            for f in files:
                n = Note(f)
                n.updatelinks(original_file, note.file)
    sys.exit()


curses.wrapper(main)


