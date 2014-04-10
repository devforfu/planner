import itertools, re, random
from functools import reduce

from variable import Variable, VariableCreator
from utils import WEEK, INFINITY, print_dictionary


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

    def check(self, variable: Variable):
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
    # FIXME: конструктор более неактуален. Планировщик в данный момент не функционирует.
    """ Класс планировщика расписаний как один из случаев решения CSP. На данном этапе не учитывает
        многие реальные факторы. Использует глобальные функции для получения значений из БД
        приложения. В дальнейшем конструктор класса будет преобразован.
    """
    def __init__(self, creator: VariableCreator, weight_estimate=lambda x: 0):
        super().__init__()
        self.weight_estimate = weight_estimate
        self.variables = list(creator.create_variables())
        # # Получение вымышленных данных из БД приложения
        # lecturer_hours = get_lecturer_hours()
        # room_domains = get_room_domains()
        # group_disc = get_group_disciplines()
        # # Формирование списка переменных, используемых при решении задачи планирования
        # for lecturer in sorted(lecturer_hours):
        #     exercises_set = lecturer_hours[lecturer]
        #     for ex in exercises_set:
        #         for n in range(int(ex.hours)): # По одной переменной на каждое занятие
        #             possible_rooms = set(room_domains[ex])
        #             listeners = {g for g, s in group_disc.items()
        #                          if ex.did in [t[0] for t in s]}
        #             self.add_variable(ScheduleVariable(lecturer, ex, listeners, possible_rooms, n+1))

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


if __name__ == '__main__':
    pass # selftest()