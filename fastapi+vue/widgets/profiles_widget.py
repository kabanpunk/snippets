import os
import sys  # We need sys so that we can pass argv to QApplication

import numpy as np
import pyqtgraph as pg
from enum import Enum
from PIL import Image
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QFileDialog
from pyqtgraph import PlotDataItem
from pyqtgraph.Qt import QtCore
from sqlalchemy.orm import sessionmaker

from models.graphics_items.profile_scatter import ProfileScatter
from models.point import Point, PointType
from models.profile import ProfilesManager
from resources.profiles_window_ui import Ui_ProfilesWindow
from utils import int_to_color
from widgets.create_profile_form import CreateProfileForm
from widgets.edit_point_form import EditPointForm
from widgets.edit_profile_form import EditProfileForm

from db import data
import db.models
import logging
import logging.config

logging.config.fileConfig('logging.conf')


class GraphicalProfileCreationState(Enum):
    INITIAL = 1
    POINT_SELECTION = 2
    ANGLE_SELECTION = 3
    FINAL = 4
    ABORTED = 5


class WorkingMode(Enum):
    INIT = 1
    ONE_PROFILE = 2
    MANY_PROFILES = 3
    SETTING_SCALE = 4


class ProfilesWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__session: sessionmaker = data.Session()

        # Load the UI Page
        self.__ui = Ui_ProfilesWindow()
        self.__ui.setupUi(self)

        self.__background: pg.ImageItem = None
        self.__scale_line_segment: pg.LineSegmentROI = None

        self.__mode = WorkingMode.INIT
        # Проверка, существуют ли уже профили для данного проекта
        profiles: list = self.__session.query(db.models.Profile).order_by(db.models.Profile.id.asc()).all()
        if len(profiles) == 1:
            self.__mode = WorkingMode.ONE_PROFILE
        elif len(profiles) > 1:
            self.__mode = WorkingMode.MANY_PROFILES

        self.__edit_point_form = None
        self.__edit_profile_form = None

        self.__create_profile_form = CreateProfileForm(
            session=self.__session
        )

        self.__plot_widget = self.__ui.plotWidget

        self.__ui.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.__ui.listWidget.itemSelectionChanged.connect(self.refresh_canvas)

        self.__ui.pushButton_edit.clicked.connect(self.pushButton_edit_profile)
        self.__ui.pushButton_add.clicked.connect(self.pushButton_create_profile)
        self.__ui.pushButton_remove.clicked.connect(self.pushButton_remove_profile)
        self.__ui.action_map_settings.triggered.connect(self.__action_map_settings)

        """
            Все что связанно с графическим добавлением профиля
        """
        self.__plot_widget.scene().sigMouseMoved.connect(self.__mouse_moved)
        self.__plot_widget.scene().sigMouseClicked.connect(self.__mouse_clicked)
        self.__new_profile_state = GraphicalProfileCreationState.INITIAL
        self.__new_profile_start_point = QtCore.QPointF()
        self.__new_profile_end_point = QtCore.QPointF()
        self.__new_profile_help_line = QtCore.QPointF()

        self.__profileModel = ProfilesManager(session=self.__session)

        self.refresh_canvas()
        self.refresh_list()

    def __action_map_settings(self):
        self.__ui.stackedWidget.setCurrentIndex(1)
        self.__mode = WorkingMode.SETTING_SCALE
        self.__scale_line_segment = pg.LineSegmentROI([[10, 64], [120, 64]], pen='r')
        self.refresh_canvas()

    def __action_set_map(self):
        dialog = QFileDialog(self)
        dialog.setDirectory(os.path.abspath(os.path.dirname(__file__)))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("PNG Files (*.png)")
        dialog.setViewMode(QFileDialog.ViewMode.Detail)
        if dialog.exec():
            filenames = dialog.selectedFiles()
            if filenames:
                self.__load_map(path=filenames[0])
                self.refresh_canvas()

    def __load_map(self, path='resources/maptest.png'):
        im = np.array(Image.open(path))
        self.__background = pg.ImageItem()
        self.__background.setImage(im)
        tr = QtGui.QTransform()
        tr.scale(1, 1)
        tr.translate(0, 0)
        tr.rotate(-90)
        self.__background.setTransform(tr)
        self.__plot_widget.addItem(self.__background)

    def __create_profile(
            self,
            start_point: QtCore.QPointF = QtCore.QPointF(),
            end_point: QtCore.QPointF = QtCore.QPointF(),
    ):
        self.__create_profile_form = CreateProfileForm(
            session=self.__session,
            start_point=start_point,
            end_point=end_point,
        )
        self.__create_profile_form.show()
        self.__create_profile_form.list_changed.connect(self.refresh_list)
        self.__create_profile_form.plots_changed.connect(self.refresh_canvas)

    def pushButton_create_profile(self):
        self.__create_profile()

    def pushButton_remove_profile(self):
        for item in self.__ui.listWidget.selectedItems():
            self.__ui.listWidget.takeItem(self.__ui.listWidget.row(item))
            self.__profileModel.delete_profile(item.data(1))
        self.refresh_canvas()

    def pushButton_edit_profile(self):
        selected_profiles_ids = [
            item.data(1) for item in self.__ui.listWidget.selectedItems()
        ]
        if len(selected_profiles_ids) == 1:
            self.__edit_profile_form = EditProfileForm(
                session=self.__session,
                profile_id=selected_profiles_ids[0]
            )
            self.__edit_profile_form.show()
            self.__edit_profile_form.list_changed.connect(self.refresh_list)

    def refresh_list(self):
        self.__ui.listWidget.clear()
        profiles = self.__session.query(db.models.Profile).order_by(db.models.Profile.id.asc()).all()
        for profile in profiles:
            list_item = QListWidgetItem(self.__ui.listWidget)
            list_item.setText(profile.name)
            list_item.setData(1, profile.id)
            self.__ui.listWidget.addItem(list_item)

    def __mouse_clicked(self, event):
        def clear_new_profile_creation():
            self.__new_profile_start_point = QtCore.QPointF()
            self.__new_profile_end_point = QtCore.QPointF()
            self.__plot_widget.removeItem(self.__new_profile_help_line)
            self.__new_profile_help_line = QtCore.QPointF()

        modifiers = QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            mouse_point = self.__plot_widget.getViewBox().mapSceneToView(event.scenePos())
            if self.__new_profile_state == GraphicalProfileCreationState.INITIAL:
                self.__new_profile_start_point = mouse_point
                self.__new_profile_state = GraphicalProfileCreationState.ANGLE_SELECTION
            elif self.__new_profile_state == GraphicalProfileCreationState.ANGLE_SELECTION:
                # Завершение создания
                self.__create_profile(
                    start_point=self.__new_profile_start_point,
                    end_point=self.__new_profile_end_point
                )
                clear_new_profile_creation()
                self.__new_profile_state = GraphicalProfileCreationState.INITIAL
        else:
            if self.__new_profile_state == GraphicalProfileCreationState.ANGLE_SELECTION:
                # Отмена создания
                clear_new_profile_creation()
                self.__new_profile_state = GraphicalProfileCreationState.INITIAL

    def __mouse_moved(self, pos: QtCore.QPointF):
        """
        Обработчик события движения мыши.
        :param pos: Абсолютная позиция мыши.
        """
        # Получаем позицию относительно наших координат.
        mouse_point = self.__plot_widget.getViewBox().mapSceneToView(pos)
        if self.__plot_widget.getViewBox().sceneBoundingRect().contains(pos):
            if self.__new_profile_state == GraphicalProfileCreationState.ANGLE_SELECTION:
                self.__new_profile_end_point = mouse_point
                x = [self.__new_profile_start_point.x(), self.__new_profile_end_point.x()]
                y = [self.__new_profile_start_point.y(), self.__new_profile_end_point.y()]
                self.__plot_widget.removeItem(self.__new_profile_help_line)
                self.__new_profile_help_line = PlotDataItem(x, y, pen='g', symbol='x', symbolPen='g',
                                                            symbolBrush=0.2, name='green')
                self.__plot_widget.addItem(self.__new_profile_help_line)

    @pyqtSlot()
    def refresh_canvas(self):
        logging.info('refreshing canvas')

        selected_profiles_ids = [
            item.data(1) for item in self.__ui.listWidget.selectedItems()
        ]

        if selected_profiles_ids is None:
            selected_profiles_ids = []

        self.__plot_widget.clear()
        if self.__background:
            self.__plot_widget.addItem(self.__background)

        if self.__mode == WorkingMode.SETTING_SCALE:
            self.__plot_widget.addItem(self.__scale_line_segment)

        profiles = self.__session.query(db.models.Profile).all()
        for profile in profiles:
            points = self.__session.query(
                db.models.Point.id,
                db.models.Point.profile_id,
                db.models.Point.x,
                db.models.Point.y,
                db.models.Point.type,
                db.models.Point.processed,
                db.models.Point.description,
                db.models.PointType.symbol,
                db.models.PointType.color,
            ).filter(
                db.models.Point.profile_id == profile.id
            ).filter(
                db.models.Point.type == db.models.PointType.id,
            ).order_by(
                db.models.Point.id.asc()
            ).all()

            scatter = ProfileScatter(
                session=self.__session,
                profile_id=profile.id,
                pxMode=False,  # Set pxMode=False to allow spots to transform with the view
                hoverable=True,
                hoverPen=pg.mkPen('g'),
                hoverSize=20
            )
            if profile.id in selected_profiles_ids:
                transparency = 255
                scatter.is_selected = True
            else:
                transparency = 40
                scatter.is_selected = False
                scatter.opts['hoverable'] = False
            spots = []

            for point in points:
                logging.info(point._mapping)
                color = int_to_color(point.color, transparency)
                if PointType(point.type) == PointType.SOURCE:
                    if point.processed:
                        color = (255, 255, 255, transparency)
                    else:
                        color = (255, 255, 0, transparency)

                spots.append({
                    'pos': (point.x, point.y),
                    'size': 10 if point.symbol == 't' else 15,
                    'brush': color,
                    'data': point.id,
                    'symbol': point.symbol
                })
            scatter.addPoints(spots)
            scatter.sigEditPoint.connect(self.on_edit_point)
            self.__plot_widget.addItem(scatter)

    @pyqtSlot(Point, int, int)
    def on_edit_point(
            self,
            point: Point,
            profile_id: int,
            point_id: int):
        self.__edit_point_form = EditPointForm(
            session=self.__session,
            profile_id=profile_id,
            x=point.x,
            y=point.y,
            point_id=point_id
        )
        self.__edit_point_form.show()
        self.__edit_point_form.plots_changed.connect(self.refresh_canvas)
