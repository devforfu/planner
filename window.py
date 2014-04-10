import sys
from collections import defaultdict

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from csp import TimetablePlanner2
from dbconnect import UniversityDatabase
from variable import VariableCreator
from utils import INFINITY, WEEK
from algorithms import backtracking_search, weighted_search, weight_function, argmin_conflicts


class ScheduleEntry(QWidget):
    def __init__(self, *args):
        super().__init__()
        discipline, lecturer, room = args
        self.empty = not any(args)
        self.lblDiscipline = QLabel(discipline)
        self.lblDiscipline.setAlignment(Qt.AlignCenter)
        text = '' if self.empty else ' / '.join([lecturer, room])
        self.lblLecturerAndRoom = QLabel(text)
        s1, s2 = QSplitter(self), QSplitter(self)

        labelLayout = QVBoxLayout()
        labelLayout .addWidget(self.lblDiscipline)
        labelLayout .addWidget(self.lblLecturerAndRoom)

        layout = QHBoxLayout(self)
        layout.addWidget(s1)
        layout.addLayout(labelLayout)
        layout.addWidget(s2)
        layout.setSpacing(0)
        self.setMinimumWidth(180)
        self.setMaximumWidth(180)
        self.setLayout(layout)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(1)
        painter.save()
        brush = QBrush(QColor(128, 128, 128) if self.empty else QColor(255, 255, 255))
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawRect(self.rect())
        painter.restore()

    def setInfo(self, discipline:str='', lecturer:str='', room:str=''):
        self.lblDiscipline.setText(discipline)
        self.lblLecturer.setText(lecturer)
        self.lblRoom.setText(room)


class WeekSuite(QWidget):
    def __init__(self, group, timetable):
        super().__init__()
        self.widgetMap = {}
        self.group = group
        layout = QGridLayout(self)
        x = y = 0
        for day in WEEK:
            exercises = timetable.get(day, {})
            for hour in range(1,7):
                # discipline, lecturer and room
                d, l, r = exercises.get(hour, ('','',''))
                entry = ScheduleEntry(d, l, r)
                entry.hide()
                layout.addWidget(entry, x, y)
                self.widgetMap[(day, hour)] = entry
                y += 1
        layout.setHorizontalSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        self.setMaximumWidth(layout.itemAtPosition(0, 0).widget().maximumWidth()*6)
        self.setLayout(layout)

    def showDay(self, day:str):
        for d, h in self.widgetMap:
            self.widgetMap[(d, h)].setVisible(d == day)

    def setTimetable(self, timetable):
        for day in WEEK:
            exercises = timetable.get(day, {})
            for hour in range(1,7):
                self.widgetMap[(day, hour)].setInfo(exercises.get(hour, ('','','')))


class TimetableWindow(QDialog):
    def __init__(self, scheduleentries):
        super().__init__()
        self.days = WEEK
        self.dayIndex = 0
        self.currentDay = 'mon'
        self.lblCurrentDay = QLabel(self.toFullName(self.currentDay))
        self.btnNext = QPushButton('Вперед >')
        self.btnPrev = QPushButton('< Назад')
        self.btnNext.setFlat(True)
        self.btnPrev.setFlat(True)
        self.weekSuits = []
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.lblCurrentDay)
        gridLayout = QGridLayout()
        row = 1
        for group, timetable in sorted(scheduleentries.items(), key=lambda x: x[0].name):
            wgt = WeekSuite(group, timetable)
            self.weekSuits.append(wgt)
            wgt.showDay(self.currentDay)
            gridLayout.addWidget(QLabel(group.name), row, 0)
            gridLayout.addWidget(wgt, row, 1)
            row += 1
        gridLayout.setVerticalSpacing(0)
        s = QSplitter(Qt.Vertical)
        navigator = QHBoxLayout()
        navigator.addWidget(self.btnPrev)
        navigator.addWidget(self.btnNext)
        mainLayout.addLayout(gridLayout)
        mainLayout.addWidget(s)
        mainLayout.addLayout(navigator)
        self.setLayout(mainLayout)
        self.btnNext.clicked.connect(self.nextDay)
        self.btnPrev.clicked.connect(self.prevDay)

    def nextDay(self):
        self.dayIndex += 1
        if self.dayIndex >= len(WEEK):
            self.dayIndex = 0
        self.currentDay = WEEK[self.dayIndex]
        self.updateTimetable()

    def prevDay(self):
        self.dayIndex -= 1
        if self.dayIndex < 0:
            self.dayIndex = len(WEEK) - 1
        self.currentDay = WEEK[self.dayIndex]
        self.updateTimetable()

    def updateTimetable(self):
        for w in self.weekSuits:
            w.showDay(self.currentDay)
        self.lblCurrentDay.setText(self.toFullName(self.currentDay))

    def toFullName(self, day):
        return "<h2>{}</h2>".format({
            'mon': 'Понедельник',
            'tue': 'Вторник',
            'wed': 'Среда',
            'thu': 'Четверг',
            'fri': 'Пятница',
            'sat': 'Суббота'
        }[day])


def main():
    import random
    def rand(X, csp):
        csp.preferences()
        return random.choice(X.curr_domain)

    app = QApplication(sys.argv)
    database = UniversityDatabase()
    creator = VariableCreator(database)
    ttp = TimetablePlanner2(creator=creator, weight_estimate=weight_function)
    ttp.setup_constraints()
    ttp.setup_preferences()
    backtracking_search(ttp)
    assignment = ttp.infer_assignment()
    value, assignment = weighted_search(ttp, max_steps=250, filename='random',
                                        select_domain_value=argmin_conflicts)
    if value == INFINITY:
        print('CSP failed: solution not found!')
        return
    print('solution weight: ', value)
    d = defaultdict(dict)
    for var in assignment:
        ((day, hour), room), group = var.curr_value, var.listeners.pop()
        t = (var.discipline, var.lecturer_name, room.name)
        try:
            d[group][day][hour] = t
        except KeyError as e:
            d[group][day] = {hour:t}
    wgt = TimetableWindow(d)
    wgt.show()
    app.exec_()


if __name__ == '__main__':
    main()
