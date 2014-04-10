import sys
from itertools import groupby
from collections import defaultdict

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from csp import TimetablePlanner2
from dbconnect import UniversityDatabase
from variable import VariableCreator
from utils import INFINITY, WEEK
from algorithms import backtracking_search, weighted_search, weight_function, argmin_conflicts


class CustomTableModel(QAbstractTableModel):
    def __init__(self, groups, schedule, rowNumber, colNumber):
        QAbstractTableModel.__init__(self)
        self.rowNumber = rowNumber
        self.colNumber = colNumber
        self.schedule = schedule
        self.customHeaders = groups


    def rowCount(self, index=QModelIndex()):
        return self.rowNumber

    def columnCount(self, index=QModelIndex()):
        return self.colNumber

    def setHeaderData(self, index, orientation, value, role=Qt.EditRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            self.customHeaders[index] = value
        return super().setHeaderData(index, orientation, value, role)

    def headerData(self, index, orientation, role=None):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.customHeaders[index]
        return super().headerData(index, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or \
           not (0 <= index.row() < self.rowCount()) or \
           not (0 <= index.column() < self.columnCount()):
            return None
        item = self.schedule[index.row()][index.column()]
        if role == Qt.DisplayRole:
            return item
        elif role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter | Qt.AlignVCenter)
        elif role == Qt.TextColorRole:
            return QColor(Qt.darkBlue)
        elif role == Qt.BackgroundColorRole:
            return Qt.white
        return None


class CustomItemDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        if 0 <= index.column() < index.model().columnCount():
            text = index.model().data(index)
            palette = QApplication.palette()
            document = QTextDocument()
            document.setDefaultFont(option.font)
            document.setHtml("""<h3 style='margin-bottom: 0px'>{1}</h3><br />{2}
                             """.format(palette.highlightedText().color().name(),
                                        text[0], text[1]))
            color = palette.highlight().color() if option.state & QStyle.State_Selected \
                    else QColor(150, 150, 150) if text == ('', '') \
                    else QColor(index.model().data(index, Qt.BackgroundColorRole))
            painter.save()
            painter.fillRect(option.rect, color)
            painter.translate(option.rect.x(), option.rect.y())
            document.drawContents(painter)
            painter.restore()
        else:
            QItemDelegate.paint(self, painter, option, index)


class VariablesConverter:
    @staticmethod
    def convert(variables):
        groups, schedule = set(), []
        for v in variables: groups.update(v.listeners)
        groupnames = sorted(g.name for g in groups)
        inmonday = sorted([v for v in variables if v.day == 'mon'], key=lambda x: x.hour)
        for k, vargroup in groupby(inmonday, key=lambda x: x.hour):
            current_hour = []
            for v in vargroup:
                for g in sorted(v.listeners, key=lambda x: x.name):
                    current_hour.append((g.name, v.lecturer_name, v.discipline, v.room.name, v.type))
            current_hour = sorted(current_hour, key=lambda x: x[0])
            processed = []
            for name in groupnames:
                found = [item for item in current_hour if item[0] == name]
                if found:
                    _, lecturer, discipline, room, type = found.pop()
                    processed.append((discipline, '{}/{}/{}'.format(lecturer, room, type)))
                else:
                    processed.append(('', ''))
            schedule.append(processed)
        return groupnames, schedule


class ResultViewer(QWidget):
    def __init__(self, schedule, groupnames):
        super().__init__()
        self.tableView = QTableView()
        self.tableView.setItemDelegate(CustomItemDelegate())
        self.tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.tableView.verticalHeader().setResizeMode(QHeaderView.Stretch)
        # Создание модели данных для отображения
        cols, rows = len(groupnames), len(schedule)
        model = CustomTableModel(groupnames, schedule, rows, cols)
        self.tableView.setModel(model)
        self.mergeSameCells(schedule)
        self.tableView.setMinimumWidth(500)
        self.tableView.setMinimumHeight(350)
        layout = QHBoxLayout()
        layout.addWidget(self.tableView)
        self.setLayout(layout)

    def mergeSameCells(self, schedule):
        for (i, row) in enumerate(schedule):
            old_pair = row[0]
            spans, acc, start = [], 1, 0
            for (j, pair) in enumerate(row[1:], 1):
                if old_pair == pair:
                    acc += 1
                else:
                    if acc > 1:
                        spans.append((start, acc))
                    old_pair = pair
                    start = j
            if acc > 1: spans.append((start, acc))
            for col, span in spans:
                self.tableView.setSpan(i, col, 1, span)


def main():
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
    for v in ttp.variables:
        if v.day == 'mon':
            print(v, v.curr_value, v.listeners)
    groupnames, schedule = VariablesConverter.convert(ttp.variables)
    viewer = ResultViewer(schedule, groupnames)
    viewer.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()