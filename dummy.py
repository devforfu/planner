""" Module for random data generation """

import random
import itertools
from operator import itemgetter
import PyQt4
from PyQt4.QtSql import *
from PyQt4.QtCore import *
from dbconnect import createConnection

def throw_sql_error(function):
    def wrapper(self, *args):
        if not function(self, *args):
            msg = "{0} failed: {1}".format(
                function.__name__, self.query.lastError().text())
            raise DatabaseError(msg)
    return wrapper


class FictionUniversity:
    def __init__(self, db: QSqlDatabase):
        assert(isinstance(db, QSqlDatabase))
        self.db = db
        self.query = QSqlQuery(self.db)
        self.department_uniq_num = 1

    def wipe(self):
        query = self.query
        query.exec("set @old_foreign_key_checks=@@foreign_key_checks, foreign_key_checks=0")
        query.exec("select TABLE_NAME from information_schema.tables "
                            "where TABLE_SCHEMA like '{}'".format(db.databaseName()))
        while query.next():
            del_query = QSqlQuery()
            if not del_query.exec("delete from {}".format(query.value(0))):
                raise DatabaseError("wipe() failed: " + del_query.lastError().text())

    @throw_sql_error
    def fill_institutes(self, data:list):
        query = self.query
        query.prepare("insert into institutes (name, abr, number) "
                      "values (:name, :abr, :number)")
        for name in data:
            first_letters = list(map(itemgetter(0), name.split(' ')))
            first_letters.append('и')
            first_letters = ''.join(first_letters)
            first_letters = first_letters.upper()
            query.bindValue(':name', name)
            query.bindValue(':abr', first_letters)
            query.bindValue(':number', random.randint(10000, 99999))
            if not query.exec_():
                return False
        return True

    @throw_sql_error
    def fill_departments_for_institute(self, institute_id, departments:list):
        query = self.query
        query.prepare("insert into departments (institute_id, name, number) "
                      "values ({}, :name, :number)".format(institute_id))
        for name in departments:
            query.bindValue(':name', name)
            query.bindValue(':number', self.department_uniq_num)
            self.department_uniq_num += 1
            if not query.exec_():
                return False
        return True

    def fill_departments(self, inst_dept:dict):
        query = QSqlQuery(self.db)
        query.exec("select id, name from institutes")
        while query.next():
            inst_id, inst_name = query.value(0), query.value(1)
            departments = inst_dept[inst_name]
            self.fill_departments_for_institute(inst_id, departments)

    @throw_sql_error
    def fill_positions(self, positions:list):
        return all([self.query.exec("insert into positions (name) "
                              "values ('{}')".format(p)) for p in positions])

    @throw_sql_error
    def fill_types(self, types:list):
        return all([self.query.exec("insert into process_types (name) "
                                    "values ('{}')".format(t)) for t in types])

    @throw_sql_error
    def fill_degrees(self, degrees:list):
        return all([self.query.exec("insert into degrees (name, abr) "
                                    "values ('{}', '')".format(d)) for d in degrees])

    @throw_sql_error
    def fill_buildings(self, buildings:list):
        def firts_letter(word):
            return word[0].upper()

        pairs = [(name, ''.join(list(map(firts_letter, name.split(' ')))))
                 for name in buildings]
        return all([self.query.exec("insert into buildings (name, abr) "
                                    "values ('{0}', '{1}')".format(*p)) for p in pairs])

    @throw_sql_error
    def fill_rooms_in_building(self, building_id, floors = (4, 10),
                               rooms = (6, 20), size = (12, 100)):
        query = self.query
        query.exec("select `int`, name from process_types")
        process_types = []
        while query.next():
            process_types.append(query.value(0))
        nfloors = random.randint(*floors)
        nrooms = random.randint(*rooms)
        minimum, maximum = size
        middle = (minimum + maximum) // 2
        room_names = [str(f*100+r) for f in range(1, nfloors+1) for r in range(1, nrooms+1)]
        name_sizes = [(name, random.choice([minimum, middle, maximum]))
                      for name in room_names]
        query.prepare("insert into rooms "
                      "(building_id, name, process_type_id, comment, size) values "
                      "({}, :name, :type, :comment, :size)".format(building_id))
        for name, size in name_sizes:
            query.bindValue(':name', name)
            query.bindValue(':type', random.choice(process_types))
            query.bindValue(':comment', '')
            query.bindValue(':size', size)
            if not query.exec_():
                return False
        return True

    def fill_rooms(self):
        query = QSqlQuery(self.db)
        query.exec("select id from buildings")
        while query.next():
            id = query.value(0)
            print(id)
            self.fill_rooms_in_building(id)

    @throw_sql_error
    def fill_institute_with_specialities(self, institute_id, spec:list):
        query = self.query
        query.prepare("insert into specialities (institute_id, name, abr, code, subname) "
                      "values ({}, :name, '', :code, '')".format(institute_id))
        for name in spec:
            query.bindValue(':name', name)
            query.bindValue(':code', random.randint(20000, 30000))
            if not query.exec_():
                return False
        return True

    def fill_specialities(self, inst_spec:dict):
        query = QSqlQuery(self.db)
        query.exec("select id, name from institutes")
        while query.next():
            inst_id, inst_name = query.value(0), query.value(1)
            specialities = inst_spec[inst_name]
            self.fill_institute_with_specialities(inst_id, specialities)

    def fill_groups(self):
        query = self.query
        query.exec("select id from degrees")
        if query.next():
            degree = query.value(0)
        query.exec("select id from specialities")
        while query.next():
            spec_id = query.value(0)
            insert_query = QSqlQuery(self.db)
            insert_query.prepare("insert into groups (speciality_id, degree_id, year, kurs, number, name, size) "
                                 "values (:id, :degree, :year, :kurs, :number, :name, :size)")
            insert_query.bindValue(':id', spec_id)
            insert_query.bindValue(':degree', degree)
            n = random.choice([4,5])
            insert_query.bindValue(':year', n)
            insert_query.bindValue(':kurs', n)
            insert_query.bindValue(':number', 0)
            name = 'гр. ' + str(random.randint(1000, 2000))
            insert_query.bindValue(':name', name)
            insert_query.bindValue(':size', 20)
            if not insert_query.exec_():
                return False
        return True

    @throw_sql_error
    def fill_teachers_for_department(self, dept_name:str, fnames:list, mnames:list,
                                     lnames:list, overall:int = 120):
        query = self.query
        query.exec("select id from departments where name like '{}'".format(dept_name))
        dept_id = query.next() and query.value(0)
        query.exec("select id, name from positions")
        positions = []
        while query.next():
            positions.append((query.value(0), query.value(1)))
        query.prepare("insert into teachers (department_id, position_id, firstname, middlename, lastname) "
                      "values (:did, :pid, :fname, :mname, :lname)")
        while overall:
            pair = pid, pname = random.choice(positions)
            if pname == 'Зав. кафедрой':
                positions.remove(pair)
            query.bindValue(':did', dept_id)
            query.bindValue(':pid', pid)
            query.bindValue(':fname', random.choice(fnames))
            query.bindValue(':mname', random.choice(mnames))
            query.bindValue(':lname', random.choice(lnames))
            if not query.exec_():
                return False
            overall -= 1
        return True

    @throw_sql_error
    def fill_disciplines_for_speciality(self, spec_name:str, total_semesters = 9, per_semester = 8):
        import math
        query = self.query
        query.exec("select id from specialities where name like '{}'".format(spec_name))
        spec_id = query.next() and query.value(0)
        query.prepare("insert into disciplines (speciality_id, name, plan, kurs, semestr, spec_code) "
                          "values ({}, :name, :plan, :kurs, :semestr, :spec_code)".format(spec_id))
        for s in range(1, total_semesters+1):
            for n in range(1, per_semester+1):
                name = 'Дисциплина-' + str(s) + str(n)
                query.bindValue(':name', name)
                query.bindValue(':plan', 20)
                query.bindValue(':kurs', math.ceil(s/2))
                query.bindValue(':semestr', s)
                query.bindValue(':spec_code', 0)
                if not query.exec_():
                    return False
        return True

    @throw_sql_error
    def fill_exercises_for_teachers(self, spec_name:str):
        query = self.query
        query.exec("select id from specialities where name like '{}'".format(spec_name))
        spec_id = query.next() and query.value(0)
        query.exec("select id from disciplines where speciality_id = {}".format(spec_id))
        disciplines, types = [], []
        while query.next():
            disciplines.append(query.value(0))
        query.exec("select `int` from process_types")
        while query.next():
            types.append(query.value(0))
        query.exec("select id from teachers")
        while query.next():
            if random.randint(1, 100) < 60:
                continue
            teacher_id = query.value(0)
            q = QSqlQuery()
            q.prepare("insert into exercises (teacher_id, discipline_id, type_id, hours) "
                      "values (:tid, :did, :type, :hours)")
            for x in range(random.randint(1, 3)):
                q.bindValue(':tid', teacher_id)
                d = random.choice(disciplines)
                q.bindValue(':did', d)
                if random.randint(1,100) < 80:
                    disciplines.remove(d)
                q.bindValue(':type', random.choice(types))
                q.bindValue(':hours', random.choice([2,2,3,4]))
                if not q.exec_():
                    return False
                if not disciplines:
                    return True
        return True


