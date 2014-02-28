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


    def get_disciplines_for_speciality(self, spec_id:int, semesters:tuple = ()):
        query_text = "select id, name from disciplines " \
                     "where speciality_id = {}".format(spec_id)
        if semesters:
            query_text += " and semestr in {}".format(semesters + (0,))
        q = QSqlQuery(query_text)
        disciplines = []
        while q.next():
            disciplines.append((q.value(0), q.value(1)))
        return disciplines


    def get_disciplines_for_group(self, group_id:str, semesters:tuple = ()):
        self.query.exec("select speciality_id, name, size "
                        "from groups where id = {}".format(group_id))
        self.query.next()
        spec_id, group_name, size = (self.query.value(x) for x in range(3))
        return (Group(spec_id, group_name, size),
                self.get_disciplines_for_speciality(spec_id, semesters))


    def get_disciplines_for_groups(self, ids:list, semesters:tuple = ()):
        return dict([self.get_disciplines_for_group(id, semesters) for id in ids])


    def get_teacher_hours(self, teacher_id, semesters:tuple = ()):
        q = QSqlQuery(self.db)
        q.exec("select id, firstname, middlename, lastname "
               "from teachers where id = {}".format(teacher_id))
        name = q.next() and Teacher(*(q.value(x) for x in range(4)))
        query_text = "select e.id, e.type_id, d.name, e.hours from " \
                     "(exercises e join disciplines d on e.discipline_id = d.id) " \
                     "where teacher_id = {}".format(teacher_id)
        if semesters:
            query_text += " and d.semestr in {}".format(semesters  + (0,))
        q.exec(query_text)
        discipline_hours = []
        while q.next():
            discipline_hours.append((Exercise(q.value(0), q.value(1), q.value(2)), q.value(3)))
        return (name, dict(discipline_hours))


    def get_teachers_hours_for_institute(self, inst_id:int, semesters:tuple = ()):
        self.query.exec("select id from teachers where department_id in "
                        "(select id from departments where institute_id = {})".format(inst_id))
        while self.query.next():
            yield self.get_teacher_hours(self.query.value(0), semesters)


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
    a = database.get_disciplines_for_groups([1,2,3,4,5,6])
    utils.print_dictionary(a)
    c = database.get_teachers_hours_for_institute(1, (3,))
    utils.print_dictionary(dict(c))
    print(list(database.get_rooms_in_building(4)))
