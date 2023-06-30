import numpy as np
import scipy
from PyQt5.QtCore import QRunnable, QMetaObject, Qt, QObject, pyqtSlot

from models.line import get_line_params
from models.point import Point


class TracesWorker(QRunnable):
    def __init__(
            self,
            parent: QObject = None,
            traces: np.ndarray = None,
            group_x: np.ndarray = None,
            gain: float = 0,
            clip_s: float = 0.9,
            dt: float = 1,
            w_d: float = 500,
            clipping: bool = False,
    ):
        QRunnable.__init__(self)

        self.__traces = traces
        self.__group_x = group_x
        self.__gain = gain
        self.__clip_s = clip_s
        self.__dt = dt
        self.__w_d = w_d
        self.__clipping = clipping
        self.__data = []

        # Разделил кривые сигнала со вспомогательными данными, для удобства передачи в дочерние классы
        self.__signal_curves = []
        self.__pilot_data = []
        self.__parent = parent

        self.__is_killed = False

        if self.__traces is not None:
            self.__t_b = np.arange(0, len(self.__traces[0, : self.__w_d]) * self.__dt, self.__dt)
            self.__traces = scipy.signal.detrend(self.__traces[::, :self.__w_d])
        else:
            self.__t_b = None

    @property
    def signal_curves(self):
        return self.__signal_curves

    @property
    def pilot_data(self):
        return self.__pilot_data

    @property
    def is_killed(self):
        return self.__is_killed

    def kill(self):
        self.__is_killed = True

    @pyqtSlot()
    def run(self):
        for i in range(len(self.__traces)):
            if self.__is_killed:
                self.__data = []
                QMetaObject.invokeMethod(self.__parent, "__end_of_processing", Qt.QueuedConnection)
                return

            t = np.copy(self.__t_b)
            tr = (self.__traces[i] / self.__traces[i].max()) * self.__gain

            if self.__clipping:
                tr = np.clip(tr, -self.__clip_s, self.__clip_s)

            # Кривая сигнала
            sc = (tr + self.__group_x[i], t)

            # Проходимся по всем x'ам кривой сигнала
            for j, x in enumerate(tr):
                # Если две соседние точки находятся по разные стороны от OY
                if x < 0 < tr[j - 1] or tr[j - 1] < 0 < x:
                    # Получаем параметры прямой, заданной этими двумя точками
                    line_params = get_line_params(
                        Point(x=x, y=t[j]),
                        Point(x=tr[j - 1], y=t[j - 1]),
                    )
                    if line_params[1] == 0:
                        continue
                    # Считаем y-координату точки пересечения прямой и OY
                    y = -line_params[2] / line_params[1]

                    # Добавляем эту точку к уже имеющимся
                    tr = np.append(tr, 0)
                    t = np.append(t, y)

            # Удаляем все точки левее OY
            mask = tr < 0
            tr = tr[~mask]
            t = t[~mask]

            # Восстанавливаем порядок
            t_arg_sorted = t.argsort()
            t = t[t_arg_sorted]
            tr = tr[t_arg_sorted]

            # Создаем кривую (без отрисовки)
            # b_plot = pg.PlotDataItem([st_offset[i]] * len(tr), t, pen=(0, 0, 0))

            # Создаем кривую (без отрисовки), содержащую только "правые" точки
            # t_plot_half = pg.PlotDataItem(tr + st_offset[i], t, pen=(0, 0, 0))

            self.__signal_curves.append(
                sc
            )
            self.__pilot_data.append((
                ([self.__group_x[i]] * len(tr), t),
                (tr + self.__group_x[i], t),
            ))

        # Вызываем обработчик завершения работы worker'а, посылая сигнал родителю.
        QMetaObject.invokeMethod(self.__parent, "__end_of_processing", Qt.QueuedConnection)
