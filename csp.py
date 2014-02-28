import itertools, re, random
from functools import reduce
from collections import namedtuple

from dbconnect import *
from utils import *


database = UniversityDatabase()
TimeSlot = namedtuple('TimeSlot', ['day', 'hour']) # timeslot in schedule


def get_group_disciplines():
    return {
        'g1281': [('Calculus I', 'lecture'), ('Physics I', 'lecture'), ('Circuits', 'lecture'),
                  ('Complex variable theory', 'lecture'),
                  ('Calculus I', 'practice'), ('Physics I', 'practice'), ('Circuits', 'practice'),
                  ('C language', 'lecture'), ('C language', 'practice')],
        'g1282': [('Calculus I', 'lecture'), ('Physics I', 'lecture'), ('Circuits', 'lecture'),
                  ('Complex variable theory', 'lecture'),
                  ('Calculus I', 'practice'), ('Physics I', 'practice'), ('Circuits', 'practice'),
                  ('C language', 'lecture'), ('C language', 'practice')],
        'g1283': [('Calculus I', 'lecture'), ('Physics I', 'lecture'), ('Circuits', 'lecture'),
                  ('Complex variable theory', 'lecture'),
                  ('Calculus I', 'practice'), ('Physics I', 'practice'), ('Circuits', 'practice'),
                  ('C language', 'lecture'), ('C language', 'practice')],

        'g1291': [('Calculus II', 'lecture'), ('Physics II', 'lecture'), ('OOP', 'lecture'), ('Software dev', 'lecture'),
                  ('OOP', 'practice'), ('Software dev', 'practice'),
                  ('Calculus II', 'practice'), ('Physics II', 'practice')],
        'g1291': [('Calculus II', 'lecture'), ('Physics II', 'lecture'), ('OOP', 'lecture'), ('Software dev', 'lecture'),
                  ('OOP', 'practice'), ('Software dev', 'practice'),
                  ('Calculus II', 'practice'), ('Physics II', 'practice'), ('Compilers', 'lecture'), ('Compilers', 'practice')],
        'g1293': [('Calculus II', 'lecture'), ('Physics II', 'lecture'), ('Optics', 'lecture'), ('Optics', 'practice'),
                  ('Quantum mech', 'lecture'), ('Quantum mech', 'practice'),
                  ('Calculus II', 'practice'), ('Physics II', 'practice')]
    }


def get_lecturer_hours():
    # в релизе необходимо заменить строки с названиями предметов на кортежи
    # следующего вида: (discipline_id, process_type_id). Кроме того, все остальные
    # строки будут заменены на id-номера из БД.
    return {
        'Jones': {('Calculus I', 'lecture'): 2, ('Calculus II', 'lecture'): 2},
        'Smith': {('Calculus I', 'practice'): 6, ('Calculus II', 'practice'): 4},
        'Fisher': {('Calculus II', 'lecture'): 2},
        'Stone': {('Physics I', 'lecture'): 2, ('Physics I', 'practice'): 6, ('Quantum mech', 'lecture'): 2},
        'Fry': {('Physics II', 'lecture'): 2, ('Physics II', 'practice'): 4, ('Quantum mech', 'practice'): 1},
        'Backer': {('Optics', 'lecture'): 3, ('Optics', 'practice'): 2},
        'Holmes': {('OOP', 'lecture'): 1, ('OOP', 'practice'): 2, ('C language', 'lecture'): 2,
                   ('Software dev', 'lecture'): 1, ('Software dev', 'practice'): 2},
        'Forest': {('Circuits', 'lecture'): 1, ('Circuits', 'practice'): 3},
        'Lory': {('Complex variable theory', 'practice'): 3},
        'Rusty': {('C language', 'practice'): 3}
    }

def get_room_domains():
    return {
        ('Calculus I', 'lecture'): [405, 406, 407],
        ('Calculus II', 'lecture'): [405, 406, 407],
        ('Calculus I', 'practice'): [420, 421],
        ('Calculus II', 'practice'): [420, 421],
        ('Physics I', 'lecture'): [322, 323],
        ('Physics II', 'lecture'): [322, 324],
        ('Physics I', 'practice'): [301, 302],
        ('Physics II', 'practice'): [301, 302, 303],
        ('Circuits', 'lecture'): [606, 607],
        ('Circuits', 'practice'): [601],
        ('OOP', 'lecture'): [606, 607],
        ('Software dev', 'lecture'): [606, 607],
        ('OOP', 'practice'): [602, 603, 604],
        ('Software dev', 'practice'): [602, 603, 604],
        ('Optics', 'lecture'): [303],
        ('Optics', 'practice'): [301, 302],
        ('Quantum mech', 'lecture'): [322, 323],
        ('Quantum mech', 'practice'): [306],
        ('Complex variable theory', 'lecture'): [405, 406, 407],
        ('Complex variable theory', 'practice'): [405, 406, 407],
        ('C language', 'lecture'): [606, 607],
        ('C language', 'practice'): [602, 603, 604]
    }

