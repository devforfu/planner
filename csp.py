import itertools, re, random
from functools import reduce

from dbconnect import *
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
    """ Базовый класс для представления переменной в задачах удовлетворения ограничений
        (CSP - constraint satisfaction problems). Предоставляет интерфейс, используемый в
        дальнейшем во всех алгоритмах поиска и не используется непосредственно.

            init_domain - возвращает исходное множество допустимых значений (readonly)
            curr_domain - возвращает текущее множество допустимых значений
            neighbors   - список переменных, которые связаны с данной ограничениями
            curr_value  - текущее значение переменной
    """
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

    def __eq__(self, other):
        return self.curr_value == other.curr_value

    def __hash__(self):
        return id(self)

    def __str__(self):
        return self.name


class CSP:
    """ Базовый класс для представления задач удовлетворения ограничений, не используется
        непосредственно. Для решения конкретных задач необходимо произвести наследование от
        данного класса и определить все необходимые методы.

            variables  - список всех переменных, используемых в задаче
            assignment - список переменных, которым присвоено какое-либо значение
    """
    def __init__(self):
        self.__variables = []

    @property
    def variables(self):
        return self.__variables

    @variables.setter
    def variables(self, val:list):
        self.__variables = val

    @property
    def assignment(self):
        return [v for v in self.variables if v.isassigned()]

    def add_variable(self, var: Variable):
        """ Добавляет переменную к списку """
        self.__variables.append(var)

    def setup_constraints(self):
        """ Реализуется, в случае необходимости, при решении конкретных задач """
        pass

    def setup_preferences(self):
        """ Реализуется, в случае необходимости, при решении конкретных задач """
        pass

    def infer_assignment(self):
        """ Возвращает словарь из переменных и их текущих доменов """
        return dict((str(Xi), Xi.curr_domain) for Xi in self.variables)

    def constraints(self, var1, value1, var2, value2):
        """ Производит проверку выполнения огрничений, связывающих переменные var 1 и var2,
            если им будут присвоены значения value1 и value2 соответственно. Предполагается,
            что все строгие ограничения, используемые в задаче, являются бинарными.
        """
        return var1 == var2 or value1 != value2

    def preferences(self):
        """ Возвращает вес текущего решения. По умолчанию считается, что присутствуют только
            строгие ограничения и если ни одно из них не нарушено, то вес решения принимается
            равным нулю, иначе - бесконечности.
        """
        return (0 if not self.violation_list()
                     and len(self.assignment) == len(self.variables)
                  else INFINITY)

    def restore(self, removed:list):
        """ Восстанавливает значения, ранее исключенные из доменов переменных.
            Список removed содержит кортежи вида (A, a), где A - переменная, a - значение
            из её изначального домена.
        """
        for var, value in removed:
            var.curr_domain.append(value)

    def restoreall(self):
        """ Приводит все домены переменных в CSP в исходное состояние """
        for v in self.variables:
            v.curr_domain = v.init_domain

    def conflicts(self, X: Variable, possible_value):
        """ Возвращает количество нарушенных ограничений, если переменной X будет
            присвоено значение possible_value.
        """
        conflict = (lambda Y: Y.isassigned()
                              and not self.constraints(X, possible_value, Y, Y.curr_value))
        return len(list(filter(conflict, X.neighbors)))

    def violation_list(self):
        """ Возвращает список переменных, значения которых нарушают имеющиеся строгие ограничения """
        return [var for var in self.variables
                if var.isassigned() and self.conflicts(var, var.curr_value) > 0]

    def display(self):
        return self.__str__()


class ScheduleVariable(Variable):
    """ Переменная, используемая в CSP, связанной с планированием расписания. Доменом каждой пере-
        менной является список кортежей вида (timeslot, room), где timeslot - именованный кортеж,
        хранящий день недели и номер пары, room - номер аудитории, в которой проходит занятие.
        Помимо домена и текущего значения каждая переменная хранит дополнительные сведения, исполь-
        зуемые для формирования расписания.

            lecturer  - свойство, хранящее именованный кортеж с данными преподавателя
            exercise  - свойство, хранящее сведения о проводимом занятии
            listeners - хранит множество групп, которые содержат занятие exercise в своем
                        учебном плане; планируется использовать данное множество для обработки
                        ситуации, при которой несколько групп должны изучить один и тот же
                        предмет, преподаваемый одним преподавателем
            count     - номер, используемый для различия переменных в том случае, если
                        занятие проводится более одного раза в неделю


    """
    # все возможные значения времени проведения занятий (день - номер пары)
    # на данный момент предполагается максимум 6 учебных дней и 6 пар в день
    timeslots = [TimeSlot(d, h) for d in WEEK for h in range(1, 7)]

    def __init__(self, lecturer, exercise, listeners, possible_rooms, count = 0):
        super().__init__(domain=[(t, r) for t in ScheduleVariable.timeslots
                                        for r in possible_rooms])
        self.__lecturer = lecturer
        self.__exercise = exercise
        self.__count = count
        self.__key = (self.lecturer.id, self.exercise.id, count)
        self.__listeners = listeners
        self.possible_rooms = possible_rooms
        self.weight = None

    @property
    def type(self):
        return self.__exercise.type

    @property
    def lecturer(self):
        return self.__lecturer

    @property
    def exercise(self):
        return self.__exercise

    @property
    def discipline(self):
        return self.__exercise.name

    @property
    def count(self):
        return self.__count

    @property
    def key(self):
        return self.__key

    @property
    def day(self):
        return self.curr_value[0].day

    @property
    def hour(self):
        return self.curr_value[0].hour

    @property
    def room(self):
        return self.curr_value[1]

    @property
    def first_name(self):
        return self.__lecturer.firstname

    @property
    def middle_name(self):
        return self.__lecturer.middlename

    @property
    def last_name(self):
        return self.__lecturer.lastname

    @property
    def listeners(self):
        return self.__listeners

    def samelecturers(self, other):
        """ Проверяет, относятся ли переменные к нагрузке одного и того же преподавателя """
        return self.lecturer.id == other.lecturer.id

    def samerooms(self, other):
        """ Проверяет, имеются ли совпадения в списках допустимых аудиторий у двух переменных """
        return self.possible_rooms.intersection(other.possible_rooms)

    def samelisteners(self, other):
        """ Возвращает пересечение множеств listeners двух переменных """
        return self.listeners.intersection(other.listeners)

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


