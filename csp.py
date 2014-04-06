import itertools, re, random
from functools import reduce

from dbconnect import *
from utils import WEEK, INFINITY, print_dictionary

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
        for _ in range(random.randint(2, 4)):
            new_domain.add(random.choice(rooms))
        domains[exercise].update(new_domain)
    return domains


class Variable:
    """ Базовый класс для представления переменной в задачах удовлетворения ограничений
        (CSP - constraint satisfaction problems). Предоставляет интерфейс, используемый в
        дальнейшем алгоритмами поиска.

        Атрибуты:
            init_domain: Возвращает исходное множество допустимых значений (readonly).
            curr_value: Текущее значение переменной (readonly).
            curr_domain: Возвращает текущее множество допустимых значений.
            neighbors: Список переменных, которые связаны с данной ограничениями.
    """
    def __init__(self, domain:list, neighbors=None):
        self.__init_domain = domain
        self.__curr_value = None
        self.curr_domain = domain
        self.neighbors = [] if neighbors is None else neighbors

    @property
    def init_domain(self):
        return self.__init_domain

    @property
    def curr_value(self):
        return self.__curr_value

    def assign(self, value):
        assert(value in self.curr_domain)
        self.__curr_value = value

    def unassign(self):
        self.__curr_value = None

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

        Атрибуты:
            variables: Список всех переменных, используемых в задаче.
            assignment: Список переменных, которым присвоено какое-либо значение. Не храниться
                      непосредственно и вычисляется при необходимости.
    """
    def __init__(self):
        self.__variables = []

    @property
    def variables(self):
        return self.__variables

    @variables.setter
    def variables(self, container):
        self.__variables = container

    @property
    def assignment(self):
        return [v for v in self.variables if v.isassigned()]

    def add_variable(self, var: Variable):
        self.__variables.append(var)

    def setup_constraints(self):
        """ Реализуется при решении конкретных задач """
        pass

    def setup_preferences(self):
        """ Реализуется при решении конкретных задач """
        pass

    def infer_assignment(self):
        return dict((str(Xi), Xi.curr_domain) for Xi in self.variables)

    def constraints(self, var1, value1, var2, value2):
        """ Производит проверку выполнения огрничений, связывающих переменные var 1 и var2,
            если им будут присвоены значения value1 и value2 соответственно. Должен быть переопре-
            делен при решении конкретных задач. Предполагается, что все строгие ограничения,
            используемые в задаче, являются бинарными.
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
    """ Класс используется в CSP, связанной с планированием расписания. Доменом каждой пере-
        менной является список кортежей вида (timeslot, room), где timeslot - именованный кортеж,
        хранящий день недели и номер пары, room - аудитория, в которой проходит занятие.Помимо
        домена и текущего значения каждая переменная хранит дополнительные сведения, исполь-
        зуемые для формирования расписания.

        Атрибуты:
            lecturer: Именованный кортеж с данными преподавателя (readonly).
            exercise: Именованный кортеж со сведениями о проводимом занятии (readonly).
            listeners: Множество групп, которые содержат занятие exercise в своем учебном
                плане. Предполагается использование множества при планировании потоковых
                лекций (readonly).
            num: Номер занятия.
            key: Идентификатор переменной.
            preferences: Список нестрогих ограничений (предпочтений).
            weight: Вес переменной; чем больше значение, тем больше предпочтений нарушено.
    """
    # все возможные значения времени проведения занятий (день - номер пары)
    # на данный момент предполагается максимум 6 учебных дней и 6 пар в день
    timeslots = [TimeSlot(d, h) for d in WEEK for h in range(1, 7)]

    def __init__(self, teacher, exercise, listeners, possible_rooms, num=1, preferences=None):
        super().__init__(domain=[(t, r) for t in ScheduleVariable.timeslots
                                        for r in possible_rooms])
        self.__teacher = teacher
        self.__exercise = exercise
        self.__listeners = listeners
        self.__possible_rooms = possible_rooms
        self.__num = num
        self.__key = (self.teacher.id, self.exercise.id, num)
        self.preferences = [] if preferences is None else preferences
        self.weight = None

    @property
    def type(self):
        return self.__exercise.type

    @property
    def teacher(self):
        return self.__teacher

    @property
    def exercise(self):
        return self.__exercise

    @property
    def discipline(self):
        return self.__exercise.name

    @property
    def count(self):
        return self.__num

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
    def lecturer_name(self):
        return ' '.join([
            self.__teacher.firstname,
            self.__teacher.middlename,
            self.__teacher.lastname])

    @property
    def listeners(self):
        return self.__listeners

    @property
    def possible_rooms(self):
        return self.__possible_rooms

    def samelecturers(self, other):
        """ Проверяет, относятся ли переменные к нагрузке одного и того же преподавателя """
        return self.teacher.id == other.teacher.id

    def samerooms(self, other):
        """ Проверяет, имеются ли совпадения в списках допустимых аудиторий у двух переменных """
        return self.__possible_rooms.intersection(other.possible_rooms)

    def samelisteners(self, other):
        """ Возвращает пересечение множеств listeners двух переменных """
        return self.listeners.intersection(other.listeners)

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        key = str(self.key)
        discipline = self.exercise.name
        process = 'process: {}'.format(self.exercise.type)
        return ' / '.join([key, self.lecturer_name, discipline, process])