def todict(var_list):
    return { v.__str__():v for v in var_list }

def tolist(var_dict):
    return list(var_dict.values())


class Variable:
    def __init__(self, domain:list, neighbors = None, name = None):
        self.__name = name
        self.__init_domain = domain
        self.neighbors = [] if neighbors is None else neighbors
        self.curr_domain = domain
        self.curr_value = None

    @property
    def init_domain(self):
        return self.__init_domain

    @property
    def name(self):
        return self.__name

    def assign(self, value):
        assert(value in self.curr_domain)
        self.curr_value = value

    def unassign(self):
        self.curr_value = None

    def isassigned(self):
        return self.curr_value is not None

    def isunassigned(self):
        return self.curr_value is None

    def __eq__(self, other):
        return self.curr_value == other.curr_value

    def __hash__(self):
        return (int(self.name)+1)*(len(self.init_domain)+1)

    def __str__(self):
        return self.name


class TimeVariable(Variable):
    week = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    hours = [1, 2, 3, 4, 5, 6]

    def __init__(self, lecturer_name, subject, count):
        timeslots = [(d, h) for d in TimeVariable.week for h in TimeVariable.hours]
        super().__init__(timeslots)
        self.lecturer_name = lecturer_name
        self.subject = subject
        self.count = count

    def __str__(self):
        return 'TimeVar: '+'_'.join([self.lecturer_name, self.subject, str(self.count)])


class RoomVariable(Variable):
    def __init__(self, lecturer_name, subject, count, domain):
        super().__init__(domain)
        self.lecturer_name = lecturer_name
        self.subject = subject
        self.count = count

    def __str__(self):
        return 'RoomVar: '+'_'.join([self.lecturer_name, self.subject, str(self.count)])


class CSP:
    def __init__(self):
        self.__variables = []
        self.nassigned = 0

    @property
    def variables(self):
        return self.__variables

    @variables.setter
    def variables(self, val):
        self.__variables = val

    @property
    def assignment(self):
        return [v for v in self.variables if v.isassigned()]

    def add_variable(self, var: Variable):
        self.__variables.append(var)

    def setup_constraints(self):
        pass

    def infer_assignment(self):
        return dict((str(Xi), Xi.curr_domain) for Xi in self.variables)

    def constraints(self, var1, value1, var2, value2):
        return var1 == var2 or value1 != value2

    def preferences(self):
        return 0 # thumb

    def restoreall(self, removed):
        for var, value in removed:
            var.curr_domain.append(value)

    def conflicts(self, X, possible_value):
        ''' Returns number of conflicts in CSP for variable X '''
        conflict = (lambda Y: Y.isassigned()
                              and not self.constraints(X, possible_value, Y, Y.curr_value))
        return len(list(filter(conflict, X.neighbors)))

    def violation_list(self):
        return [var for var in self.variables
                if var.isassigned() and self.conflicts(var, var.curr_value) > 0]


def flatten(seqs): return sum(seqs, [])

