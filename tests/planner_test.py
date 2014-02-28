import unittest
from planner import TimetablePlanner, Constraint, Lecturer, Group, SubjectType


class TimetablePlannerTestCase(unittest.TestCase):
    def setUp(self):
        constraints = {
            'Calculus I': Constraint([304, 306, 311], SubjectType.lecture),
            'Calculus II': Constraint([304, 306, 311], SubjectType.lecture),
            'Physics I': Constraint([409, 411], SubjectType.stream_lecture),
            'Physics II': Constraint([409, 411], SubjectType.stream_lecture),
            'Circuits': Constraint([501, 502], SubjectType.stream_lecture),
            'OOP': Constraint([501, 502], SubjectType.stream_lecture),
            'Software dev.': Constraint([501, 502], SubjectType.stream_lecture),
            'Compilers': Constraint([501, 502, 503], SubjectType.lecture),
            'Quantum mech.': Constraint([401, 402],  SubjectType.lecture),
            'Optics': Constraint([401, 402], SubjectType.lecture),
            'Theoretical mech.': Constraint([303], SubjectType.lecture)
        }

        g1281 = Group('12-81', {
            'Calculus I': 2,
            'Physics I': 2,
            'Circuits': 3
        })
        g1282 = Group('12-82', {
            'Calculus I': 3,
            'Physics I': 2,
            'Circuits': 2
        })
        g1283 = Group('12-83', {
            'Calculus I': 2,
            'Physics I': 3,
            'Circuits': 2
        })
        g1291 = Group('12-91', {
            'Calculus II': 2,
            'Physics II': 3,
            'OOP': 3,
            'Software dev.': 3,
            'Theoretical mech.': 4
        })
        g1292 = Group('12-92', {
            'Calculus II': 2,
            'Physics II': 3,
            'OOP': 3,
            'Software dev.': 3,
            'Compilers': 4
        })
        g1293 = Group('12-93', {
            'Calculus II': 2,
            'Physics II': 3,
            'Quantum mech.': 2,
            'Optics': 3
        })

        smith = Lecturer('Prof. Smith',  ['Calculus I', 'Calculus II', 'Theoretical mech.'])
        jones = Lecturer('PhD. Jones', ['Calculus I'])
        fisher = Lecturer('Prof. Fisher', ['Physics I', 'Physics II', 'Optics'])
        stone = Lecturer('Dr. Stone', ['Calculus I', 'Calculus II'])
        fry = Lecturer('PhD. Fry', ['Physics I', 'Physics II'])
        holmes = Lecturer('Dr. Holmes', ['OOP', 'Software dev.', 'Compilers'])
        backer = Lecturer('PhD. Backer', ['OOP'])
        drake = Lecturer('Prof. Drake', ['Physics I', 'Physics II', 'Quantum mech.'])
        gnome = Lecturer('Dr. Gnome', ['Calculus I', 'Calculus II'])
        forest = Lecturer('Prof. Forest', ['Circuits'])

        self.planner = TimetablePlanner(
            constraints, # are relative to subjects
            [g1281, g1282, g1283, g1291, g1292, g1293], # academic groups
            [smith, jones, fisher, stone, fry,          # lecturers
             holmes, backer, drake, gnome, forest]
        )

    def test_create_feasible_timetable(self):
        self.planner.create_feasible_timetable()
        # no unplanned lectures
        self.assertEquals(
            sum([sum(g.unplanned_lectures.values()) for g in self.planner.groups]), 0)


if __name__ == '__main__':
    unittest.main()
