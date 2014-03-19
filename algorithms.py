import random
import itertools

from utils import *
from csp import Variable, CSP


def AC3(csp: CSP, queue=None) -> bool:
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


def argmin_conflicts(var: Variable, csp: CSP):
    """ Возвращает значение из домена переменной var, которое, будучи присвоенным этой переменной,
        приводит к наименьшему количеству нарушенных ограничений в csp.
    """
    return argmin(lambda x: csp.conflicts(var, x),
                  var.curr_domain, random.choice)


def weighted_argmin_conflicts(var: Variable, csp: CSP):
    """ Действует аналогично argmin_conflicts, но после выбора множества наименее конфликтных
        значений, производит среди них выбор в соответствии с эвристической функцией из csp.
    """
    def f(x):
        var.assign(x)
        return csp.preferences()

    args = argmin(lambda x: csp.conflicts(var, x), var.curr_domain)
    random.shuffle(args)
    return argmin(f, args[:5], random.choice)


## Стратегии выбора переменных
def first_unassigned_variable(csp: CSP) -> Variable:
    """ Выбирает первую найденную неприсвоенную переменную. """
    assert([v for v in csp.variables if not v.isassigned()]) # FIXME: will be removed
    for v in csp.variables:
        if not v.isassigned(): return v

def random_unassigned_variable(csp: CSP) -> Variable:
    """ Выбирает случайную неприсвоенную переменную. """
    return random.choice([v for v in csp.variables if not v.isassigned()])

def minimum_remaining_value(csp: CSP):
    pass

def most_weight_variable(csp: CSP) -> int:
    """ Возвращает переменную с максимальным значением атрибута weight. """
    return max(csp.variables, key=lambda x: getattr(x, 'weight'))


## Стратегии просмотра значений переменных
def least_constraining_value(var: Variable, csp: CSP) -> list:
    """ Упорядочивает значения в соответствии с количеством конфликтов, ими вызываемых. """
    return sorted(var.curr_domain,
                  key=lambda Vi: csp.conflicts(var, Vi))


def forward_checking(X: Variable, csp: CSP, removed: list) -> bool:
    """ Наиболее простой способ распространения ограничений. Каждый раз при присваивании
        переменной X, функция поддерживает совместимость дуг для нее: у каждой неприсвоенной
        переменной Y, соединенной ограничением с X, из домена исключаются значения, несовместные
        со значением переменной Y. Если у какой либо из этих переменных домен оказывается пустым,
        функция сообщает об этом возвратом ложного значения.
        [AIMA, 3rd, p.217]
    """
    for Y in X.neighbors:
        if not Y.isassigned():
            for y in Y.curr_domain:
                if not csp.constraints(X, X.curr_value, Y, y):
                    Y.curr_domain.remove(y) # удалить конфликтные значения
                    removed.append((Y, y))
            if not Y.curr_domain: # домен пуст, присваивание недопустимо
                return False
    return True


def weight(vars):
    """ Эвристическая функция оценки качества найденного решения. В начале каждая переменная
        оценивается отдельно от всех остальных, а затем её текущее значение рассматривается в
        общем контексте. Суммарный вес решения состоит из суммы весов всех входящих в него пере-
        менных. Чем больше вес, тем больше предпочтений не выполнено.
    """
    for v in vars:
        v.weight = sum(p.check(v) for p in v.preferences)
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

        # keyfunc = lambda x: getattr(x, 'lecturer_name')
        # grouped_by_exercise, acc = [], []
        # group = sorted(group, key=keyfunc)
        # for _, g in itertools.groupby(group, key=keyfunc):
        #     grouped_by_exercise.append(list(g))
        #
        # input('...')
    return bounded_sum(v.weight for v in vars)


## Алгоритмы поиска
def backtracking_search(csp: CSP,
                        select_unassigned_variable=first_unassigned_variable,
                        order_domain_values=least_constraining_value,
                        inference=forward_checking):
    """ Поиск с возвратами для решения CSP. Правило выбора переменной, упорядочивание доменов
        и распространение ограничений могут регулироваться.
        [AIMA, 3rd, p.214]
    """
    def Backtrack():
        if len(csp.assignment) == len(csp.variables):
            return True # все переменные присвоены
        var = select_unassigned_variable(csp)
        for value in order_domain_values(var, csp):
            if not csp.conflicts(var, value):
                var.assign(value)
                removed = [(var, x) for x in var.curr_domain if x != value]
                var.curr_domain = [value]
                # распространение ограничений может быть пропущено, т.е. можно
                # определить inference = lambda _,_,_: return True
                if inference(var, csp, removed):
                    result = Backtrack()
                    if result:
                        return True
                csp.restore(removed)
            var.unassign()
        return False # полное присваивание не найдено

    return Backtrack()


def min_conflicts(csp: CSP, max_steps=2000):
    """ Локальный поиск, основанный на минимизации количества конфликтов. Возвращает первое
        найденное решение, удовлетворяющее всем строгим ограничениям.
    """
    # Изначальное присваивание (может нарушать ограничения)
    for var in csp.variables:
        var.assign(argmin_conflicts(var, csp))
    # Поиск проходит до тех пор, пока не будет найдено решение или не будет исчерпан лимит попыток
    for i in range(max_steps):
        violations = csp.violation_list()
        if not violations: # Все ограничения удовлетворены
            return csp.infer_assignment()
        var = random.choice(violations)
        val = argmin_conflicts(var, csp)
        var.assign(val)
    return None


def weighted_search(csp: CSP,
                    select_variable=most_weight_variable,
                    select_domain_value=weighted_argmin_conflicts,
                    max_steps=1000,
                    filename:str = 'log'):
    """ Локальный поиск с использованием весовой функции в качестве эвристики выбора значения
        очередной переменной. Используется для тестирования реализованных алгоритмов и записывает в
        файл данные для построения графика зависимости значения веса решения от номера итерации.
    """
    f = open(filename, 'w')
    if backtracking_search(csp): # Изначальное присваивание
        csp.restoreall() # Восстановление исходных доменов
    else:
        return (INFINITY, None) # Не удалось удовлетворить строгие ограничения
    best_value, best_assignment = csp.preferences(), csp.infer_assignment()
    for i in range(max_steps):
        X = select_variable(csp)
        X.assign(select_domain_value(X, csp))
        violations = csp.violation_list() # Список нарушающих строгие ограничения переменных
        estimate = csp.preferences()
        if not violations:
            if estimate < best_value:
                f.write('{} {}\n'.format(i, estimate))
                best_value, best_assignment = estimate, csp.infer_assignment()
            else:
                f.write('{} {}\n'.format(i, best_value))
        for Y in violations: Y.unassign()
    return (best_value, best_assignment)