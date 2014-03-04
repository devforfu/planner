import itertools, re, random
from functools import reduce
from collections import namedtuple, defaultdict
from operator import add

from dbconnect import *
from utils import *
from algorithms import *


database = UniversityDatabase()
TimeSlot = namedtuple('TimeSlot', ['day', 'hour']) # timeslot in schedule


def get_group_disciplines():
    return database.get_disciplines_for_group()


def get_lecturer_hours():
    return database.get_teacher_hours()


def get_room_domains():
    domains = defaultdict(set)
    rooms = list(database.get_rooms_in_building(4))
    for exercise in database.get_all_exercises():
        new_domain = set()
        for _ in range(random.randint(2,4)):
            new_domain.add(random.choice(rooms))
        domains[exercise].update(new_domain)
    return domains


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
        return id(self)

    def __str__(self):
        return self.name


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
        return 0 if not self.violation_list() else INFINITY

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


def flatten(seqs):    return sum(seqs, [])
def todict(var_list): return { v.__str__():v for v in var_list }
def tolist(var_dict): return list(var_dict.values())

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


class ScheduleVariable(Variable):
    ''' Каждой записи в таблице Exercises соответствует количество переменных,
        равное значению атрибута hours этой записи.
    '''
    timeslots = [TimeSlot(d, h) for d in WEEK for h in range(1, 7)]

    def __init__(self, lecturer, exercise, listeners, possible_rooms, count = 0):
        super().__init__(domain=[(t, r) for t in ScheduleVariable.timeslots
                                        for r in possible_rooms])
        self.lecturer = lecturer
        self.exercise = exercise
        self.listeners = listeners
        self.possible_rooms = possible_rooms
        self.count = count
        self.key = (self.lecturer.id, self.exercise.id, count)
        self.weight = None

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        key = str(self.key)
        fullname = ' '.join([
            self.lecturer.firstname,
            self.lecturer.middlename,
            self.lecturer.lastname])
        discipline = self.exercise.name
        process = 'process: {}'.format(self.exercise.type)
        return ' / '.join([key, fullname, discipline, process])

    @property
    def type(self):
        return self.exercise.type

    def samelecturers(self, other):
        return self.lecturer.id == other.lecturer.id

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
    def __init__(self, weight_estimate=lambda x: 0):
        super().__init__()
        self.weight_estimate = weight_estimate
        lecturer_hours = get_lecturer_hours()
        room_domains = get_room_domains()
        group_disc = get_group_disciplines()
        for lecturer in sorted(lecturer_hours):
            subj_set = lecturer_hours[lecturer]
            for subj in subj_set:
                n = int(subj.hours) # subj = exercise
                while n > 0:
                    possible_rooms = set(room_domains[subj])
                    # same name are equal (for now)
                    listeners = {g for g, s in group_disc.items()
                                 if subj.name in [t[1] for t in s]} # FIXME: list compr
                    #print(subj.name, subj.type, listeners)
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
        return self.weight_estimate(self.variables)

    def infer_assignment(self):
        return dict((Xi, Xi.curr_value) for Xi in self.variables
                    if Xi.isassigned())

    def display(self, assignment:dict = None, days:list = None, hours:list = None):
        a = assignment if assignment is not None else self.infer_assignment()
        if days:
            a = { x:a[x] for x in a if a[x][0].day in days }
        if hours:
            a = { x:a[x] for x in a if a[x][0].hour in hours }
        print(len(a)); print_dictionary(a)


def weight(vars):
    if any(v for v in vars if v.isunassigned()): return INFINITY
    for v in vars:
        v.weight = 0
        timeslot, room = v.curr_value[0], v.curr_value[1]
        if timeslot.day == 'sat': v.weight += 10
        if timeslot.hour > 4: v.weight += 10
        if room.size > 40: v.weight += 5
        if v.lecturer.lastname == 'Кузнецов' and timeslot.day in ['mon','sat']: v.weight += 100
    grouped_by_day = [[v for v in vars if v.curr_value[0].day == day] for day in WEEK]
    for group in grouped_by_day:
        keyfunc = lambda x: getattr(x, 'exercise').name
        grouped_by_exercise, acc = [], []
        group = sorted(group, key=keyfunc)
        for _, g in itertools.groupby(group, key=keyfunc):
            grouped_by_exercise.append(list(g))
        exercises = map(len, grouped_by_exercise)
        day_load = [g for n, g in zip(exercises, grouped_by_exercise) if n >= 3]
        for item in day_load:
            acc += item
        for var in acc:
            var.weight += 40
    return bounded_sum(v.weight for v in vars)


