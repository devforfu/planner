import itertools

INFINITY = 99999

def print_dictionary(dict):
    if not dict: print('Empty'); return
    for key in sorted(dict.keys()):
        acc = ''
        if isinstance(dict[key], list):
            for item in dict[key]:
                acc += str(item) + ', '
            print('{0} -> {1}'.format(key, acc[:-2]))
        else:
            print('{0} -> {1}'.format(key, dict[key]))


def every(predicate, seq):
    return all(map(predicate, seq))


def argmin(function, X, tiesolve=None):
    """ Returns element x from X which minimizes function value """
    X = [(x, function(x)) for x in sorted(X, key=function)]
    X = [x for x, y in itertools.takewhile(lambda pair: pair[1] == X[0][1], X)]
    return tiesolve(X) if tiesolve is not None else X


def argmax(function, X, tiesolve=None):
    """ Returns element x from X which maximizes function value """
    return argmin(lambda x: -function(x), X, tiesolve)


def bounded_sum(seq, K=INFINITY):
    """ Вычисляет сумму, ограниченную диапазоном [0; K] """
    acc = sum(map(abs, seq))
    return acc if acc < K else K