class Sudoku(CSP):
    def __init__(self, grid):
        super().__init__()
        R3 = range(3)
        Cell = itertools.count().__next__
        bgrid = self.bgrid = [[[[Cell() for x in R3] for y in R3] for bx in R3] for by in R3]
        boxes = flatten([list(map(flatten, brow))       for brow in bgrid])
        rows  = flatten([list(map(flatten, zip(*brow))) for brow in bgrid])
        cols = list(zip(*rows))
        squares = iter(re.findall(r'\d|\.', grid))

        for var, ch in zip(flatten(rows), squares):
            v = Variable(
                domain=([ch] if ch in '123456789' else list('123456789')),
                name=str(var),
                neighbors=set())
            self.add_variable(v)
        for _ in squares:
            raise ValueError("Not a Sudoku grid", grid) # Too many squares
        var_dict = todict(self.variables)
        for unit in map(set, boxes + rows + cols):
            for v in unit:
                new_neighbors = unit - set([v])
                nbrs = {var_dict[v] for v in var_dict if int(v) in new_neighbors}
                var_dict[str(v)].neighbors.update(nbrs)
        self.variables = tolist(var_dict)

    def constraints(self, var1, value1, var2, value2):
        return value1 != value2

    def infer_assignment(self):
        return dict((v.name, v.curr_domain) for v in self.variables if 1 == len(v.curr_domain))

    def display(self):
        assignment = self.infer_assignment()

        def abut(lines1, lines2):
            return map(' | '.join, zip(lines1, lines2))
        def show_cell(cell):
            return assignment.get(str(cell), '.')[0]
        def show_box(box):
            return [' '.join(map(show_cell, row)) for row in box]

        print('\n------+-------+------\n'.join(
            '\n'.join(reduce(abut, map(show_box, brow))) for brow in self.bgrid
        ))


class MapColoring(CSP):
    def __init__(self, colors, neighbors):
        super().__init__()
        vars = {}
        for var in neighbors:
            vars[var] = Variable(colors[:], name=var)
        for var_name in vars:
            for neighbor in neighbors[var_name]:
                vars[var_name].neighbors.append(vars[neighbor])
            self.variables.append(vars[var_name])

    def constraints(self, var1, value1, var2, value2):
        return value1 != value2

    def preferences(self):
        var = [x for x in self.variables if x.name == 'T'][0]
        return {
            'R': 10,
            'G': 5,
            'B': 1
        }[var.curr_value]

    def display(self):
        for var in self.variables:
            print(var.name, '=', var.curr_domain)


class TimetablePlanner1(CSP):
    def __init__(self):
        ''' Variables creation. There are 2*k variables for each lecturer
            where k is number of execises which lecturer should provide
            every week. First k variables needed for time and another k - for rooms
        '''
        super().__init__()
        lecturer_hours = get_lecturer_hours()
        room_domains = get_room_domains()
        for lecturer_name in sorted(lecturer_hours):
            subj_dict = lecturer_hours[lecturer_name]
            for subj in subj_dict:
                n = subj_dict[subj]
                while n > 0:
                    self.add_variable(TimeVariable(lecturer_name, subj, n))
                    domain = room_domains[subj]
                    self.add_variable(RoomVariable(lecturer_name, subj, n, domain))
                    n -= 1
        self.setup_constrainsts()

    def setup_constrainsts(self):
        ''' Setup binary constraints between variable pairs '''
        for Xi in self.variables:
            for Xj in self.variables:
                if Xi is Xj: continue # do not tie variable with itself
                if isinstance(Xi, TimeVariable) and isinstance(Xj, TimeVariable):
                    if Xi.lecturer_name == Xj.lecturer_name: # variables with same lecturer
                        Xi.neighbors.append(Xj)
                    continue
                if isinstance(Xi, TimeVariable) and isinstance(Xj, RoomVariable):
                    Si, Sj = Xi.subject, Xj.subject
                    if Si == Sj and Xi.lecturer_name == Xj.lecturer_name: continue
                    all_subjects = get_group_subjects() # subject sets for all institute groups
                    for subj_list in all_subjects.values(): # iterate throw subject sets
                        if Si in subj_list and Sj in subj_list: # some group has both Si and Sj
                            Xi.neighbors.append(Xj)
                    continue
                # check if Xi and Xj has intersections in domains
                if (isinstance(Xi, RoomVariable) and isinstance(Xj, RoomVariable)
                    and set(Xi.init_domain).intersection(set(Xj.init_domain))):
                        Xi.neighbors.append(Xj)

    def constrainsts(self, var1, value1, var2, value2):
        if (isinstance(var1, TimeVariable) and isinstance(var2, TimeVariable)
            and var1 == var2):
            return False
        return True


WEEK = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']

