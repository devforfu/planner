import unittest
from dbconnect import *


class UnivercityDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.database = UniversityDatabase(ConnData('localhost', 'work', '123', 'univercity'))

    def get_disciplines_for_group_test(self):
        pass

if __name__ == '__main__':
    unittest.main()
