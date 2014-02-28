from PyQt4.QtSql import *
from collections import namedtuple


class ConnectionError(Exception): pass
class DatabaseError(Exception): pass
class IncorrectOrder(Exception): pass
ConnData = namedtuple('ConnData', ['host', 'user', 'password', 'dbname'])
Teacher = namedtuple('Teacher', ['id', 'firstname', 'middlename', 'lastname'])
Group = namedtuple('Group', ['id', 'name', 'size'])
Exercise = namedtuple('Exercise', ['id', 'type', 'name'])
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

    def get_disciplines_for_group(self, group_id:str, semesters:tuple = None):
        def get_disciplines_for_speciality(spec_id:int, course:int):
            query_text = "select id, name from disciplines where speciality_id = {0} " \
                         "and kurs = {1}".format(spec_id, course)
            if semesters is not None:
                query_text += " and semestr in {}".format(semesters)
            q = QSqlQuery(query_text)
            disciplines = []
            while q.next():
                disciplines.append((q.value(0), q.value(1)))
            return disciplines

        self.query.exec("select speciality_id, name, size, kurs from groups where id = {}".format(group_id))
        self.query.next()
        spec_id, group_name, size, course = (self.query.value(x) for x in range(4))
        return (Group(spec_id, group_name, size), get_disciplines_for_speciality(spec_id, course))

    def get_disciplines_for_groups(self, ids:list, semesters:tuple = None):
        return dict([self.get_disciplines_for_group(id, semesters) for id in ids])

    def get_teacher_hours(self, teacher_id, semesters:tuple = None):
        q = QSqlQuery(self.db)
        q.exec("select id, firstname, middlename, lastname from teachers "
                        "where id = {}".format(teacher_id))
        q.next()
        name = Teacher(*(q.value(x) for x in range(4)))
        query_text = "select e.id, e.type_id, d.name, e.hours from " \
                     "(exercises e join disciplines d on e.discipline_id = d.id)" \
                     "where teacher_id = {}".format(teacher_id)
        if semesters is not None:
            query_text += " and d.semestr in ({})".format(*semesters)
        q.exec(query_text)
        discipline_hours = []
        while q.next():
            discipline_hours.append((Exercise(q.value(0), q.value(1), q.value(2)), q.value(3)))
        return (name, dict(discipline_hours))

    def get_teachers_hours_for_institute(self, inst_id:int, semesters:tuple = None):
        self.query.exec("select id, firstname, middlename, lastname from teachers where department_id in "
                        "(select id from departments where institute_id = {})".format(inst_id))
        hours = []
        while self.query.next():
            hours.append(self.get_teacher_hours(self.query.value(0), semesters))
        return dict(hours)

    def get_rooms_in_building(self, building_id:int):
        self.query.exec("select id, name, process_type_id, size from rooms "
                        "where building_id = {}".format(building_id))
        while self.query.next():
            yield Room(*(self.query.value(x) for x in range(4)))

    def get_all_institute_groups(self, as_names = True):
        pass


if __name__ == '__main__':
    import utils
    database = UniversityDatabase()
    a = database.get_disciplines_for_groups([73, 74, 75, 76, 77, 78])
    utils.print_dictionary(a)
    c = database.get_teachers_hours_for_institute(187, (1,))
    utils.print_dictionary(c)
    for r in database.get_rooms_in_building(61):
        print(r)