class Preference:
    """ Класс, используемый для представления нестрогих ограничений, накладываемых на значения
        переменных. Нарушением предпочтения считается принятие переменнойзначения, не содержащегося
        в отведенном для нее домене в словаре conditions.
    """
    def __init__(self, conditions: dict, penalty: int):
        self.conditions = conditions
        self.penalty = penalty
        self.string = 'if '
        # Формирование строки, отображаемой при передаче объектов класса в поток вывода
        for attrname, domain in self.conditions.items():
            self.string += ' (attribute {} in domain {})\nand'.format(attrname, domain)
        self.string = self.string[:-3] + 'then penalty={}'.format(penalty)

    def __str__(self):
        return self.string

    def check(self, variable):
        """ Проверяет удовлетворение предпочтений переменной variable. При этом, в ходе проверки
            производится сопоставление отдельных элементов кортежа (день, час, аудитория),
            являющегося текущим значением переменной, с заданными для них доменами.
        """
        if not variable.isassigned():
            return INFINITY
        for attrname, domain in self.conditions.items():
            if not (getattr(variable, attrname) in domain):
                return self.penalty
        return 0


class TimetablePlanner2(CSP):
    """ Класс планировщика расписаний как один из случаев решения CSP. На данном этапе не учитывает
        многие реальные факторы. Использует глобальные функции для получения значений из БД
        приложения. В дальнейшем конструктор класса будет преобразован.
    """
    def __init__(self, weight_estimate=lambda x: 0):
        super().__init__()
        self.weight_estimate = weight_estimate
        # Получение вымышленных данных из БД приложения
        lecturer_hours = get_lecturer_hours()
        room_domains = get_room_domains()
        group_disc = get_group_disciplines()
        # Формирование списка переменных, используемых при решении задачи планирования
        for lecturer in sorted(lecturer_hours):
            exercises_set = lecturer_hours[lecturer]
            for ex in exercises_set:
                for n in range(int(ex.hours)): # По одной переменной на каждое занятие
                    possible_rooms = set(room_domains[ex])
                    listeners = {g for g, s in group_disc.items()
                                 if ex.did in [t[0] for t in s]}
                    self.add_variable(ScheduleVariable(lecturer, ex, listeners, possible_rooms, n+1))

    def setup_constraints(self):
        """ Устанавливает строгие ограничения на значения переменных """
        for Xi in self.variables:
            for Xj in self.variables:
                if Xi is Xj: continue # связывать переменную с собой же не нужно
                if Xi.samelecturers(Xj) or Xi.samerooms(Xj) or Xi.samelisteners(Xj):
                    Xi.neighbors.append(Xj)

    def setup_preferences(self):
        """ Устанавливает предпочтения для значений переменных. В настоящий момент функция содержит
            вручную закодированные ограничения. В дальнейшем планируется организация управления
            предпочтениями на основе данных пользовательского ввода.
        """
        # Предпочтения (нестрогие ограничения) и штрафы за нарушения
        p1 = Preference(dict(day=WEEK[:5]), 10) # больше занятий в будни
        p2 = Preference(dict(hour=[1,2,3,4]), 75) # больше занятий 1-4 парой
        # Личные предпочтения преподавателей
        p4 = Preference(dict(day=['tue', 'thu', 'fri']), 50) # предпочтение занятиям во ВТ, ЧТ и ПТ
        p5 = Preference(dict(day=['fri', 'sat']), 50)  # предпочтение занятиям в ПТ и СБ
        for v in self.variables:
            v.preferences.extend([p1, p2])
            if v.lecturer_name == 'К. Н. Стрельцов':
                v.preferences.append(p4)
            elif v.lecturer_name == 'П. К. Сидоров':
                v.preferences.append(p5)

    def constraints(self, A, a, B, b):
        """ Проверяет, не нарушают ли присваивания A=a и B=b какое-либо из ограничений
            (все ограничения - бинарные).
        """
        if A is B: return True
        aTime, aRoom = a
        bTime, bRoom = b
        if aTime == bTime:
            if A.samelecturers(B):
                return False
            if A.samelisteners(B):
                return False
            if A.samerooms(B) and aRoom == bRoom:
                return False
        return True

    def preferences(self):
        """ Возвращает вес найденного решения. Чем меньше вес, тем меньшее количество нестрогих
            ограничений (предпочтений) было нарушено, и соответственно, тем "оптимальнее"
            (в смысле, определяемом объектами класса Preference и функцией weight_estimate) решение.
        """
        for v in self.variables:
            v.weight = sum(p.check(v) for p in v.preferences)
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


def selftest():
    print_dictionary(get_group_disciplines())
    # print_dictionary(get_lecturer_hours())
    print_dictionary(get_room_domains())

if __name__ == '__main__':
    selftest()