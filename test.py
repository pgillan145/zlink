#!/usr/bin/env python3

import os
import random
import tempfile
import unittest
import zlink.note

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

        # verify the search functions work
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
        # create multiple notes, make sure 
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

    def test_003_links(self):
        return

if __name__ == "__main__":
    unittest.main()
