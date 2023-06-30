from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QDesktopWidget
from resources.parameters_widget_ui import Ui_ParametersWidget


class ParametersWidget(QWidget):
    apply_signal = pyqtSignal()

    def __init__(
            self,
            parent
    ):
        super().__init__()

        # Загрузка UI страницы.
        self.__ui = Ui_ParametersWidget()
        self.__ui.setupUi(self)

        self.__parent = parent

        self.__gain = int(self.__ui.lineEdit_gain.text())
        self.__gain_min = int(self.__ui.lineEdit_gain_min.text())
        self.__gain_max = int(self.__ui.lineEdit_gain_max.text())

        self.__clipping = self.__ui.checkBox_clipping.isChecked()
        self.__w_d = int(self.__ui.lineEdit_w_d.text())
        self.__dt = float(self.__ui.lineEdit_dt.text())
        self.__clip_s = float(self.__ui.lineEdit_clip_s.text())

        self.__ui.pushButton_apply.clicked.connect(self.__pushButton_apply_clicked)
        self.__ui.pushButton_cancel.clicked.connect(self.__pushButton_cancel_clicked)

        sizeObject = QDesktopWidget().screenGeometry(-1)

        self.move((sizeObject.width() - self.__parent.width()) // 2,
                  (sizeObject.height() - self.__parent.height()) // 2)

    def __pushButton_apply_clicked(self):
        self.__gain = int(self.__ui.lineEdit_gain.text())
        self.__gain_min = int(self.__ui.lineEdit_gain_min.text())
        self.__gain_max = int(self.__ui.lineEdit_gain_max.text())
        self.__clipping = self.__ui.checkBox_clipping.isChecked()
        self.__w_d = int(self.__ui.lineEdit_w_d.text())
        self.__dt = float(self.__ui.lineEdit_dt.text())
        self.__clip_s = float(self.__ui.lineEdit_clip_s.text())
        self.apply_signal.emit()

    def __pushButton_cancel_clicked(self):
        self.__ui.lineEdit_gain.setText(str(self.__gain))
        self.__ui.lineEdit_gain_min.setText(str(self.__gain_min))
        self.__ui.lineEdit_gain_max.setText(str(self.__gain_max))
        self.__ui.checkBox_clipping.setChecked(self.__clipping)
        self.__ui.lineEdit_w_d.setText(str(self.__w_d))
        self.__ui.lineEdit_dt.setText(str(self.__dt))
        self.__ui.lineEdit_clip_s.setText(str(self.__clip_s))
        self.close()

    @property
    def gain(self) -> int:
        return self.__gain

    @gain.setter
    def gain(self, value):
        self.__gain = value
        self.__ui.lineEdit_gain.setText(str(self.__gain))

    @property
    def gain_min(self) -> int:
        return self.__gain_min

    @property
    def gain_max(self) -> int:
        return self.__gain_max

    @property
    def clipping(self) -> bool:
        return self.__clipping

    @property
    def w_d(self) -> int:
        return self.__w_d

    @property
    def dt(self) -> float:
        return self.__dt

    @property
    def clip_s(self) -> float:
        return self.__clip_s