def max_day_load(assignment):
    pairs = [[v.curr_value[0].hour for v in assignment
             if v.curr_value[0].day == day] for day in WEEK]
    return max(map(max, filter(lambda x: len(x), pairs)))


def combined_local_search(csp, max_steps=2000):
    def argmin_conflicts(var):
        return argmin(lambda x: csp.conflicts(var, x),
                      var.curr_domain, random.choice)

    def most_weight_variable(vars):
        from operator import itemgetter
        csp.weight_estimate(vars)
        return max(vars, key=lambda x: getattr(x, 'weight'))

    #for var in csp.variables:
    #    var.assign(argmin_conflicts(var))
    BacktrackingSearch(csp, select_unassigned_variable=random_unassigned_variable)
    for v in csp.variables: v.curr_domain = v.init_domain
    best_value, best_assignment = INFINITY, csp.infer_assignment()
    tabu, timestep, time_limit = [], 0, 20
    for _ in range(max_steps):
        vars = [v for v in csp.variables if v not in tabu]
        # print(len(csp.variables), len(tabu), len(vars))
        X = most_weight_variable(vars)
        a = argmin_conflicts(X) # FIXME?: возвращать список значений, а уже из него выбирать в соответствии с весом
        X.assign(a)
        violations = csp.violation_list()
        for Y in violations: Y.unassign()
        if not violations:
            estimate = csp.preferences()
            if estimate < best_value:
                # print(estimate)
                best_value, best_assignment = estimate, csp.infer_assignment()
        #for Y in violations: Y.unassign()
        if X.isassigned(): tabu.append(X)
        timestep += 1
        if timestep == time_limit:
            timestep = 0
            if tabu: tabu = tabu[:1]
    return best_assignment


def selection(population, fn):
    if random.random() <= 0.1:
        return random.choice(population)
    return max(population, key=fn)


def crossingover(csp, X, Y):
    n = len(X)
    while True:
        partition = random.randint(n/2, 2*n/3)
        csp.variables = X.variables[:partition] + Y.variables[partition:]
        if min_conflicts(csp, max_steps=1000) is not None:
            return csp.variables


def mutate(csp, child:dict):
    keys = list(child.keys())
    k = random.choice(keys)
    var = child[k]
    var.assign(random.choice(var.curr_domain))
    csp.variables = child
    child[var] = var.curr_value
    return child


def GA(csp, population, selection, crossingover, mutate, fitness, max_steps=5000):
    n, p = len(population), 0.01
    for _ in range(max_steps):
        new_population = {}
        for _ in range(n):
            X = selection(population, fitness)
            Y = selection(population, fitness)
            child = crossingover(csp, X, Y)
            if random.random() < p:
                child = mutate(child)
            new_population.add(child)
        population = new_population
    best = max(population, key=fitness)
    return best


def assign_groups(csp):
    # Необходимо распределить группы по переменным, т.е. по сути сократить множество
    # listeners каждой переменной до одного элемента. При этом, необходимо каждого
    # слушателя назначить единожды, а значит, придется группировать переменные по лекторам
    # и по полученным группам проходить в цикле, назначая и попутно вычеркивая группы (с этим проблема)
       

    return
    result = {}
    for lecturer, grouper in itertools.groupby(csp.variables, key=lambda x: getattr(x, 'lecturer')):
        #print(lecturer, end=': ')
        #for v in grouper: print(v.listeners, end=' ')
        #print('')
        vars = sorted(list(grouper), key=lambda x: getattr(x, 'count'))
        old_count = 1
        while vars:
            v = vars.pop()
            possible_listeners = list(v.listeners)
            print(v, v.listeners)
            real_listener = random.choice(possible_listeners)
            v.listeners = real_listener
            if v.count <= old_count:
                for var in vars:
                    var.listeners = var.listeners.difference({real_listener})
                old_count = v.count
            result[v] = real_listener
    print_dictionary(result)
    pass

if __name__ == '__main__':
    ttp = TimetablePlanner2(weight_estimate=weight)
    ttp.setup_constraints()
    #BacktrackingSearch(ttp)
    a = combined_local_search(ttp, max_steps=500); print(len(ttp.assignment))
    #for day in WEEK:
    #    print_dictionary({ x:a[x] for x in a if a[x][0].day == day })
    #    print('-'*80)
    assign_groups(ttp)

    easy1 = '..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3..'
    s = Sudoku(easy1)

    australia = MapColoring(list('RGB'), {
        'SA':  ['WA', 'NT', 'Q', 'NSW', 'V'],
        'WA':  ['SA', 'NT'],
        'Q' :  ['SA', 'NT', 'NSW'],
        'NT':  ['WA', 'Q'],
        'NSW': ['Q', 'V'],
        'V':   ['SA', 'NSW'],
        'T':   []
    })