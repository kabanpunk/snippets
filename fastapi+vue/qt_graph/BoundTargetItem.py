import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from models.line import get_line_params
from models.point import Point
from widgets.edit_bound_target_item_widget import EditBoundTargetItemWidget


class BoundTargetItem(pg.TargetItem):
    def __init__(
            self,
            curve: pg.PlotDataItem,
            pos=None,
            size=10,
            symbol="crosshair",
            pen=None,
            hoverPen=None,
            brush=None,
            hoverBrush=None,
            movable=True,
            label=None,
            labelOpts=None,
    ):
        super().__init__(
            pos, size, symbol, pen, hoverPen, brush, hoverBrush, movable, label, labelOpts
        )

        self.__curve = curve
        self.__curve.sigPlotChanged.connect(self.update_pos)
        self.__edit_bound_target_item_widget = EditBoundTargetItemWidget()
        self.__metadata = ""
        self.__ox_fixation = False

        self.__edit_bound_target_item_widget.apply_signal.connect(self.__update_metadata)

    def fix_on_ox(self):
        self.__ox_fixation = True

    def free_movement_on_ox(self):
        self.__ox_fixation = False

    def update_pos(self):
        cp = self.__closest_point(self.pos())
        if self.__ox_fixation:
            self.setPos(
                QtCore.QPointF(self.pos().x(), cp.y())
            )
        else:
            self.setPos(cp)

    def mouseClickEvent(self, ev):
        if self.moving and ev.button() == QtCore.Qt.MouseButton.RightButton:
            ev.accept()
            self.moving = False
            self.sigPositionChanged.emit(self)
            self.sigPositionChangeFinished.emit(self)
        elif ev.button() == QtCore.Qt.MouseButton.LeftButton:
            self.__edit_bound_target_item_widget.metadata = self.__metadata
            self.__edit_bound_target_item_widget.show()

    def mouseDragEvent(self, ev):
        if not self.movable or ev.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        ev.accept()
        if ev.isStart():
            self.moving = True

        if not self.moving:
            return

        pos = self.mapToView(ev.pos())
        new_pos = self.__closest_point(pos)

        if self.__ox_fixation:
            self.setPos(
                QtCore.QPointF(self.pos().x(), new_pos.y())
            )
        else:
            self.setPos(new_pos)

        if ev.isFinish():
            self.moving = False
            self.sigPositionChangeFinished.emit(self)

    def __update_metadata(self):
        self.__metadata = self.__edit_bound_target_item_widget.metadata

    def __closest_point(
            self,
            point: QtCore.QPointF
    ) -> QtCore.QPointF:
        """
        Находит ближайшую точку на линии.
        """

        bottom_closest_y_i, bottom_closest_y_d = 0, float('inf')
        for i, y in enumerate(self.__curve.yData):
            if y >= point.y():
                continue
            cdy_ = abs(y - point.y())
            if cdy_ < bottom_closest_y_d:
                bottom_closest_y_d = cdy_
                bottom_closest_y_i = i

        upper_closest_y_i, upper_closest_y_d = 0, float('inf')
        for i, y in reversed(list(enumerate(self.__curve.yData))):
            if y <= point.y():
                continue
            cdy_ = abs(y - point.y())
            if cdy_ < upper_closest_y_d:
                upper_closest_y_d = cdy_
                upper_closest_y_i = i

        line_params = get_line_params(
            Point(self.__curve.xData[bottom_closest_y_i], self.__curve.yData[bottom_closest_y_i]),
            Point(self.__curve.xData[upper_closest_y_i], self.__curve.yData[upper_closest_y_i]),
        )
        x = (-line_params[1] * point.y() - line_params[2]) / line_params[0]

        return QtCore.QPointF(x, point.y())

    @property
    def curve(self) -> pg.PlotDataItem:
        return self.__curve

    @property
    def metadata(self) -> str:
        return self.__metadata

    @metadata.setter
    def metadata(self, value):
        self.__metadata = value
