import os
import sys
import datetime
import mmap
import time
import shutil

from PySide6 import QtCore, QtWidgets, QtGui

from ui.search_form import Ui_MainWindow
from ui.previewWindow import PrevieWindow


class Form_backend(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initUi()
        self.initThreads()

    def initUi(self):
        """
        Инициализация начальных значений для пользовательского интефейса
        """
        self.setWindowTitle('Поиск файлов')
        self.ui.stopSearchpushButton.setEnabled(False)

        self.ui.tableView.setModel(self.createQStandardItemModel()) # добавление заголовков таблицы
        self.ui.tableView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  # изменение ширины первого столбца
        self.ui.tableView.setVisible(False)
        self.ui.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers) # запрет на редактирование ячейки

        self.errorMsg = QtWidgets.QErrorMessage(self)

        # установка параметров для treeView
        model = QtWidgets.QFileSystemModel()
        model.setRootPath(QtCore.QDir.currentPath())
        self.ui.treeView.setModel(model)
        self.ui.treeView.setMinimumSize(300, 200)  # минимальный размер
        self.ui.treeView.setColumnWidth(0, 200)    # ширина первой колонки

        # заполнение entringStringLabel и lineEdit
        self.changeText()

        #слоты
        self.ui.chooseSettingComboBox.currentTextChanged.connect(self.changeText)
        self.ui.startSearchpushButton.clicked.connect(self.startSearchButtonClick)
        self.ui.stopSearchpushButton.clicked.connect(self.stopSearchButtonClick)
        self.ui.treeView.clicked.connect(self.changeDir)

    def initThreads(self):
        """
        инициализация потока
        """
        self.findfileThread = TFindFileThread()
        self.findfileThread.infoSignal.connect(self.addItemToResultTable)
        self.findfileThread.statusSignal.connect(self.showProcessInStatusBar)
        self.findfileThread.finished.connect(self.stopSearchButtonClick)

    def changeText(self):
        """
        устанавливает текст entringStringLabel и lineEdit в зависимости от chooseSettingComboBox
        """
        start_text = 'Введите данные для поиска '
        self.ui.entringStringlineEdit.setText('')
        self.ui.entringStringLabel.setText(start_text+self.ui.chooseSettingComboBox.currentText())
        if str.find(self.ui.entringStringLabel.text(), 'расширению') != -1:
            self.ui.entringStringlineEdit.setPlaceholderText('Задайте расширения файлов вида ".txt" через пробел')
            self.kind_of_search = 1
        elif str.find(self.ui.entringStringLabel.text(), 'сигнатурам') != -1:
            self.ui.entringStringlineEdit.setPlaceholderText('Задайте значение в bin или hex')
            self.kind_of_search = 2
        else:
            self.ui.entringStringlineEdit.setPlaceholderText('ключевое слово')
            self.kind_of_search = 3

    def changeDir(self):
        """
        получение пути к выбранному в treeview каталогу
        """
        model = self.ui.treeView.model()
        dir = QtWidgets.QFileSystemModel(model).filePath(self.ui.treeView.selectedIndexes()[0])
        if os.path.isfile(dir):
            dir = os.path.dirname(dir)
        self.ui.selectedDir_lineEdit.setText(str(dir))

    def setValuesForFindeFileThread(self) -> bool:
        """
        установка начальных значений для потока в зависимости от выбранного вида поиска
        """
        # если не выбрана директория или не заданы условия поска
        if not self.ui.entringStringlineEdit.text().split() or not self.ui.selectedDir_lineEdit.text():
            return False
        #self.findfileThread.recursion = self.ui.recursionSearchcheckBox.checkState()
        self.findfileThread.startDir = self.ui.selectedDir_lineEdit.text()
        self.findfileThread.Flag = True
        if self.kind_of_search == 1:
            self.findfileThread.ext = self.ui.entringStringlineEdit.text().split()
            self.findfileThread.ext_flag = True
            self.findfileThread.flag_signatue = False
            self.findfileThread.flag_keyword = False
            return True

        elif self.kind_of_search == 2:
            # если выбран поиск по сигнатуре файла
            # проверка входных данных - в байтах или в hex задана сигнатура файла
            s = set(self.ui.entringStringlineEdit.text())
            if s <= set('01'):
                self.findfileThread.signature = bytearray(self.ui.entringStringlineEdit.text(), 'ascii')
            elif s <= set('0123456789ABCDEF'):
                self.findfileThread.signature = bytearray.fromhex(self.ui.entringStringlineEdit.text())
            else:
                msg = QtWidgets.QMessageBox()
                msg.setText('Введены некорректные значения')
                msg.exec()
                return False
            self.findfileThread.ext_flag = False
            self.findfileThread.flag_signatue = True
            self.findfileThread.flag_keyword = False

        elif self.kind_of_search == 3:
            # если выбран поиск по ключевому слову
            self.findfileThread.ext_flag = False
            self.findfileThread.flag_signatue = False
            self.findfileThread.flag_keyword = True
            self.findfileThread.keyword = self.ui.entringStringlineEdit.text()

        else:
            return False

        return True




    def startSearchButtonClick(self):
        """
        изменяет состояние визуальных элементов и запускает поток
        """
        if self.ui.tableView.model().rowCount() > 0:
            self.ui.tableView.model().removeRows(0, self.ui.tableView.model().rowCount())
        if self.setValuesForFindeFileThread():
            self.ui.startSearchpushButton.setEnabled(False)
            self.ui.stopSearchpushButton.setEnabled(True)
            self.ui.chooseSettingComboBox.setEnabled(False)
            self.ui.entringStringlineEdit.setEnabled(False)
            #self.ui.recursionSearchcheckBox.setEnabled(False)
            self.findfileThread.start()
            self.ui.tableView.setVisible(True)
            self.ui.statusbar.showMessage('Поиск начат')

    def stopSearchButtonClick(self):
        """
        изменяет состояние визуальных элементов и останавливает поток
        """
        self.ui.startSearchpushButton.setEnabled(True)
        self.ui.stopSearchpushButton.setEnabled(False)
        self.ui.chooseSettingComboBox.setEnabled(True)
        self.ui.entringStringlineEdit.setEnabled(True)
        #self.ui.recursionSearchcheckBox.setEnabled(True)
        self.findfileThread.Flag = False
        self.ui.statusbar.showMessage('Завершено')


    def createQStandardItemModel(self) -> QtGui.QStandardItemModel:
        """
        создание и заполнение заголовка результирующей таблицы
        """
        sim = QtGui.QStandardItemModel()
        sim.setHorizontalHeaderLabels(["Имя файла", "Размер", "Время создания", "Время модификации", "Время последнего доступа"])

        return sim

    def addItemToResultTable(self, info: list):
        """
        Сигнал,добавляет в таблицу информацию о найденных файлах
        """
        list_item = []
        for s in info:
            item = QtGui.QStandardItem(f'{s}')

            list_item.append(item)
        self.ui.tableView.model().appendRow(list_item)

    def showProcessInStatusBar(self, statStr: str):
        """
        Отображение текущего положения дел в потоке
        :param statStr: сообщение из потока
        """
        self.ui.statusbar.showMessage(statStr)

    def event(self, event: QtCore.QEvent) -> bool:
        """
        Обработка событий
        """
        if event.type() == QtCore.QEvent.Close:
            msg = QtWidgets.QMessageBox()
            msg.setText("Вы уверены, что хотите выйти?")
            msg.setInformativeText("")
            msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            reply = msg.exec()
            if reply == QtWidgets.QMessageBox.Yes:
                if self.findfileThread.Flag:
                    self.findfileThread.Flag = False
                    time.sleep(1) # задержка чтобы процесс успел остановиться
                    self.findfileThread.terminate()
                event.accept()
            elif reply == QtWidgets.QMessageBox.No:
                event.ignore()
        return QtWidgets.QWidget.event(self, event)


