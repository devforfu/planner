import random

from utils import *


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

## Variable ordering heuristics
def first_unassigned_variable(csp):
    assert([v for v in csp.variables if not v.isassigned()]) # FIXME: will be removed
    for v in csp.variables:
        if not v.isassigned(): return v

def minimum_remaining_value(csp):
    pass


## Value ordering heuristics
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


def argmin_conflicts(csp, var):
    return argmin(lambda x: csp.conflicts(var, x),
                  var.curr_domain, random.choice)

def most_weight_variable(csp, vars):
    return max(csp.weight_list().items(), key=itemgetter(1))[0]


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