class ScheduleVariable(Variable):
    timeslots = [TimeSlot(d, h) for d in WEEK for h in range(1, 7)]

    def __init__(self, lecturer, discipline, listeners, possible_rooms, count = 0):
        super().__init__(domain=[(t, r) for t in ScheduleVariable.timeslots
                                        for r in possible_rooms])
        self.lecturer = lecturer
        self.discipline = discipline
        self.listeners = listeners
        self.possible_rooms = possible_rooms
        self.type = None
        self.count = count

    def __hash__(self):
        return (self.count + 1) * (hash(self.lecturer) + hash(self.discipline))

    def __str__(self):
        return ' '.join([self.lecturer, self.discipline, str(self.count)])

    def samelecturers(self, other):
        return self.lecturer == other.lecturer

    def samerooms(self, other):
        return self.possible_rooms.intersection(other.possible_rooms)

    def samelisteners(self, other):
        return self.listeners.intersection(other.listeners)


class TimetablePlanner2(CSP):
    ''' Планировщик расписаний.

        Планирование расписания рассматривается как решение CSP. Каждый
        элемент расписания представлен переменной, значением которой
        является кортеж, содержищий интервал времени (день и номер пары),
        и номера аудитории. Необходимыми для инициализации входными
        данными являются:

        1) словарь, ключами которого являются имена преподавателей,
           а значениями вновь словари; ключами этих вложенных словарей
           являются названия предметов, значениями - количество часов,
           которое должен провести преподаватель; при этом, лекционные
           и практические занятия рассматриваются отдельно

        2) словарь, ключами которого являются имена групп, а значениями -
           списки предметов, предписанных для изучения

        3) словарь, ключи которого - названия предметов, а значения -
           списки аудиторий, в которых могут проводиться (или обычно проводятся)
           занятия по данному предмету

        Метод setup_constraints() связывает ограничениями переменные.
        Метод constraints(A, a, B, b) проверяет, не нарушают ли
        присваивания A=a и B=b какое-либо из ограничений (все ограничения
        - бинарные).

    '''

    def __init__(self):
        super().__init__()
        lecturer_hours = get_lecturer_hours()
        room_domains = get_room_domains()
        get_group_disciplines()
        for lecturer in sorted(lecturer_hours):
            subj_dict = lecturer_hours[lecturer]
            for subj in subj_dict:
                n = subj_dict[subj]
                while n > 0:
                    possible_rooms = set(room_domains[subj])

                    listeners = {g for g, s in get_group_disciplines().items()
                                   if subj in s}
                    self.add_variable(ScheduleVariable(lecturer, subj, listeners, possible_rooms, n))
                    n -= 1

    def setup_constraints(self):
        for Xi in self.variables:
            for Xj in self.variables:
                if Xi is Xj: continue
                if Xi.samelecturers(Xj) or Xi.samerooms(Xj) or Xi.samelisteners(Xj):
                    Xi.neighbors.append(Xj)

    def constraints(self, A, a, B, b):
        if A is B: return True
        aTime, aRoom = a
        bTime, bRoom = b
        if A.samelecturers(B) and aTime == bTime:
            return False
        if A.samerooms(B) and aTime == bTime and aRoom == bRoom:
            return False
        if A.samelisteners(B) and aTime == bTime:
            return False # need more precise constraint (maybe subclass ScheduleVariable?)
        return True

    def preferences(self):
        def max_day_load():
            pairs = [[v.curr_value[0].hour for v in self.variables
                     if v.curr_value[0].day == day] for day in WEEK]
            return max(map(max, filter(lambda x: len(x), pairs)))

        return bounded_sum(self.weight_list().values())

    def weight_list(self):
        def weight(var):
            if var.isunassigned():
                return INFINITY
            acc = 0
            t, r = var.curr_value
            if t.hour == 6:
                acc += 10
            if t.day == 'mon':
                acc -= 2
            if t.day == 'sat':
                acc += 4
            return acc

        return {var : weight(var) for var in self.variables}

    def infer_assignment(self):
        return dict((str(Xi), Xi.curr_value) for Xi in self.variables
                    if Xi.isassigned())


def AC3(csp, queue = None):
    ''' Arc consistency. Реализует алгоритм поддержания ...'''
    def revise(Xi, Xj):
        revised = False
        for x in Xi.curr_domain:
            if every(lambda y: not csp.constraints(Xi, x, Xj, y),
                  [y for y in Xj.curr_domain]):
                Xi.curr_domain.remove(x)
                revised = True
        return revised

    if queue is None:
        queue = [(Xi, Xk) for Xi in csp.variables for Xk in Xi.neighbors]
    while queue:
        (Xi, Xj) = queue.pop()
        if revise(Xi, Xj):
            if len(Xi.curr_domain) == 0: return False
            for Xk in Xi.neighbors:
                queue.append((Xk, Xi))
    return True

