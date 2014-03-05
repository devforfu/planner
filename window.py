import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from utils import WEEK


class ScheduleEntry(QWidget):
    def __init__(self, *args):
        super().__init__()
        discipline, lecturer, room = args
        self.empty = not any(args)
        lblDiscipline = QLabel(discipline)
        lblDiscipline.setAlignment(Qt.AlignCenter)
        lblLecturer = QLabel(lecturer)
        lblRoom = QLabel(room)
        s1, s2 = QSplitter(self), QSplitter(self)

        labelGrid = QGridLayout()
        labelGrid.addWidget(lblDiscipline, 0, 0, 1, 2)
        labelGrid.addWidget(lblLecturer, 1, 0)
        labelGrid.addWidget(lblRoom, 1, 1)

        layout = QHBoxLayout(self)
        layout.addWidget(s1)
        layout.addLayout(labelGrid)
        layout.addWidget(s2)
        self.setMinimumWidth(120)
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
        self.setLayout(layout)

    def show_day(self, day:str):
        for d, h in self.widgetMap:
            if d == day: self.widgetMap[(d, h)].setVisible(True)


class TimetableWindow(QDialog):
    def __init__(self, scheduleentries):
        super().__init__()
        layout = QVBoxLayout()
        for group, timetable in scheduleentries.items():
            wgt = WeekSuite(group, timetable)
            wgt.show_day('mon')
            layout.addWidget(wgt)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    d = {
        '1291': dict(
            mon={1:('Мат. анализ', 'Семенов', '205'), 2:('Физика', 'Иванов', '406')},
            wed={2:('Физика', 'Иванов', '407'), 3:('Физика', 'Кузнецов', '422')}
        ),
        '1292': dict(
            mon={1:('ЦСТ', 'Краснов', '310'), 3:('ЦСТ', 'Фриз', '322'), 4:('Физика', 'Иванов', '407')}
        )
    }
    wgt = TimetableWindow(d)
    wgt.show()
    app.exec_()