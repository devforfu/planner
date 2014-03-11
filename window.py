import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from csp import *


class ScheduleEntry(QWidget):
    def __init__(self, *args):
        super().__init__()
        discipline, lecturer, room = args
        self.empty = not any(args)
        self.lblDiscipline = QLabel(discipline)
        self.lblDiscipline.setAlignment(Qt.AlignCenter)
        self.lblLecturer = QLabel(lecturer)
        self.lblRoom = QLabel(room)
        s1, s2 = QSplitter(self), QSplitter(self)

        labelGrid = QGridLayout()
        labelGrid.addWidget(self.lblDiscipline, 0, 0, 1, 2)
        labelGrid.addWidget(self.lblLecturer, 1, 0)
        labelGrid.addWidget(self.lblRoom, 1, 1)

        layout = QHBoxLayout(self)
        layout.addWidget(s1)
        layout.addLayout(labelGrid)
        layout.addWidget(s2)
        self.setMinimumWidth(140)
        self.setMaximumWidth(140)
        self.setLayout(layout)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(2)
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
        layout.setSpacing(1)
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
        #self.btnGen = QPushButton('Сгенерировать')
        self.btnNext.setFlat(True)
        self.btnPrev.setFlat(True)
        #self.btnGen.setFlat(True)
        self.weekSuits = []
        layout = QGridLayout()
        layout.addWidget(self.lblCurrentDay, 0, 0, 1, 2)
        row = 1
        for group, timetable in sorted(scheduleentries.items(), key=lambda x: x[0].name):
            wgt = WeekSuite(group, timetable)
            self.weekSuits.append(wgt)
            wgt.showDay(self.currentDay)
            layout.addWidget(QLabel(group.name), row, 0)
            layout.addWidget(wgt, row, 1)
            row += 1
        navigator = QHBoxLayout()
        navigator.addWidget(self.btnPrev)
        navigator.addWidget(self.btnNext)
        layout.addLayout(navigator, row, 0, 1, 2)
        layout.setVerticalSpacing(0)
        self.setLayout(layout)
        self.btnNext.clicked.connect(self.nextDay)
        self.btnPrev.clicked.connect(self.prevDay)
        #self.btnGen.clicked.connect(self.generateTimetable)

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


if __name__ == '__main__':
    ttp = TimetablePlanner2(weight_estimate=weight)
    ttp.setup_constraints()
    backtracking_search(ttp)
    a = combined_local_search(
        ttp,
        select_variable=lambda x, _: most_weight_variable(x),
        max_steps=10000,
        attempt_limit=100
    )

    #a = min_conflicts(ttp, max_steps=2000)

    #backtracking_search(ttp)
    #a = ttp.infer_assignment()

    tree = lambda: defaultdict(tree); root = tree()
    d = defaultdict(dict)
    b = assign_groups(a)
    for var in b:
        ((day, hour), room), groupset = b[var]
        group = groupset.pop()
        t = (var.discipline, var.last_name, room.name)
        try:
            d[group][day][hour] = t
        except KeyError as e:
            d[group][day] = {hour:t}

    app = QApplication(sys.argv)
    wgt = TimetableWindow(d)
    wgt.show()
    app.exec_()