# Variable ordering heuristics

def first_unassigned_variable(csp):
    assert([v for v in csp.variables if not v.isassigned()]) # FIXME: will be removed
    for v in csp.variables:
        if not v.isassigned(): return v

def minimum_remaining_value(csp):
    pass


# Value ordering heuristics

def least_constraining_value(var, csp):
    return sorted(var.curr_domain,
                  key=lambda Vi: csp.conflicts(var, Vi))


def forward_checking(X, csp, removed):
    ''' Simplest way of inference. Whenever X is assigned, function establishes
        arc consistency for it: for each unassigned variable Y connected to X
        by constraint, delete from Y.curr_domain values inconsistent with X.value.

        [According to: AIMA, 3rd, p.217]
    '''
    for Y in X.neighbors:
        if Y.isunassigned():
            for y in Y.curr_domain:
                if not csp.constraints(X, X.curr_value, Y, y):
                    Y.curr_domain.remove(y)
                    removed.append((Y, y))
            if not Y.curr_domain:
                return False
    return True


def BacktrackingSearch(csp,
                       select_unassigned_variable=first_unassigned_variable,
                       order_domain_values=least_constraining_value,
                       inference=forward_checking):
    ''' Backtracking algorithm for CSP. Variable selection, domain values
        ordering and inference algorithms could be tuned.

        [According to: AIMA, 3rd, p.214]
    '''
    def Backtrack():
        if len(csp.assignment) == len(csp.variables):
            return True
        var = select_unassigned_variable(csp)
        for value in order_domain_values(var, csp):
            if not csp.conflicts(var, value):
                var.assign(value)
                removed = [(var, x) for x in var.curr_domain if x != value]
                var.curr_domain = [value]
                if inference(var, csp, removed):
                    result = Backtrack()
                    if result:
                        return True
                csp.restoreall(removed)
            var.unassign()
        return False

    return Backtrack()


def min_conflicts(csp, max_steps=10000):
    def argmin_conflicts(var):
        return argmin(lambda x: csp.conflicts(var, x),
                      var.curr_domain, random.choice)

    # initial assignment (probably unfeasible)
    for var in csp.variables:
        var.assign(argmin_conflicts(var))
    # local search
    best_value = INFINITY
    best_assignment = None
    for _ in range(max_steps):
        violations = csp.violation_list()
        if not violations: # all constrains satisfied
            return {v.name:v.curr_value for v in csp.variables}
        var = random.choice(violations)
        val = argmin_conflicts(var)
        var.assign(val)
    return best_assignment


def iterative_forward_search(csp, max_steps=5000):
    def argmin_conflicts(var):
        return argmin(lambda x: csp.conflicts(var, x),
                      var.curr_domain, random.choice)

    def most_weight_variable(vars):
        from operator import itemgetter
        return max(csp.weight_list().items(), key=itemgetter(1))[0]

    best_value, best_assignment = INFINITY, csp.infer_assignment()
    for _ in range(max_steps):
        X = most_weight_variable(csp.variables)
        a = argmin_conflicts(X)
        X.assign(a)
        violations = csp.violation_list()
        if not violations:
            estimate = csp.preferences()
            if estimate < best_value:
                print(estimate)
                best_value, best_assignment = estimate, csp.infer_assignment()
        for Y in violations: Y.unassign()
    return best_assignment


ttp = TimetablePlanner2()
#ttp.setup_constraints()
#d1 = ttp.infer_assignment()
#iterative_forward_search(ttp)
#d2 = ttp.infer_assignment()
#print(ttp.preferences())

#for k in d2: print(k, d2[k])

easy1   = '..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3..'
s = Sudoku(easy1)
#BacktrackingSearch(s)
#s.display()

australia = MapColoring(list('RGB'), {
    'SA':  ['WA', 'NT', 'Q', 'NSW', 'V'],
    'WA':  ['SA', 'NT'],
    'Q' :  ['SA', 'NT', 'NSW'],
    'NT':  ['WA', 'Q'],
    'NSW': ['Q', 'V'],
    'V':   ['SA', 'NSW'],
    'T':   []
})
a = min_conflicts(australia)
print_dictionary(a if a else {})

# Stone Physics I practice 6 (TimeSlot(day='mon', hour=1), 302)
# Jones Calculus II 2 (TimeSlot(day='mon', hour=1), 405)