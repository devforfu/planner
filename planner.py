import random
from collections import namedtuple, defaultdict
import ezodf


class SubjectType:
    lecture = 1
    stream_lecture = 2
    practice = 3
    lab = 4

Constraint = namedtuple(
    'Constraint',
    ['rooms', 'type']
)

class Lecturer:
    def __init__(self, name, subjects: list):
        self.name = name
        self.subjects = subjects
        self.busy_time = {} # dictionary with filled timeslots: (day, hour) -> (subject, groupid, room)

    def __str__(self):
        return self.name

    def is_busy(self, timeslot):
        return timeslot in self.busy_time.keys()

    def fill_slot(self, timeslot, subject, groupid, room):
        self.busy_time[timeslot] = (subject, groupid, room)


class Group:
    def __init__(self, group_id: str, lectures: dict):
        self.id = group_id
        self.unplanned_lectures = lectures # contains lectures without timeslots
        self.busy_time = {} # dictionary contains such records: (day, hour) -> (subject, lecturer, room)

    def __str__(self):
        return self.id

    def lecture_quantity(self, day):
        return len([h for ((d, h), s) in self.busy_time.items() if d == day])

    def is_busy(self, time_slot):
        return time_slot in self.busy_time.keys()

    def is_empty_day(self, day):
        return self.lecture_quantity(day) == 0

    def fill_slot(self, timeslot, subject, lecturername, room):
        self.busy_time[timeslot] = (subject, lecturername, room)


class TimetablePlanner:
    WEEK = [
        'MON', 'TUE', 'WED',
        'THU', 'FRI', 'SAT'
    ]
    HOURS = [
        '1st', '2nd', '3rd',
        '4th', '5th'#, '6th'
    ]

    def __init__(self, constraints, groups, lecturers):
        self.constraints = constraints
        self.groups = groups
        self.lecturers = lecturers
        self.taken_rooms = defaultdict(list)


    def plan_group_lectures(self, group, lecturer):
        ''' Fills group and lecturer objects with feaseble values of timeslots.
            Is used for random generation of feasible solution in genetic algorithm.
        '''
        # list of subjects this group is studying
        group_subjects = group.unplanned_lectures.keys()
        # list of subjects which this lecturer is teaching for this group
        actual_lectures = set(group_subjects).intersection(lecturer.subjects)

        if not actual_lectures: # lecturer is not teaching this group
            return
        week, hours = TimetablePlanner.WEEK, TimetablePlanner.HOURS
        time_slots = [(d, h) for d in week for h in hours]
        random.shuffle(time_slots)

        for lecture in actual_lectures:
            free_room = None
            for slot in time_slots:
                if not group.unplanned_lectures[lecture]:
                    break # all lectures for current subject were planned
                if group.is_busy(slot) or lecturer.is_busy(slot):
                    continue
                if group.lecture_quantity(slot[0]) >= 4:
                    continue # not more than 4 lectures per day
                try:
                    free_room = random.choice(
                        [r for r in self.constraints[lecture].rooms
                        if r not in self.taken_rooms[slot]]
                    )
                except IndexError:
                    continue # if free room is absent then choose another timeslot
                self.taken_rooms[slot].append(free_room)
                lecturer.fill_slot(slot, lecture, group.id, free_room)
                group.fill_slot(slot, lecture, lecturer.name, free_room)
                group.unplanned_lectures[lecture] -= 1


    def create_feasible_timetable(self):
        ''' Returns imetable that maintains all constraints but is not optimal '''
        random.shuffle(self.groups)
        random.shuffle(self.lecturers)
        for g in self.groups:
            for l in self.lecturers:
                self.plan_group_lectures(g, l)


    def find_optimal_timetable(self):
        pass


    def damp_timetable(self, filename):
        ''' Creates file in .ods format with selected name for timetable keeping. '''
        group_names = sorted([g.id for g in self.groups])
        week, hours = TimetablePlanner.WEEK, TimetablePlanner.HOURS + ['6th']
        time_slots = [(d, h) for d in week for h in hours]

        ods = ezodf.newdoc(doctype='ods', filename=filename)
        sheet = ezodf.Sheet('Timetable', size=(37, 6))
        ods.sheets += sheet

        coords = [str(r) + str(c) for r in 'ABCDEF' for c in range(2, 38)]
        headers = [c + '1' for c in 'ABCDEF']

        for header, name in zip(headers, group_names):
            sheet[header].set_value(name)
        start, end = 0, 36
        for g in sorted(self.groups, key=lambda x: x.id):
            for (coord, timeslot) in zip(coords[start:end], time_slots):
                if timeslot in g.busy_time:
                    sheet[coord].set_value(g.busy_time[timeslot][0])
            start, end = end, end + 36
        ods.save()


    def print_group_timetable(self, group):
        from operator import itemgetter

        def day_number(slot):
            return {
                'MON': 1, 'TUE': 2, 'WED': 3,
                'THU': 4, 'FRI': 5, 'SAT': 6
            }[slot[0]]

        times = sorted(group.busy_time.keys(), key=itemgetter(1))
        times = sorted(times, key=day_number)
        print('Group ' + group.id, group.unplanned_lectures)
        for day, hour in times:
            print(day, hour, ': ', group.busy_time[(day, hour)])


    def print_timetable(self):
        for g in self.groups:
            self.print_group_timetable(g)
            print('')
