import itertools
import random

INFINITY = 99999
WEEK = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']

def print_dictionary(dict, isjson=False):
    import json
    if not dict:
        print('Empty'); return
    if isjson:
        print(json.dumps(dict)); return
    for key in sorted(dict.keys(), key=hash, reverse=True):
        acc = ''
        if isinstance(dict[key], list):
            for item in dict[key]:
                acc += str(item) + ', '
            print('{0} -> {1}'.format(key, acc[:-2]))
        else:
            print('{0} -> {1}'.format(key, dict[key]))


def every(predicate, seq):
    """ Возвращает истину, если все элементы последовательности удовлетворяют условию predicate """
    return all(map(predicate, seq))


def argmin(function, X, tiesolve=None):
    """ Возвращает элемент из множества X, минимизирующий значение функции. """
    X = [(x, function(x)) for x in sorted(X, key=function)]
    X = [x for x, y in itertools.takewhile(lambda pair: pair[1] == X[0][1], X)]
    return tiesolve(X) if tiesolve is not None else X


def argmax(function, X, tiesolve=None):
    """ Возвращает элемент из множества X, максимизирующий значение функции. """
    return argmin(lambda x: -function(x), X, tiesolve)


def bounded_sum(*args, K=INFINITY):
    """ Вычисляет сумму элементов одного или более списков, ограниченную диапазоном [0; K]. """
    s = sum(sum(map(abs, seq)) for seq in args)
    return s if s < K else K