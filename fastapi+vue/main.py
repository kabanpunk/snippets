import sys

from PyQt5 import QtWidgets

from db.init_db import init_db
from resources.launchwindow_ui import Ui_LaunchWindow
from widgets.create_project_form import CreateProjectForm

init_db()

from db import data
import logging.config

logging.config.fileConfig('logging.conf')


class LaunchWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__session = data.Session()

        # Load the UI Page
        self.__ui = Ui_LaunchWindow()
        self.__ui.setupUi(self)

        self.__ui.pushButton_create.clicked.connect(self.__create_project)

    def __create_project(self):
        self.__create_project_form = CreateProjectForm(self.__session)
        self.__create_project_form.show()
        ...


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = LaunchWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