class TFindFileThread(QtCore.QThread):
    """
    поток поиска файлов
    """
    infoSignal = QtCore.Signal(list)
    statusSignal = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.finished = None
        self.Flag = None
        self.startDir = None
        self.ext = None
        self.ext_flag = False  # флаг отбора файлов по расширению
        self.flag_signatue = False  # флаг отбора по сигнатуре
        self.flag_keyword = False # флаг отбора файлов по ключевому слову
        self.keyword = None
        self.signature = None

    def run(self) -> None:
        if self.Flag is None:
            self.Flag = True
        if self.startDir is None:
            self.startDir = QtCore.QDir.currentPath()
        if self.ext is None:
            self.ext = ['*.*']
        self.run_fast_scandir(self.startDir, self.ext)



    def run_fast_scandir(self, dir, ext) -> list:
        """
        Поиск файлов
        :param dir: стартовая директория
        :param ext: расширения файлов
        :return: спискок найденных подкаталогов
        """
        subfolders, files = [], []

        def add_item():
            """
            передача данных в сигнал
            """
            ctime = datetime.datetime.fromtimestamp(f.stat().st_ctime).strftime("%d-%m-%Y %H:%M:%S")
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d-%m-%Y %H:%M:%S")
            atime = datetime.datetime.fromtimestamp(f.stat().st_atime).strftime("%d-%m-%Y %H:%M:%S")
            self.infoSignal.emit([f.path, f"{f.stat().st_size} байт", ctime, mtime, atime])

        def find_signature() -> bool:
            """
            поиск сигнатуры в файле
            """
            with open(f.path, "rb") as sf:
                if self.signature == sf.read(len(self.signature)):
                    return True
            return False

        def find_string_in_file() -> bool:
            """
            поиск ключевого слова в файле
            """
            # определяем кодировку файла
            self.statusSignal.emit(f'Поиск в файле {f.path}')
            size = f.stat().st_size
            if size == 0:
                return False
            code_file = PrevieWindow.detect_code(f.path, size)

            if code_file is None:
                return False
            search_str = str(self.keyword).encode().decode(code_file)
            search_str = bytearray(search_str, code_file)
            try:
                with open(f.path, "rb") as fb:
                    step = mmap.ALLOCATIONGRANULARITY
                    if size < step:
                        step = size
                    offset = 0
                    map_ = mmap.mmap(fb.fileno(), length=step, access=mmap.ACCESS_READ)
                    while self.Flag:
                        offset += step
                        self.statusSignal.emit(f'Поиск в файле {f.path}')
                        if offset + step > size:
                            map_.close()
                            return False
                        if map_.find(search_str) == -1:
                            map_ = mmap.mmap(fb.fileno(), length=step, offset=offset)
                        else:
                            map_.close()
                            return True

                    map_.close()
                    return False
            except PermissionError:
                print(f"{f.path}: недостаточно прав")
                return False

        try:
            for f in os.scandir(dir):
                self.statusSignal.emit(f'Поиск в директории {dir}')
                if f.is_dir(follow_symlinks=False):
                    subfolders.append(f.path)
                if f.is_file():
                    # проверка отбора по расширению
                    if (ext[0] == '*.*' or os.path.splitext(f.name)[1].lower() in ext) and self.ext_flag:
                        add_item()
                    # проверка отбора по сигнатуре (байтовой строке)
                    if self.flag_signatue and find_signature():
                        add_item()
                    # проверка отбора по ключевой строке
                    if self.flag_keyword and find_string_in_file():
                        add_item()

                if not (self.Flag):
                    os.scandir().close()
                    break
        except PermissionError:
            print(f'Объект {dir} пропущен: недостаточно прав доступа')
            self.statusSignal.emit(f'Объект {dir} пропущен: недостаточно прав доступа')
        return [subfolders, files]


if __name__ == "__main__":
    app = QtWidgets.QApplication()  # Создаем  объект приложения
    # app = QtWidgets.QApplication(sys.argv)  # Если PyQt

    myWindow = Form_backend()  # Создаём объект окна
    myWindow.show()  # Показываем окно

    sys.exit(app.exec_())  # Если exit, то код дальше не исполняется