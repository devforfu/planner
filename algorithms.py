import random

from utils import *


def AC3(csp, queue=None):
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

## Стратегии выбора переменных
def first_unassigned_variable(csp):
    """ Выбирает первую найденную неприсвоенную переменную. """
    assert([v for v in csp.variables if not v.isassigned()]) # FIXME: will be removed
    for v in csp.variables:
        if not v.isassigned(): return v

def random_unassigned_variable(csp):
    """ Выбирает случайную неприсвоенную переменную. """
    return random.choice([v for v in csp.variables if not v.isassigned()])

def minimum_remaining_value(csp):
    pass

def most_weight_variable(vars):
    """ Возвращает переменную с максимальным значением атрибута weight. """
    return max(vars, key=lambda x: getattr(x, 'weight'))


## Стратегии просмотра значений переменных
def least_constraining_value(var, csp):
    """ Упорядочивает значения в соответствии с количеством конфликтов, ими вызываемых. """
    return sorted(var.curr_domain,
                  key=lambda Vi: csp.conflicts(var, Vi))


def forward_checking(X, csp, removed):
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
            if not Y.curr_domain:
                return False
    return True


## Алгоритмы поиска
def backtracking_search(csp,
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


def min_conflicts(csp, max_steps=10000):
    """ Локальный поиск, основанный на минимизации количества конфликтов """
    # Изначальное присваивание (может нарушать ограничения)
    if len(csp.assignment) != len(csp.variables):
        for var in csp.variables:
            var.assign(argmin_conflicts(var, csp))
    # Поиск проходит до тех пор, пока не будет найдено решение или не будет исчерпан лимит попыток
    for _ in range(max_steps):
        violations = csp.violation_list()
        if not violations: # все ограничения удовлетворены
            return csp.variables
        var = random.choice(violations)
        val = argmin_conflicts(var)
        var.assign(val)
    return None


def combined_local_search(csp,
                          select_variable=most_weight_variable,
                          select_domain_value=weighted_argmin_conflicts,
                          max_steps=2000,
                          attempt_limit=200,
                          filename:str = 'log'):
    #TODO: ввести ограничение на количество нерезультативных итераций и перезапускать поиск
    f = open(filename, 'w') if filename else None
    backtracking_search(csp)
    csp.restoreall() # восстановить исходные домены переменных
    attempt, best_value, best_assignment = 0, INFINITY, csp.infer_assignment()
    csp.preferences() # необходимо для инициализации весов переменных
    for i in range(max_steps):
        if attempt > attempt_limit: break
        vars = csp.variables #[v for v in csp.variables if v not in tabu]
        X = select_variable(vars, csp)
        X.assign(select_domain_value(X, csp))
        violations = csp.violation_list()
        estimate = csp.preferences()
        if not violations:
            if estimate < best_value:
                f.write('{} {}\n'.format(i, estimate))
                attempt, best_value, best_assignment = 0, estimate, csp.infer_assignment()
            else:
                f.write('{} {}\n'.format(i, best_value))
                attempt += 1
        for Y in violations: Y.unassign()
    return best_assignment

