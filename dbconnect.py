from PyQt4.QtSql import *
from collections import namedtuple, defaultdict


class ConnectionError(Exception): pass
class DatabaseError(Exception): pass
class IncorrectOrder(Exception): pass
ConnData = namedtuple('ConnData', ['host', 'user', 'password', 'dbname'])
Teacher = namedtuple('Teacher', ['id', 'firstname', 'middlename', 'lastname'])
Group = namedtuple('Group', ['id', 'sid', 'name', 'kurs', 'size'])
Exercise = namedtuple('Exercise', ['id', 'did', 'type', 'name', 'hours'])
Room = namedtuple('Room', ['id', 'name', 'type', 'size'])


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
    def __init__(self, data:ConnData = ConnData('localhost', 'work', '123', 'univercity')):
        try:
            self.db = createConnection(*data)
        except ConnectionError as e:
            print(e)
        self.query = QSqlQuery(self.db)


    def get_all_disciplines(self):
        self.query.exec("select id, name from disciplines")
        while self.query.next():
            yield (self.query.value(0), self.query.value(1))


    def get_all_exercises(self):
        self.query.exec("select e.id, d.id, e.type_id, d.name, e.hours from "
                        "(exercises e join disciplines d on e.discipline_id = d.id)")
        while self.query.next():
            yield Exercise(*(self.query.value(x) for x in range(5)))


    def get_disciplines_for_group(self, ids:tuple = (), semesters:tuple = ()):
        query_text = "select id, speciality_id, name, kurs, size from groups "
        if ids:
            query_text += "where id in {}".format(ids + (0,))
        group_disc = defaultdict(list)
        self.query.exec(query_text)
        while self.query.next():
            g = Group(*(self.query.value(x) for x in range(5)))
            query_text = "select id, name from disciplines where speciality_id = {} " \
                         "and kurs = {}".format(g.sid, g.kurs)
            if semesters:
                query_text += "and semestr in {}".format(semesters + (0,))
            q = QSqlQuery(query_text)
            while q.next():
                group_disc[g].append((q.value(0), q.value(1)))
        return group_disc


    def get_teacher_hours(self, ids:tuple = (), semesters:tuple = ()):
        query_text = "select id, firstname, middlename, lastname from teachers "
        if ids:
            query_text += "where id in ".format(ids + (0,))
        self.query.exec(query_text)
        teacher_hours = defaultdict(set)
        while self.query.next():
            t = Teacher(*(self.query.value(x) for x in range(4)))
            query_text = "select e.id, d.id, e.type_id, d.name, e.hours from " \
                         "(exercises e join disciplines d on e.discipline_id = d.id) " \
                         "where teacher_id = {} ".format(t.id)
            if semesters:
                query_text += "and semestr in {}".format(semesters + (0,))
            q = QSqlQuery(query_text)
            while q.next():
                teacher_hours[t].add(Exercise(*(q.value(x) for x in range(5))))
        return teacher_hours


    def get_teachers_hours_for_institute(self, inst_id:int = None, semesters:tuple = ()):
        query_text = "select id from teachers where department_id in "
        if inst_id is None:
            query_text += "(select id from departments)"
        else:
            query_text += "(select id from departments where institute_id = {})".format(inst_id)
        self.query.exec(query_text)
        while self.query.next():
            yield self.get_teacher_hours(self.query.value(0), semesters)


    def get_rooms_in_building(self, building_id:int):
        self.query.exec("select id, name, process_type_id, size from rooms "
                        "where building_id = {}".format(building_id))
        while self.query.next():
            yield Room(*(self.query.value(x) for x in range(4)))



if __name__ == '__main__':
    import utils
    database = UniversityDatabase()
    a = database.get_disciplines_for_group()
    # utils.print_dictionary(a)
    b = database.get_teacher_hours()
    # utils.print_dictionary(b)
    for e in database.get_all_exercises(): print(e)

