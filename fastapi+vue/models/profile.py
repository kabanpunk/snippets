import copy
import math
import random
from dataclasses import dataclass
from math import sqrt
from typing import List

from pyqtgraph import PlotDataItem, mkPen
from pyqtgraph.Qt import QtCore
from scipy import interpolate
import numpy as np
import scipy.ndimage
import db.models
from models.graphics_items.profile_scatter import ProfileScatter
from models.point import PointType, Point
import pyqtgraph as pg
from utils import int_to_color


@dataclass
class Estimate:
    x: float
    y: float
    val: int
    src: float
    symbol: str = 'o'


class ProfilesManager:
    def __init__(
            self,
            session=None
    ):
        self.__session = session

    def create_profile(
            self,
            step_sp: float,
            step_rp: float,
            start_point: Point,
            end_point: Point,
            name: str = '',
            comment: str = '',
            db_update: bool = False
    ) -> list[db.models.Point]:
        """
        Создание и заполнение случайными данными профиля.
        :param step_sp: шаг источника
        :param step_rp: шаг приёмника
        :param start_point: начальная точка
        :param end_point: конечная точка
        :param name: имя
        :param comment: мета информация,
        :param db_update: проверка нужно ли сразу добавлять профиль в БД,
        """

        print(start_point, end_point)

        line_params = ProfilesManager.__get_line_params(start_point, end_point)

        profile = db.models.Profile(
            name=name,
            description=comment,
            a_coefficient=line_params[0],
            b_coefficient=line_params[1],
            c_coefficient=-line_params[2]
        )
        if db_update:
            self.__session.add(profile)
            self.__session.commit()
            self.__session.refresh(profile)

        source_points = self.__generate_points(
            profile=profile,
            step=step_sp,
            point_type=PointType.SOURCE,
            start_point=start_point,
            end_point=end_point,
            line_params=line_params,
            db_update=db_update
        )
        receiver_points = self.__generate_points(
            profile=profile,
            step=step_rp,
            point_type=PointType.RECEIVER,
            start_point=start_point,
            end_point=end_point,
            line_params=line_params,
            db_update=db_update
        )

        return source_points + receiver_points

    def get_2d_view(
            self,
            points: list,
            with_estimates: bool = False,
            using_interpolate: bool = False
    ) -> tuple[pg.PlotDataItem | pg.ScatterPlotItem, pg.ScatterPlotItem, list[PlotDataItem]]:
        """
        Функция для получения объектов для последующей отрисовки.
        """

        if using_interpolate and not with_estimates:
            raise ValueError("Impossible to interpolate without estimates")

        # Определяем крайние точки
        bottom_left_point = min(points, key=lambda p: (p.x, p.y))
        upper_right_point = max(points, key=lambda p: (p.x, p.y))

        # Определяем сдвиг к центру координат по левой нижней точке
        offset_x = bottom_left_point.x
        offset_y = bottom_left_point.y

        # Находим угол прямой
        dx = upper_right_point.x - offset_x
        dy = upper_right_point.y - offset_y
        theta = math.atan2(dy, dx)
        # Угол в диапазоне (-180,180]
        angle = math.degrees(theta)
        if angle < 0:
            angle = 360 + angle
        alpha = math.radians(angle)

        sources = []
        receivers = []

        for i in range(len(points)):
            points[i].x -= offset_x
            points[i].y -= offset_y

            x_ = points[i].x * math.cos(-alpha) - points[i].y * math.sin(-alpha)
            y_ = points[i].x * math.sin(-alpha) + points[i].y * math.cos(-alpha)

            points[i].x = round(x_, 5)
            points[i].y = round(y_, 5)

            if points[i].type == PointType.SOURCE.value:
                sources.append(
                    points[i]
                )
            elif points[i].type == PointType.RECEIVER.value:
                receivers.append(
                    points[i]
                )

        matrix_size = math.ceil(upper_right_point.x) + 1
        matrix = np.array(
            [[None for i in range(matrix_size)] for j in range(matrix_size)],
            dtype=float
        )

        estimates = []
        dashed_lines = []

        for src_i, src in enumerate(sources):
            for rec_i, rec in enumerate(receivers):
                est = None
                if with_estimates:
                    est = self.__session.query(
                        db.models.Estimate
                    ).filter(
                        db.models.Estimate.source_point_id == src.id,
                        db.models.Estimate.receiver_point_id == rec.id
                    ).one()

                dest = math.sqrt((src.x - rec.x) ** 2 + (src.y - rec.y) ** 2)

                # Находим координаты вершины равнобедренного треугольника,
                #   у к-го медиана равна половине основания.
                if rec.x > src.x:
                    est_x = dest / 2 + src.x
                    est_y = dest / 2 + src.y
                else:
                    est_x = dest / 2 + rec.x
                    est_y = dest / 2 + rec.y

                estimates.append(
                    Estimate(
                        est_x,
                        est_y,
                        100 if est is None else est.value,
                        src.x
                    )
                )

                # Построение пунктирных линий
                if rec_i == 0 or rec_i == len(receivers) - 1:
                    dashed_lines.append(
                        PlotDataItem([est_x, src.x], [est_y, src.y],
                                     pen=mkPen('y', width=0.5, style=QtCore.Qt.DashLine))
                    )

                if with_estimates:
                    # Округляем координаты, чтобы можно было сопоставить ячейку матрицы
                    est_x = round(est_x)
                    est_y = round(est_y)

                    # Работает только если в одну точку попадают два или одно значения,
                    #   по идее больше двух попасть не может, но мало ли.
                    if np.isnan(matrix[est_x][est_y]):
                        matrix[est_x][est_y] = est.value
                    else:
                        matrix[est_x][est_y] += est.value
                        matrix[est_x][est_y] /= 2

        # Проверяем, какой тип вывода нужен пользователю.
        if using_interpolate:
            # Блок с интерполяцией
            x = np.arange(0, matrix.shape[1])
            y = np.arange(0, matrix.shape[0])
            # Создаём маску позиций с NaN'ами
            array = np.ma.masked_invalid(matrix)
            xx, yy = np.meshgrid(x, y)
            # Координаты только валидных позиций
            x1 = xx[~array.mask]
            y1 = yy[~array.mask]
            # Значения всех валидных позиций
            new_arr = array[~array.mask]

            grid_data = interpolate.griddata((x1, y1), new_arr.ravel(),
                                             (xx, yy),
                                             method='nearest',
                                             rescale=True)

            # Размытие по Гауссу
            sigma = [10, 10]
            grid_data = scipy.ndimage.filters.gaussian_filter(grid_data, sigma)

            img_src = np.array(
                [[(0, 0, 0, 0) for i in range(matrix_size)] for j in range(matrix_size)]
            )

            # Середина всего отрезка
            middle_x = math.sqrt(bottom_left_point.x ** 2 + upper_right_point.x ** 2) / 2
            for i in range(matrix_size):
                for j in range(matrix_size):
                    if self.is_point_in_triangle(
                            Point(bottom_left_point.x, 0),
                            Point(middle_x, middle_x),
                            Point(upper_right_point.x, 0),
                            Point(i, j)
                    ):
                        if not np.isnan(grid_data[i][j]):
                            img_src[i][j] = (
                                255 * (1 - grid_data[i][j] / 100),
                                255 * (grid_data[i][j] / 100),
                                0,
                                255
                            )

            img = pg.ImageItem(border='k')
            img.setImage(img_src, border='k')
            result = img
        else:
            result = self.__plot_estimates(estimates)
        return (
            result,
            self.__plot_profile(points),
            dashed_lines
        )

    def __plot_profile(
            self,
            points: List[db.models.Point]
    ) -> ProfileScatter:
        """
        Отрисовка треугольников
        :param points: Преобразованные точки профиля
        :return:
        """
        profile_plot_item = ProfileScatter(
            session=self.__session,
            pxMode=False,
            hoverable=True,
            hoverPen=pg.mkPen('g'),
            hoverSize=4
        )

        points_types_query = self.__session.query(
            db.models.PointType
        ).order_by(
            db.models.PointType.id.asc()
        ).all()

        spots = []

        for point in points:
            spots.append({
                'pos': (point.x, point.y),
                'size': 2 if point.type == 2 else 4,
                'brush': int_to_color(points_types_query[point.type - 1].color, 255),
                'data': point.id,
                'symbol': points_types_query[point.type - 1].symbol
            })
        profile_plot_item.addPoints(spots)
        return profile_plot_item

    def __plot_estimates(
            self,
            estimates: List[Estimate]
    ) -> ProfileScatter:
        """
        Отрисовка только точек отношений.
        :param estimates: Список зависимостей
        :return:
        """
        scatter_plot_item = ProfileScatter(
            session=self.__session,
            pxMode=False,
            hoverable=True,
            hoverPen=pg.mkPen('g'),
            hoverSize=5
        )

        spots = []

        for i in range(len(estimates)):
            for j in range(len(estimates)):
                if i != j and estimates[i].x == estimates[j].x and estimates[i].y == estimates[j].y:
                    if estimates[i].src > estimates[j].src:
                        estimates[i].symbol = 'oh_right'
                    elif estimates[i].src < estimates[j].src:
                        estimates[i].symbol = 'oh_left'

        for est in estimates:
            spots.append({
                'pos': (est.x, est.y),
                'size': 3,
                'brush': (
                    255 * (1 - est.val / 100),
                    255 * (est.val / 100),
                    0,
                    255
                ),
                'data': est.val,
                'symbol': est.symbol
            })
        scatter_plot_item.addPoints(spots)
        return scatter_plot_item

    @staticmethod
    def is_point_in_triangle(
            point1: Point,
            point2: Point,
            point3: Point,
            point: Point
    ) -> bool:
        """
        Проверка, принадлежит ли точка треугольнику.
        Нужно для того, чтобы урезать матрицу с
            экстраполированными значениями до треугольника.
        :param point1: Первая точка треугольника.
        :param point2: Вторая точка треугольника.
        :param point3: Третья точка треугольника.
        :param point: Точка для проверка.
        :return: Соответсвующее булево значение.
        """

        def area(
                point1_: Point,
                point2_: Point,
                point3_: Point,
        ) -> float:
            return abs(
                (
                        point1_.x * (point2_.y - point3_.y) +
                        point2_.x * (point3_.y - point1_.y) +
                        point3_.x * (point1_.y - point2_.y)
                ) / 2.0
            )

        eps = 10e-5
        a = area(point1, point2, point3)
        a1 = area(point, point2, point3)
        a2 = area(point1, point, point3)
        a3 = area(point1, point2, point)
        if abs(a - (a1 + a2 + a3)) < eps:
            return True
        else:
            return False

    def delete_profile(self, profile_id: int):
        profile = self.__session.query(db.models.Profile).filter(
            db.models.Profile.id == profile_id
        ).one()
        self.__session.delete(profile)
        self.__session.commit()

    def fill_estimates_for_one(self, profile_id: int, source_point_id: int):
        profile = self.__session.query(db.models.Profile).filter(
            db.models.Profile.id == profile_id
        ).one()

        receiver_points = self.__session.query(db.models.Point).filter(
            db.models.Point.profile_id == profile_id,
            db.models.Point.type == 2
        ).all()

        base_st = random.randint(0, 100)
        for rp in receiver_points:
            val = base_st + random.randint(-10, 10)
            if val < 0:
                val = 0
            elif val > 100:
                val = 100
            estimate = db.models.Estimate(
                profile_id=profile.id,
                source_point_id=source_point_id,
                receiver_point_id=rp.id,
                value=val
            )
            self.__session.add(estimate)
            self.__session.commit()
            self.__session.refresh(estimate)

    def __generate_points(
            self,
            profile: db.models.Profile,
            step: float,
            point_type: PointType,
            start_point: Point,
            end_point: Point,
            line_params: tuple,
            db_update: bool = False
    ) -> List[db.models.Point]:
        """
        Создание и добавление в БД точек определенного типа в заданном промежутке с шагом.
        :param profile: профиль для добавления точек
        :param step: шаг
        :param point_type: тип добавляемых точек
        :param start_point: начальная точка
        :param end_point: конечная точка
        :param line_params: параметры линии
        :param db_update: проверка, нужно ли сразу добавлять записи в БД
        :return: список точек из объектов моделей БД
        """

        def add_point(
                points_: List[db.models.Point],
                point_: Point
        ) -> None:
            new_point = db.models.Point(
                profile_id=profile.id,
                type=point_type.value,
                x=point_.x,
                y=point_.y
            )
            points_.append(new_point)
            if db_update:
                self.__session.add(new_point)
                self.__session.commit()
                self.__session.refresh(new_point)

        points = []
        add_point(points, start_point)

        point = self.__get_next_point(start_point, end_point, step, line_params)

        while self.__is_between(start_point, end_point, point):
            add_point(points, point)
            point = self.__get_next_point(point, end_point, step, line_params)

        return points

    def __fill_estimates(
            self,
            source_points: List[db.models.Point],
            receiver_points: List[db.models.Point],
            profile: db.models.Profile
    ) -> None:
        """
        Заполнение отношений между точками.
        :param source_points: точки источников
        :param receiver_points: точки приёмников
        :param profile: профиль для добавления
        """
        for sp in source_points:
            base_st = random.randint(0, 100)
            for rp in receiver_points:
                val = base_st + random.randint(-10, 10)
                if val < 0:
                    val = 0
                elif val > 100:
                    val = 100
                estimate = db.models.Estimate(
                    profile_id=profile.id,
                    source_point_id=sp.id,
                    receiver_point_id=rp.id,
                    value=val
                )
                self.__session.add(estimate)
                self.__session.commit()
                self.__session.refresh(estimate)

    @staticmethod
    def __get_next_point(
            point_a: Point,
            point_b: Point,
            step: float,
            line_params: tuple
    ) -> Point:
        """
        Получение точки на расстоянии step от точки point_a на прямой,
            заданной точками point_a и point_b .
        :param point_a: точка от которой идет отсчет
        :param point_b: вторая точка для задания направления
        :param step: шаг
        :param line_params: параметры линии
        :return:
        """

        def dy(step_, k_):
            return k * dx(step_, k_)

        def dx(step_, k_):
            return sqrt(step_ ** 2 / (k_ ** 2 + 1))

        if line_params[1] == 0:
            # случай когда прямая параллельна OY
            if point_a.y < point_b.y:
                return Point(point_a.x, point_a.y + step)
            return Point(point_a.x, point_a.y - step)
        elif line_params[0] == 0 and line_params[2] == 0:
            # случай когда прямая параллельна OX
            if point_a.x < point_b.x:
                return Point(point_a.x + step, point_a.y)
            return Point(point_a.x - step, point_a.y)
        else:
            # все остальные случаи
            k = -line_params[0] / line_params[1]
            if point_a.x < point_b.x:
                return Point(point_a.x + dx(step, k), point_a.y + dy(step, k))
            return Point(point_a.x - dx(step, k), point_a.y - dy(step, k))

    @staticmethod
    def __get_line_params(
            start_point: Point,
            end_point: Point,
    ) -> tuple:
        # TODO: перенести в отдельный класс
        """
        Получение параметров прямой, заданной точками start_point и end_point.
        Параметры a,b,c задают прямую ax+by+c=0.
        :param start_point: начальная точка
        :param end_point: конечная точка
        :return: кортеж из параметров прямой
        """
        a = end_point.y - start_point.y
        b = start_point.x - end_point.x
        c = start_point.y * end_point.x - start_point.x * end_point.y
        return a, b, c

    @staticmethod
    def __is_between(
            point_a: Point,
            point_b: Point,
            point_c: Point
    ) -> bool:
        # TODO: перенести в отдельный класс
        """
        Проверка, лежит ли точка point_c между точками point_a и point_b
        :param point_a: первая точка прямой
        :param point_b: вторая точка прямой
        :param point_c: точка для проверка
        :return: соответсвующее булево значение
        """

        def distance(point_a_, point_b_):
            return sqrt((point_a_.x - point_b_.x) ** 2 + (point_a_.y - point_b_.y) ** 2)

        eps = 10 ** -4
        d = distance(point_a, point_c) + distance(point_c, point_b)
        if d - distance(point_a, point_b) < eps:
            return True
        return False
