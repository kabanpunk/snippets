import os

import numpy as np
from PyQt5 import QtWidgets

from PyQt5.QtCore import pyqtSlot, QThreadPool
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QFileDialog

from pyqtgraph import mkPen, FillBetweenItem
import pyqtgraph as pg

from pyqtgraph.Qt import QtCore

from resources.traces_window_ui import Ui_TracesWindow
from widgets.hodograph_widget import HodographWidget
from widgets.traces_plot_widget import TracesPlotWidget

import seg_read

from pyqtspinner import WaitingSpinner
from workers.traces import TracesWorker

from widgets.parameters_widget import ParametersWidget


class TracesWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Загрузка UI страницы.
        self.__ui = Ui_TracesWindow()
        self.__ui.setupUi(self)

        # Инициализация окна параметров
        self.__parameters_widget = ParametersWidget(self)
        self.__parameters_widget.apply_signal.connect(self.__parameters_apply)

        # Установка PlotWidget'а.
        self.__plot_widget = TracesPlotWidget()
        self.__ui.gridLayout.addWidget(self.__plot_widget, 0, 0)

        self.__file = None
        self.__head = None
        self.__trace_head = None
        self.__traces = None

        self.__is_first_render = True

        self.__signal_curves = []
        self.__fill_between_curves = []
        self.__b_plots = []
        self.__t_plot_half = []

        # Загрузочный спиннер.
        self.__spinner = WaitingSpinner(self)

        # Инициализация worker'а для вычисления PlotItem'ов.
        self.__traces_worker = TracesWorker()
        # Разрешение на запуск отрисовки (проверяет есть ли запущенный QThread).
        self.__rendering_permission = True

        # Подключение обработчиков событий.
        self.__ui.horizontalSlider_gain.valueChanged.connect(self.__dial_gain_changed)
        self.__ui.lineEdit_gain.textChanged.connect(self.__lineEdit_gain_changed)
        self.__ui.pushButton_reset_scale.clicked.connect(lambda: self.__plot_widget.getPlotItem().enableAutoRange())
        self.__plot_widget.scene().sigMouseMoved.connect(self.__mouse_moved)
        self.__plot_widget.scene().sigMouseClicked.connect(self.__mouse_clicked)
        self.__ui.actionParameters.triggered.connect(self.__action_parameters)
        self.__ui.pushButton_add_hodograph.clicked.connect(self.__create_hodograph)
        self.__ui.listWidget.itemSelectionChanged.connect(self.__listWidget_item_selection_changed)
        self.__ui.action_open.triggered.connect(self.__action_open_file)
        self.__ui.action_export.triggered.connect(self.__action_export)

        # Инициализация линий отображающих текущее положение курсора.
        self.__v_line = pg.InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=3, style=QtCore.Qt.DashLine))
        self.__h_line = pg.InfiniteLine(angle=0, movable=False, pen=mkPen('r', width=3, style=QtCore.Qt.DashLine))

        # Добавляем эти линии
        self.__plot_widget.addItem(self.__v_line)
        self.__plot_widget.addItem(self.__h_line)

        self.__plot_widget.invertY()

        # Текущий годограф
        self.__selected_hodograph: int = -1

    @property
    def file(self):
        return self.__file

    @file.setter
    def file(self, value):
        self.__file = value
        self.__read()
        self.__render_plot()

    def open_file(self):
        self.__action_open_file()

    def __create_hodograph(self):
        item = QListWidgetItem()

        item_widget = HodographWidget()
        item_widget.remove_signal.connect(self.__remove_hodograph)
        item_widget.gen_points_signal.connect(self.__gen_points)

        item.setSizeHint(item_widget.sizeHint())
        self.__ui.listWidget.addItem(item)
        self.__ui.listWidget.setItemWidget(item, item_widget)

    def __gen_points(self, hodograph_widget: HodographWidget, dist: int):
        x, y = zip(*[(p.pos().x(), p.pos().y()) for p in sorted(hodograph_widget.points, key=lambda p: p.pos().x())])

        for i in range(len(hodograph_widget.points) - 1):
            x_1, x_2 = x[i], x[i + 1]
            y_1, y_2 = y[i], y[i + 1]

            line_params: np.array = np.polyfit([x_1, x_2], [y_1, y_2], 1)

            m, c = np.transpose(line_params)

            for curve in self.__signal_curves:
                xs = curve.xData
                ys = curve.yData

                if not x_1 < xs[0] < x_2:
                    continue

                y_c = m * xs[0] + c

                # Если точка пересечения выходит за границы графика
                if y_c < 0:
                    continue

                # Индекс точки пересечения (intersection point index)
                ip_i = min(range(len(ys)), key=lambda i: abs(ys[i] - y_c))

                # Максимальная по иксу точка на отрезке
                if not xs[ip_i - dist: ip_i + dist].any():
                    continue
                mp_i, mp_x = max(enumerate(xs[ip_i - dist: ip_i + dist]), key=lambda i: i[1])

                mp_i += ip_i - dist

                point = hodograph_widget.create_point(
                    curve,
                    pos=(xs[mp_i], ys[mp_i]),
                    update_pos_flag=False
                )

                # Проверка если item_widget.create_point не смог расположить точку (две на одной трассе)
                if point.pos():
                    self.__plot_widget.addItem(point)

    def __remove_hodograph(self):
        for i in range(self.__ui.listWidget.count()):
            item = self.__ui.listWidget.item(i)
            item_widget: HodographWidget = self.__ui.listWidget.itemWidget(item)
            if not item_widget:
                continue
            # print(i, item_widget.should_be_removed)
            if item_widget.should_be_removed:
                for p in item_widget.points:
                    self.__plot_widget.removeItem(p)
                item_widget.points.clear()
                self.__ui.listWidget.takeItem(i)

    def __listWidget_item_selection_changed(self):
        if len(self.__ui.listWidget.selectedIndexes()) > 0:
            self.__selected_hodograph = self.__ui.listWidget.selectedIndexes()[0].row()
        else:
            self.__selected_hodograph = -1

    def __parameters_apply(self):
        self.__ui.lineEdit_gain.setText(str(self.__parameters_widget.gain))
        self.__ui.horizontalSlider_gain.setValue(self.__parameters_widget.gain)
        self.__ui.horizontalSlider_gain.setMinimum(self.__parameters_widget.gain_min)
        self.__ui.horizontalSlider_gain.setMaximum(self.__parameters_widget.gain_max)
        self.__render_plot()

    def __action_export(self):
        dialog = QFileDialog(self)
        dialog.setNameFilter("TPoints Files (*.tpnt)")
        name = dialog.getSaveFileName(self, 'Save File')
        file = open(name[0], 'w')
        for i in range(self.__ui.listWidget.count()):
            item = self.__ui.listWidget.item(i)
            item_widget: HodographWidget = self.__ui.listWidget.itemWidget(item)
            file.write(f'{item_widget.name}:')
            for point in item_widget.points:
                file.write(f'{point.pos().x()},{point.pos().y()};')
            file.write('\n')
        file.close()

    def __action_open_file(self):
        dialog = QFileDialog(self)
        dialog.setDirectory(os.path.abspath(os.path.dirname(__file__)))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("SegY Files (*.segy)")
        dialog.setViewMode(QFileDialog.ViewMode.Detail)
        if dialog.exec():
            filenames = dialog.selectedFiles()
            if filenames:
                self.__file = filenames[0]
                self.__read()
                self.__render_plot()

    def __action_parameters(self):
        self.__parameters_widget.show()

    def __closest_curve(self, pos: QtCore.QPointF):
        closest_curve_i, closest_curve_d = 0, float('inf')
        for i, signal_curve in enumerate(self.__signal_curves):
            cdc_ = abs(signal_curve.xData[0] - pos.x())
            if cdc_ < closest_curve_d:
                closest_curve_d = cdc_
                closest_curve_i = i
        return self.__signal_curves[closest_curve_i]

    def __mouse_clicked(self, event):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            mouse_point = self.__plot_widget.getViewBox().mapSceneToView(event.scenePos())
            closest_curve = self.__closest_curve(mouse_point)

            item = self.__ui.listWidget.item(self.__selected_hodograph)
            item_widget: HodographWidget = self.__ui.listWidget.itemWidget(item)

            # Проверка если нет выбранного годографа
            if not item_widget:
                return

            point = item_widget.create_point(
                closest_curve,
                pos=(mouse_point.x(), mouse_point.y())
            )

            # Проверка если item_widget.create_point не смог расположить точку (две на одной трассе)
            if point.pos():
                self.__plot_widget.addItem(point)

            print(event, event.pos(), type(event), modifiers)

    def __mouse_moved(self, pos: QtCore.QPointF):
        """
        Обработчик события движения мыши.
        :param pos: Абсолютная позиция мыши.
        """

        # Получаем позицию относительно наших координат.
        mouse_point = self.__plot_widget.getViewBox().mapSceneToView(pos)
        if self.__plot_widget.getViewBox().sceneBoundingRect().contains(pos):
            self.__ui.label_pos.setText(
                "<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y=%0.1f</span>" % (
                    mouse_point.x(), mouse_point.y()))
            self.__v_line.setPos(mouse_point.x())
            self.__h_line.setPos(mouse_point.y())

    def __read(self):
        """
        Чтение данных из файла.
        """
        seg_file = seg_read.seg.SegReader()
        seg_file.open(self.__file)
        self.__traces, self.__head, self.__trace_head = seg_file.read_all()

    def __dial_gain_changed(self, value: int):
        """
        Обработчик события изменение положения круговой шкалы.
        """
        self.__ui.lineEdit_gain.setText(str(value))
        self.__parameters_widget.gain = value
        self.__render_plot()

    def __lineEdit_gain_changed(self, value: str):
        """
        Обработчик события редактирование текстовой строки связанной с круговой шкалой.
        """
        value = int(value)
        if 0 <= value <= 10000:
            self.__ui.horizontalSlider_gain.setValue(value)
        else:
            ...

    def __render_plot(self):
        """
        Отрисовка всех данных
        """

        if not self.__rendering_permission:
            return

        self.__rendering_permission = False

        if self.__is_first_render:
            self.__spinner.start()

        # Plot params
        # Усиление
        gain = self.__parameters_widget.gain
        # Срезание
        clipping = self.__parameters_widget.clipping
        # Срез оси времени от 0 до w_d
        w_d = self.__parameters_widget.w_d
        # Частота дискретизации
        dt = self.__parameters_widget.dt
        # Диапазон срезания: +-clip_s
        clip_s = self.__parameters_widget.clip_s

        # Инициализация worker'а
        self.__traces_worker = TracesWorker(
            self,
            traces=self.__traces,
            group_x=self.__trace_head['GroupX'].to_numpy(),
            clip_s=clip_s,
            gain=gain,
            dt=dt,
            w_d=w_d,
            clipping=clipping
        )
        # Запуск потока
        QThreadPool.globalInstance().start(self.__traces_worker)

    @pyqtSlot()
    def __end_of_processing(self):
        """
        Обработчик события завершения работы worker'а.
        """
        self.__rendering_permission = True

        if self.__is_first_render:
            self.__spinner.stop()

        if not self.__traces_worker.signal_curves:
            return

        # Отрисовка всех полученных данных от worker'а.
        if self.__signal_curves == [] or self.__fill_between_curves == []:
            for i in range(len(self.__traces_worker.signal_curves)):
                sample = (
                    self.__traces_worker.signal_curves[i],
                    self.__traces_worker.pilot_data[i][0],
                    self.__traces_worker.pilot_data[i][1]
                )
                self.__b_plots.append(pg.PlotDataItem(sample[1][0], sample[1][1], pen=(0, 0, 0), skipFiniteCheck=True))
                self.__t_plot_half.append(
                    pg.PlotDataItem(sample[2][0], sample[2][1], pen=(0, 0, 0), skipFiniteCheck=True))

                self.__signal_curves.append(
                    pg.PlotDataItem(sample[0][0], sample[0][1], pen=(0, 0, 0), skipFiniteCheck=True))
                self.__fill_between_curves.append(
                    FillBetweenItem(
                        self.__b_plots[i],
                        self.__t_plot_half[i],
                        (0, 0, 0)
                    )
                )

                self.__plot_widget.addItem(self.__signal_curves[i])
                self.__plot_widget.addItem(self.__fill_between_curves[i])
        else:
            for i in range(len(self.__traces_worker.signal_curves)):
                sample = (
                    self.__traces_worker.signal_curves[i],
                    self.__traces_worker.pilot_data[i][0],
                    self.__traces_worker.pilot_data[i][1]
                )
                self.__signal_curves[i].setData(sample[0][0], sample[0][1], pen=(0, 0, 0))
                self.__b_plots[i].setData(sample[1][0], sample[1][1])
                self.__t_plot_half[i].setData(sample[2][0], sample[2][1])
                self.__fill_between_curves[i].setCurves(
                    self.__b_plots[i],
                    self.__t_plot_half[i]
                )

        self.__is_first_render = False

