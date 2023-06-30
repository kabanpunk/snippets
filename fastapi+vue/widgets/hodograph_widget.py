from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget
from pyqtgraph.graphicsItems.ScatterPlotItem import Symbols
from pyqtgraph.Qt import QtCore
from qt_graph.BoundTargetItem import BoundTargetItem
from resources.hodograph_widget_ui import Ui_HodographWidget
import pyqtgraph as pg

from widgets.hodograph_options_widget import HodographOptionsWidget


class HodographWidget(QWidget):
    remove_signal = pyqtSignal()
    gen_points_signal = pyqtSignal(object, int)

    def __init__(
            self,
    ):
        super().__init__()
        # Загрузка UI страницы.
        self.__ui = Ui_HodographWidget()
        self.__ui.setupUi(self)

        self.__ui.toolButton_remove.clicked.connect(self.__remove)
        self.__ui.toolButton_options.clicked.connect(self.__options)

        self.__name = ''
        self.__description = ''

        self.name = 'Годограф'

        self.__options_widget = HodographOptionsWidget(self.name)
        self.__options_widget.apply_signal.connect(self.__options_apply)
        self.__options_widget.gen_points_signal.connect(self.__gen_points)

        self.__should_be_removed = False

        self.__points: list[BoundTargetItem] = []

    def __gen_points(self, value: int):
        self.gen_points_signal.emit(self, value)

    def __options_apply(self):
        if self.__options_widget.combine_points:
            ...

        self.name = self.__options_widget.name
        self.__description = self.__options_widget.description

        for p in self.__points:
            if self.__options_widget.ox_fixation:
                p.fix_on_ox()
            else:
                p.free_movement_on_ox()
            p.setPen(self.__options_widget.point_color)
            p.setPath(Symbols[self.__options_widget.point_symbol])

    def __remove(self):
        self.__should_be_removed = True
        self.remove_signal.emit()

    def __options(self):
        self.__options_widget.show()

    def create_point(
            self,
            curve: pg.PlotDataItem,
            pos=None,
            update_pos_flag=True
    ) -> BoundTargetItem:
        curves = [p.curve for p in self.__points] + [curve]
        if len(curves) != len(set(curves)):
            return BoundTargetItem(curve)

        point = BoundTargetItem(
            curve, pos,
            size=20,
            symbol=Symbols[self.__options_widget.point_symbol],
            pen=self.__options_widget.point_color,
            label=lambda _, y: f"{y:.4f}",
            labelOpts={
                "offset": QtCore.QPointF(0, -20),
                "color": "#004DFF"
            }
        )

        if update_pos_flag:
            point.update_pos()

        if self.__options_widget.ox_fixation:
            point.fix_on_ox()
        else:
            point.free_movement_on_ox()

        self.__points.append(point)
        return point

    @property
    def points(self) -> list[BoundTargetItem]:
        return self.__points

    @property
    def should_be_removed(self):
        return self.__should_be_removed

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value
        self.__ui.label.setText(self.__name)
