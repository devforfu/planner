import copy, random, itertools
import xml.etree.ElementTree as ET
from collections import namedtuple
from dbconnect import UniversityDatabase, Teacher, Discipline, Room
from utils import WEEK


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


TimeSlot = namedtuple('TimeSlot', ['day', 'hour']) # timeslot in schedule


class ScheduleVariable(Variable): # TODO: исправить комментарий к классу
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

    def __init__(self, teacher, discipline, process_type, listeners,
                 possible_rooms, is_lecture, num=1, preferences=None):
        super().__init__(domain=[(t, r) for t in ScheduleVariable.timeslots
                                        for r in possible_rooms])
        self.__teacher = teacher
        self.__discipline = discipline
        self.__process_type = process_type
        self.__listeners = listeners
        self.__possible_rooms = possible_rooms
        self.__is_lecture = is_lecture
        self.__num = num
        self.__key = (self.__teacher.id,  self.__discipline.id,
                      self.__process_type, int(is_lecture))
        self.preferences = [] if preferences is None else preferences
        self.weight = None

    @property
    def type(self):
        return self.__process_type

    @property
    def islecture(self):
        return self.__is_lecture

    @property
    def teacher(self):
        return self.__teacher

    @property
    def discipline(self):
        return self.__discipline.name

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
        discipline = self.__discipline
        process = 'process: {}'.format(self.__process_type)
        return ' / '.join([key, self.lecturer_name, self.discipline, process])


class Subgroup:
    NONE = 0
    A = 1
    B = 2


class Periodicity:
    NONE = 0
    NOMINATOR = 1
    DENOMINATOR = 2


class SubgroupMixIn:
    def __init__(self, subgroup=Subgroup.A):
        self.__subgroup = subgroup

    @property
    def subgroup(self):
        return self.__subgroup

    @subgroup.setter
    def subgroup(self, value):
        self.__subgroup = value

    def subgroupname(self):
        return 'Подгруппа А' if self.subgroup == Subgroup.A else 'Подгруппа Б'

    def samesubgroups(self, other):
        return self.subgroup == other.subgroup


class PeriodicityMixIn:
    def __init__(self, periodicity=Periodicity.NOMINATOR):
        self.__periodicity = periodicity

    @property
    def periodicity(self):
        return self.__periodicity

    @periodicity.setter
    def periodicity(self, value):
        self.__periodicity = value

    def periodicityname(self):
        return 'Числитель' if self.periodicity == Periodicity.NOMINATOR else 'Знаменатель'

    def sameperiodicities(self, other):
        return self.periodicity == other.periodicity


class PeriodicVariable(PeriodicityMixIn, ScheduleVariable):
    def __init__(self, periodicity=Periodicity.NOMINATOR, **kwargs):
        PeriodicityMixIn.__init__(self, periodicity)
        ScheduleVariable.__init__(self, **kwargs)

    def __str__(self):
        return ScheduleVariable.__str__(self) + '/' + self.periodicityname()


class SubgroupVariable(SubgroupMixIn, ScheduleVariable):
    def __init__(self, subgroup=Subgroup.A, **kwargs):
        SubgroupMixIn.__init__(self, subgroup)
        ScheduleVariable.__init__(self, **kwargs)

    def __str__(self):
        return ScheduleVariable.__str__(self) + '/' + self.subgroupname()


class PeriodicSubgroupVariable(PeriodicityMixIn, SubgroupMixIn, ScheduleVariable):
    def __init__(self, periodicity=Periodicity.NOMINATOR, subgroup=Subgroup.A, **kwargs):
        PeriodicityMixIn.__init__(self, periodicity)
        SubgroupMixIn.__init__(self, subgroup)
        ScheduleVariable.__init__(self, **kwargs)

    def __str__(self):
        return '{}/{}/{}'.format(ScheduleVariable.__str__(self),
                                 self.periodicityname(), self.subgroupname())


class HalfPerWeekVariable(ScheduleVariable):
    """ Класс для реализации поддержки планирования занятий, которые проводятся один раз в две
        недели, т.е. по числителю или знаменателю.
    """
    def __init__(self, teacher, discipline, process_type, listeners,
                 possible_rooms, is_lecture, num=1, denominator=False, preferences=None):
        super().__init__(teacher, discipline, process_type,
                         listeners, possible_rooms, is_lecture, num, preferences)
        self.denominator = denominator


class VariableCreator:
    def __init__(self, db: UniversityDatabase):
        self.database = db
        self.teachers_load = db.get_teachers_load() # распределение нагрузки по занятиям
        self.discipline_institutes = db.get_discipline_institutes()
        self.discipline_teacher = db.get_discipline_teachers()
        self.discipline_group = db.get_groups_for_discipline()

    def _calc_hours_per_week(self, overall: int, semester_length: int = 16):
        per_week, rest = divmod(overall, semester_length)
        return (per_week, not bool(rest))

    def _merge_variables(self, variables):
        def keyfunc(v):
            return v.teacher, v.discipline, v.islecture

        lecture_vars = set(v for v in variables if v.islecture) # переменные для лекционных занятий
        lecture_vars = sorted(lecture_vars, key=keyfunc)
        other_vars = variables.difference(lecture_vars) # все переменные, кроме лекционных
        same_eliminated = set()
        for (key, group) in itertools.groupby(lecture_vars, key=keyfunc): # слияние переменных
            group = list(group)
            v = group[0]
            if len(group) > 1: # несколько групп должны прослушать одну и ту же лекцию
                for item in group[1:]:
                    v.listeners.update(item.listeners)
                same_eliminated.add(v)
            else:
                same_eliminated.update(group)
        variables = same_eliminated.union(other_vars)
        for v in variables:
            print(v, v.listeners)
        print('='*80)
        return variables

    def _get_free_teacher(self, possible_teachers):
        free_teachers = [l for l in possible_teachers if self.teachers_load[l] > 0]
        teacher = random.choice(free_teachers)
        self.teachers_load[teacher] -= 1
        return teacher

    def create_variables(self):
        AUDITORIUM_TYPE = 1
        variables = set()
        # формирование переменных для CSP (по одной на каждую пару)
        for (discipline, possible_teachers) in self.discipline_teacher.items():
            institute = self.discipline_institutes[discipline]
            root = ET.fromstring(discipline.plan)
            n = 1
            for ex in root.findall('exercise'):
                hours = int(ex.attrib['hours'])
                type = int(ex.attrib['process_type_id'])
                is_practise = int(ex.attrib.get('is_practise', 0))
                per_week, every_week = self._calc_hours_per_week(hours)
                teacher = self._get_free_teacher(possible_teachers)
                listeners = self.discipline_group[discipline]
                overall_students_number = sum(l.size for l in listeners)
                # отсечь аудитории, в которых невозможно проводить занятие
                possible_rooms = set(r for r in
                                     self.database.get_rooms_for_institute(institute, type))
                is_lecture = lambda type: type == AUDITORIUM_TYPE and not is_practise
                attrib = dict(teacher=teacher, discipline=discipline,
                              process_type=type, listeners=copy.deepcopy(listeners),
                              possible_rooms=possible_rooms, is_lecture=is_lecture(type))
                for _ in range(per_week): # по одной переменной на каждое занятие
                    variables.add(ScheduleVariable(num=n, **attrib))
                    n += 1
                if not every_week: # плюс одна для занятия, проводимого один раз в две недели
                    variables.add(PeriodicVariable(num=n, **attrib))
        return self._merge_variables(variables)


if __name__ == '__main__':
    database = UniversityDatabase()
    creator = VariableCreator(database)
    variables = creator.create_variables()
