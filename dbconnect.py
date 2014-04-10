import xml.etree.ElementTree as ET
from PyQt4.QtSql import *
from collections import namedtuple, defaultdict


class ConnectionError(Exception): pass
class DatabaseError(Exception): pass
class IncorrectOrder(Exception): pass
ConnData = namedtuple('ConnData', ['host', 'user', 'password', 'dbname'])
Teacher = namedtuple('Teacher', ['id', 'firstname', 'middlename', 'lastname'])
Group = namedtuple('Group', ['id', 'sid', 'name', 'kurs', 'size'])
Room = namedtuple('Room', ['id', 'name', 'type', 'size'])
# Exercise = namedtuple('Exercise', ['id', 'did', 'type', 'name', 'hours'])

_discipline = namedtuple('Discipline', ['id', 'name', 'plan'])
class Discipline(_discipline):
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "Discipline(id={}, name={}, plan=<xml-data>)".format(self.id, self.name)


def throw_sql_error(function):
    def wrapper(self, *args):
        if not function(self, *args):
            msg = "{0} failed: {1}".format(
                function.__name__, self.query.lastError().text())
            raise DatabaseError(msg)
    return wrapper


def createConnection(host:str, user:str, password:str, dbname=None) -> QSqlDatabase:
    db = QSqlDatabase.addDatabase('QMYSQL')
    db.setHostName(host)
    db.setUserName(user)
    db.setPassword(password)
    if dbname is not None:
        db.setDatabaseName(dbname)
    if not db.open():
        raise ConnectionError(db.lastError().text())
    return db


class UniversityDatabase:
    """ Класс осуществляет извлечение данных из БД приложения. """

    ROOM_COLUMNS = range(4)
    GROUP_COLUMNS = range(5)
    TEACHER_COLUMNS = range(4)
    DISCIPLINE_COLUMNS = range(4,7)

    def __init__(self, data:ConnData = ConnData('localhost', 'work', '123', 'university_v')):
        self.db = createConnection(*data)
        self.query = QSqlQuery(self.db)

    def _extract(self, range):
        return (self.query.value(x) for x in range)

    def get_all_disciplines(self):
        """ Возвращает последовательность из всех дисциплин, содержащихся в БД. """
        self.query.exec("select id, name, plan from disciplines")
        while self.query.next():
            yield Discipline(self.query.value(0), self.query.value(1), self.query.value(2))


    def get_all_teachers(self):
        """ Возвращает последовательность из всех преподавателей, содержищихся в БД """
        self.query.exec("select id, firstname, middlename, lastname from teachers")
        while self.query.next():
            yield Teacher(*(self.query.value(x) for x in self.TEACHER_COLUMNS))


    def get_groups_for_discipline(self, ids:tuple = (), semesters:tuple = ()):
        """ Возвращает словарь с дисциплинами, преподаваемыми в заданные семестры для заданного
            множества академических групп.
        """
        query_text = "select g.id, g.speciality_id, g.name, g.kurs, g.size, " \
                     "d.id, d.name, d.plan from (groups g join specialities s " \
                     "join disciplines d on g.speciality_id = s.id and d.speciality_id = s.id " \
                     "and g.kurs = d.kurs) "
        if ids:
            query_text += "where g.id in {} ".format(ids + (0,))
        if semesters:
            query_text += "and d.semestr in {}".format(semesters + (0,))
        group_discipline = defaultdict(set)
        self.query.exec(query_text)
        print(self.query.lastError().text())
        while self.query.next():
            g = Group(*(self.query.value(x) for x in self.GROUP_COLUMNS))
            # d = Discipline(*(self.query.value(x) for x in range(5,8)))
            d = Discipline(*self._extract(range(5, 8)))
            group_discipline[d].add(g)
        return group_discipline


    def get_discipline_teachers(self, ids:tuple = (), semesters:tuple = ()):
        """ Возвращает словарь с информацией о преподавателях и проводимых ими занятиями. """
        query_text = "select t.id, t.firstname, t.middlename, t.lastname, d.id, d.name, d.plan " \
                     "from (teachers t join teacher_discipline td join disciplines d " \
                     "on t.id = td.teacher_id and d.id = td.discipline_id) "
        if ids:
            query_text += "where t.id in {} ".format(ids + (0,))
        if semesters:
            query_text += "and d.semestr in {}".format(semesters + (0,))
        discipline_teacher = defaultdict(set)
        self.query.exec(query_text)
        while self.query.next():
            t = Teacher(*(self.query.value(x) for x in self.TEACHER_COLUMNS))
            d = Discipline(*(self.query.value(x) for x in self.DISCIPLINE_COLUMNS))
            discipline_teacher[d].add(t)
        return discipline_teacher


    def get_teachers_disciplines_for_institute(self, inst_id:int = None, semesters:tuple = ()):
        """ Возвращает информацию о занятиях всех преподавателей, работающих в институте. """
        query_text = "select id from teachers where department_id in "
        if inst_id is None:
            query_text += "(select id from departments)"
        else:
            query_text += "(select id from departments where institute_id = {})".format(inst_id)
        q = QSqlQuery(query_text)
        while q.next():
            yield self.get_discipline_teachers((q.value(0),), semesters)


    def get_teachers_load(self):
        """ Возвращает количество часов, в течение которох преподаватели должны читать лекции """
        import random
        return {t:random.randint(6,10) for t in self.get_all_teachers()}


    def get_discipline_institutes(self):
        query_text = "select d.id, d.name, d.plan, i.id from " \
                     "(disciplines d join specialities s join institutes i " \
                     "on d.speciality_id = s.id and s.institute_id = i.id) "
        discipline_institute = {}
        self.query.exec(query_text)
        while self.query.next():
            d = Discipline(*(self.query.value(x) for x in range(3)))
            discipline_institute[d] = self.query.value(3)
        return discipline_institute


    def get_rooms_in_building(self, building_id:int):
        """ Возвращает множество аудиторий, расположенных в заданном здании. """
        self.query.exec("select id, name, process_type_id, size from rooms "
                        "where building_id = {}".format(building_id))
        while self.query.next():
            yield Room(*(self.query.value(x) for x in self.ROOM_COLUMNS))


    def get_rooms_for_institute(self, inst_id:int, process_type:int = 0):
        """ Возвращает все аудитории, расположенные в зданиях, с которыми связан выбранный
            институт (т.е. здания, в которых могут проходить занятия групп этого института).
        """
        query_text = "select r.id, r.name, r.process_type_id, r.size from " \
                     "(institutes i join institute_building ib join buildings b " \
                     "join rooms r on i.id = ib.institute_id and b.id = ib.building_id " \
                     "and r.building_id = b.id) where i.id = {} ".format(inst_id)
        if process_type:
            query_text += "and r.process_type_id = {}".format(process_type)
        self.query.exec(query_text)
        while self.query.next():
            yield Room(*(self.query.value(x) for x in self.ROOM_COLUMNS))


def conntest():
    import utils
    try:
        database = UniversityDatabase()
    except ConnectionError as e:
        print(e)
    a = database.get_groups_for_discipline()
    # utils.print_dictionary(a)
    # b = database.get_teacher_disciplines()
    b = database.get_groups_for_discipline()
    utils.print_dictionary(b)
    # utils.print_dictionary(b)
    #for e in database.get_all_exercises(): print(e)


if __name__ == '__main__':
    conntest()