class Preference:
    def __init__(self, variable, conditions, penalty):
        self.__variable = variable
        self.__conditions = conditions
        self.__penalty = penalty

    @property
    def conditions(self):
        return self.__conditions

    @property
    def penalty(self):
        return self.__penalty

    @property
    def variable(self):
        return self.__variable

    def isfired(self):
        for attrname, domain in self.conditions:
            if not (getattr(self.__variable, attrname) in domain):
                return False
        return True

class TimetablePlanner2(CSP):
    """ Класс планировщика расписаний как один из случаев решения CSP. """
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
                                 if subj.did in [t[0] for t in s]}
                                 #if (subj.type == 1 and subj.name in [t[1] for t in s])
                                 #or (subj.type == 3 and subj.did  in [t[0] for t in s])} # FIXME: list compr
                    #print(subj.name, subj.type, listeners)
                    self.add_variable(ScheduleVariable(lecturer, subj, listeners, possible_rooms, n))
                    n -= 1
        # for v in self.variables: print(v, v.listeners)

    def setup_constraints(self):
        """ Устанавливает строгие ограничения для переменных """
        for Xi in self.variables:
            for Xj in self.variables:
                if Xi is Xj: continue # связывать переменную с собой же не нужно
                if Xi.samelecturers(Xj) or Xi.samerooms(Xj) or Xi.samelisteners(Xj):
                    Xi.neighbors.append(Xj) # совпадают преподаватель, аудитории или группы

    def setup_preferences(self):
        """ Рассчитывает вес полученного присваивания.
        >>> p1 = Preference([
        ...     dict(property1=domain1, property2=domain21),
        ...     dict(property3=domain3),
        ...     dict(property2=domain22)
        ...])
        >>> variable.add_preference(p1)
        """
        pass

    def constraints(self, A, a, B, b):
        """ Проверяет, не нарушают ли присваивания A=a и B=b какое-либо из ограничений
            (все ограничения - бинарные).
        """
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
        """ Возвращает вес найденного решения. Чем меньше вес, тем меньшее количество нестрогих
            ограничений (предпочтений) было нарушено, и соответственно, тем "оптимальнее"
            (в смысле, определяемом функцией weight_estimate) решение.
        """
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
    """ Эвристическая функция оценки качества найденного решения. В начале каждая переменная
        оценивается отдельно от всех остальных, а затем её текущее значение рассматривается в
        общем контексте. Суммарный вес решения состоит из суммы весов всех входящих в него пере-
        менных. Чем больше вес, тем больше предпочтений не выполнено.
    """
    if any(v for v in vars if not v.isassigned()): return INFINITY
    for v in vars:
        v.weight = 0
        if v.day == 'sat': v.weight += 10
        if v.room.size > 40: v.weight += 10
        if v.hour == 6: v.weight += 50
        if v.hour > 3: v.weight += 25
        if v.last_name == 'Хомский' and v.day in ['mon','sat']: v.weight += 25
        if v.last_name == 'Сидоров' and v.day not in ['fri', 'sat']: v.weight += 25
    # формирование списка групп переменных, которым присвоен один и тот же день
    grouped_by_day = [[v for v in vars if v.day == day] for day in WEEK]
    # ограничение количества занятий в день по одному предмету
    for group in grouped_by_day:
        keyfunc = lambda x: getattr(x, 'discipline') # ф-ция для извлечения названия дисциплины
        grouped_by_exercise, acc = [], []
        group = sorted(group, key=keyfunc)
        for _, g in itertools.groupby(group, key=keyfunc): # группирование переменных по дисц.
            grouped_by_exercise.append(list(g))
        exercises = map(len, grouped_by_exercise) # получения списка с количеством занятий по дисц.
        day_load = [g for n, g in zip(exercises, grouped_by_exercise) if n >= 3]
        for item in day_load:
            acc += item
        for var in acc: # назначения веса при наличии более 3 занятий в день по некоторому предмету
            var.weight += 75
    return bounded_sum(v.weight for v in vars)


def assign_groups(assignment):
    return {v: (v.curr_value, v.listeners) for v in assignment}