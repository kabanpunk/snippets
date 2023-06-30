from PyQt5 import QtWidgets
from sqlalchemy.orm import Session

from models.profile import ProfilesManager
from resources.processing_form_ui import Ui_Form

import db.models
from widgets.profiles_window.profiles_plot_widget import ProfilesPlotWidget
from widgets.traces_window import TracesWindow

import copy


class ProcessingForm(QtWidgets.QWidget):
    def __init__(
            self,
            session: Session,
            profile_id: int,
            *args,
            **kwargs
    ):
        """
        Форма для обработки профиля.
        :param session: Текущая сессия SQLAlchemy.
        :param profile_id: ID профиля для обработки.
        """
        super().__init__(*args, **kwargs)
        self.__session = session

        # Загрузка UI страницы
        self.__ui = Ui_Form()
        self.__ui.setupUi(self)

        self.__profiles_manager = ProfilesManager(session=self.__session)

        self.__profile_id = profile_id
        self.__graphWidget = ProfilesPlotWidget()
        self.scatter_plot_item = None
        self.profile_plot_item = None

        self.__ui.gridLayout.addWidget(self.__graphWidget, 0, 0)

        self.__profile = self.__session.query(
            db.models.Profile
        ).filter(
            db.models.Profile.id == self.__profile_id
        ).first()

        self.__last_view_option = True
        self.__ui.pushButton_change_view.clicked.connect(self.__change_view)
        self.__ui.pushButton_read_data.clicked.connect(self.__read_data)

        self.__render_plot(using_interpolate=True)

    def __read_data(self):
        self.traces_window = TracesWindow()
        self.traces_window.show()
        self.traces_window.open_file()

    def __change_view(self):
        self.__last_view_option = not self.__last_view_option
        self.__render_plot(using_interpolate=self.__last_view_option)

    def __render_plot(
            self,
            using_interpolate: bool = False
    ) -> None:
        """
        Основная функция отрисовки.
        :param using_interpolate: Способ отображения.
            true - с использованием интерполяции.
            false - без использования интерполяции.
        :return:
        """
        self.__graphWidget.clear()
        points_ = self.__session.query(
            db.models.Point
        ).filter(
            db.models.Point.profile_id == self.__profile_id
        ).order_by(
            db.models.Point.id.asc()
        ).all()
        points = copy.deepcopy(points_)
        d2, d1, dl = self.__profiles_manager.get_2d_view(points=points, with_estimates=True, using_interpolate=using_interpolate)
        self.__graphWidget.addItem(d2)
        self.__graphWidget.addItem(d1)
        for l in dl:
            self.__graphWidget.addItem(l)