if __name__ == '__main__':
    host, user, password = 'localhost', 'work', '123'
    db = createConnection(host, user, password, 'univercity')
    insts = ['Математический', 'Политехнический',
             'Радиотехнический', 'Гуманитарный', 'Юридический']
    depts = [
        ['Прикладная математика', 'Теоретическая математика'],
        ['Автоматики и компьютерных систем', 'АСОИУ'],
        ['Телевидение'],
        ['Лингвистика', 'Филология'],
        ['Гражданское право', 'Уголовное право']
    ]
    specs = [
        ['Высшая математика', 'Математическое моделирование'],
        ['ПОВТиАС', 'УИТС', 'Физика', 'Радиотехника'],
        ['Оптоволоконные линии связи'],
        ['Перевод', 'Литературоведение', 'Филология'],
        ['Адвокатура', 'Арбитраж']
    ]

    inst_dept = { i:d for i, d in zip(insts, depts) }
    inst_spec = { i:s for i, s in zip(insts, specs) }

    positions = ['Ассистент', 'Преподаватель', 'Ст. преподаватель',
                 'Доцент', 'Профессор', 'Зав. кафедрой']
    types = ['Лекция', 'Лабораторная', 'Практика']
    buildings = ['Главное здание', 'Северный корпус', 'Южный корпус', 'Новое здание']
    degrees = ['Специалитет', 'Магистратура', 'Бакалавриат']
    fiction = FictionUniversity(db)
    # fiction.wipe()
    if True:
        try:
            fiction.wipe()
            fiction.fill_institutes(insts)
            fiction.fill_departments(inst_dept)
            fiction.fill_positions(positions)
            fiction.fill_types(types)
            fiction.fill_buildings(buildings)
            fiction.fill_rooms()
            fiction.fill_degrees(degrees)
            fiction.fill_teachers_for_department(
                'Автоматики и компьютерных систем',
                ['Иван', 'Петр', 'Андрей', 'Михаил', 'Федор', 'Игорь', 'Дмитрий'],
                ['Сергеевич', 'Иванович', 'Петрович', 'Леонидович', 'Федорович',
                 'Игоревич', 'Ильич', 'Степанович'],
                ['Семенов', 'Иванов', 'Кузнецов', 'Петров', 'Сидоров', 'Рыбаков',
                 'Федоров', 'Симонов', 'Попов']
            )
            fiction.fill_specialities(inst_spec)
            fiction.fill_groups()
            for s in ['ПОВТиАС', 'УИТС', 'Физика', 'Радиотехника']:
                fiction.fill_disciplines_for_speciality(s)
                fiction.fill_exercises_for_teachers(s)
            pass
        except DatabaseError as e:
            print(e)
        finally:
            fiction.query.exec("set foreign_key_checks=1")
            db.close()
