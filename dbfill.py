import xml.etree.ElementTree as RT
import random

from PyQt4.QtSql import *
from dbconnect import createConnection, DatabaseError


def fill_disciplines(filename: str='example.xml'):
    tree = RT.parse(filename)
    db = createConnection('localhost', 'work', '123', 'university_v')
    query = QSqlQuery(db)
    for l in tree.getroot():
        for d in l.findall('discipline'):
            query_text = ('insert into {table} '
                          '(speciality_id, name, plan, kurs, semestr, spec_code) values '
                          '({speciality}, "{name}", \'{plan}\', {kurs}, {semestr}, {code})')
            plan = '<exercises>'
            for e in d.findall('exercise'):
                plan += '<exercise '
                for k, v in e.attrib.items():
                    plan += '{key}="{val}" '.format(key=k, val=v)
                plan += '/>'
            plan += '</exercises>'
            query_text = query_text.format(
                table='disciplines',
                speciality=l.attrib['speciality_id'],
                name=d.attrib['name'],
                plan=plan,
                kurs=l.attrib['kurs'],
                semestr=l.attrib['semestr'],
                code=random.randint(1000, 9000)
            )
            # print(query_text, '\n\n')
            if not query.exec(query_text):
                raise DatabaseError(query.lastError().text())


if __name__ == '__main__':
    try:
        fill_disciplines()
    except DatabaseError as err:
        print('Error occurred: ', err)