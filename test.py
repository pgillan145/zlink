#!/usr/bin/env python3

import os
import random
import re
import tempfile
import unittest
import zlink.note

# https://docs.python.org/3/library/unittest.html
# test fixture
#   setup steps necessary to run one or more tests
#test case
#   individual unit of testing, one specific peice of functionality
# test suite
#   A collection of test cases and/or suites
# test runner
#   The overall mechanism for running tests and returning the data to the user/caller

class TestNote(unittest.TestCase):

    test_dir = None

    #def __init__(self, methodName):
    #    super(TestNote, self).__init__(methodName)
    #    self.test_dir = os.getcwd()

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        os.chdir(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_001_newnote(self):
        # create a new note based on position and title
        note_order = random.randint(1,9)
        note = zlink.note.newNote(note_order,"TITLE")
        self.assertEqual(note.order,note_order)

        # verify the file is what we expect
        fields = note.filename.split(" - ")
        self.assertEqual(fields[0], '000' + str(note_order))
        self.assertEqual(fields[2], 'TITLE.md')

        # verify the internal search function works
        self.assertTrue(note.search("title"))
        self.assertTrue(note.search("TITLE"))
        self.assertFalse(note.search("foo"))

        # load a note by filename
        new_note = zlink.note.Note(note.filename)
        self.assertEqual(new_note.title, "TITLE")

        # try and load an invalid note
        with self.assertRaises(Exception):
            new_note = zlink.note.Note("invalid filename")

    def test_002_multiplenotes(self):
        # create multiple notes, make sure they're loaded properly
        note1 = zlink.note.newNote(1,"ONE")
        note2 = zlink.note.newNote(2,"TWO")
        self.assertEqual(note1.order,1)
        self.assertEqual(note2.order,2)
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 2)
        self.assertEqual(zlink.note.Note(notes[0]).title, "ONE")
        self.assertEqual(zlink.note.Note(notes[1]).title, "TWO")

        # swap them around
        zlink.note.swapnotes(notes,0,1)
        notes = zlink.note.loadnotes()
        self.assertEqual(zlink.note.Note(notes[0]).title, "TWO")
        self.assertEqual(zlink.note.Note(notes[1]).title, "ONE")

        # insert a new note in between them
        new_hole = zlink.note.makehole(notes, 1)
        self.assertEqual(new_hole, 2)
        note3 = zlink.note.newNote(new_hole, "THREE")
        notes = zlink.note.loadnotes()
        self.assertEqual(zlink.note.Note(notes[0]).title, "TWO")
        self.assertEqual(zlink.note.Note(notes[1]).title, "THREE")
        self.assertEqual(zlink.note.Note(notes[2]).order, 3)

        # create a new note with an order/position that's already defined
        # (NOTE: should this be allowed? Maybe we should throw an error if you're creating
        #        new note that's already taken? We might want to revisit this)
        note4 = zlink.note.newNote(3, "FOUR")
        notes = zlink.note.loadnotes()
        self.assertEqual(zlink.note.Note(notes[2]).order, 3)
        self.assertEqual(zlink.note.Note(notes[3]).order, 3)
        new_hole = zlink.note.makehole(notes, 2)

        # make sure makehole() fixes duplicate orders
        self.assertEqual(new_hole, 3)
        notes = zlink.note.loadnotes()
        self.assertEqual(zlink.note.Note(notes[2]).order, 4)
        self.assertEqual(zlink.note.Note(notes[3]).order, 5)

        # make sure delete() works
        note = zlink.note.Note(notes[1])
        self.assertEqual(note.title, "THREE")
        note.delete()
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 3)
        self.assertEqual(zlink.note.Note(notes[0]).title, "TWO")
        self.assertEqual(zlink.note.Note(notes[1]).title, "FOUR")
        self.assertEqual(zlink.note.Note(notes[2]).title, "ONE")

    def test_003_links(self):
        note1 = zlink.note.newNote(1,"ONE")
        note2 = zlink.note.newNote(2,"TWO")
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 2)

        # confirm note links are created correctly
        note1.addnotelink(note2)
        note1.write()
        test_note = zlink.note.Note(note1.filename)
        self.assertEqual(test_note.linkcount(),1)
        # TODO: Verify there's a good reason for the link selection to be 1 based rather than 0 based
        #       like note selection.  I *think* I did that on purpose, but I have no idea why.
        link = test_note.getlink(1)
        self.assertEqual(link.text, "TWO")
        self.assertTrue(re.search(" - TWO.md$", link.url))
        self.assertTrue(re.search("^0002 - ", link.url))
        original_url = link.url

        # Insert a new entry and confirm that the url is properly updated on the notes that were moved
        new_hole = zlink.note.makehole(notes, 1)
        self.assertEqual(new_hole, 2)
        note3 = zlink.note.newNote(new_hole, "THREE")

        notes = zlink.note.loadnotes()
        test_note = zlink.note.Note(notes[0])
        self.assertEqual(test_note.title, "ONE")
        # NOTE: still confusing
        link = test_note.getlink(1)
        self.assertEqual(link.text, "TWO")
        self.assertTrue(re.search(" - TWO.md$", link.url))
        self.assertTrue(re.search("^0003 - ", link.url))
        self.assertTrue(re.sub("^0002 - ", "0003 - ", original_url), link.url)
    
    def test_004_filters(self):
        # verify filters only show us the notes we expect
        note1 = zlink.note.newNote(1, "ONE")
        note1.default = ["this is data for note number one"]
        note1.write()
        note2 = zlink.note.newNote(2, "TWO")
        note2.default = ["this is data for note number two"]
        note2.write()
        note3 = zlink.note.newNote(3, "THREE")
        note3.default = ["this is garbage for note number three"]
        note3.write()

        zlink.globalvars.filter = "data"
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 2)

        zlink.globalvars.filter = "garbage"
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 1)

        zlink.globalvars.filter = ""
        notes = zlink.note.loadnotes()
        self.assertEqual(len(notes), 3)

    # TODO:
    #        Write a test to focus on data.
    #           - tags, references, backlinks and whatnot
    #        Write at least one test that dumps a note to a string and verifies the actual data.  That
    #           seems like a bug that could happen really easily.
    #        Compare the data to the actual file written to disk to make sure no bugs are creeping in that way.
    #        Move a lot of the note creation code to the startUp() function, and break each long test function into
    #           smaller methods, and turn each of the test methods I have now into seperate test cases.  I think smaller
    #           is better when it comes to these things.
    #        Figure out if there's some way to have these tests "build" on one another.  It seems like the work done during early tests
    #           of basic functionality could serve as a basis for more complicated tests further down in the process.
    #        Likewise... it seems odd that these tests would be run in alphabetical order as opposed the order that they're defined... while it's
    #           true they don't have to be run in any specific order since the data is blown away and recreated between each one, but if a "high" level
    #           mechanism breaks, it'll be way harder to troubleshoot than it would have been if I'd seen the failed "low" level test first.  Numbering
    #           the functions seems like a meh solution compared to being able to define dependencies.


if __name__ == "__main__":
    unittest.main()
