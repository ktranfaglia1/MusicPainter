#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created: 10/1/2022
Revised: 10/16/2022

@authors: Luke Zolenski, Don Spickler, Kyle Tranfaglia, & Timothy McKirgan

This program is a music/sound visualizer for frequency data from either a wav file or
an input stream from a microphone.  It allows the user to set chunk size and rendering algorithm
and render images based on the wav or stream data.  It also has features to render as the
wav file is playing and to save the streamed music to a wav file.

"""

# System imports.
import platform
import sys
import os
import numpy as np
import wave
import math
from scipy.io import wavfile
from threading import Thread
import sounddevice as sd
import pyaudio
import webbrowser
import time
from PySide2.QtCore import (Qt, QSize, QDir, QPoint, QMarginsF, QRect, QLine, QTimer)
from PySide2.QtGui import (QIcon, QFont, QCursor, QPainter, QColor, QFontMetrics,
                           QMouseEvent, QPageSize, QPageLayout, QPixmap, QBrush)
from PySide2.QtWidgets import (QApplication, QMainWindow, QStatusBar, QPushButton,
                               QToolBar, QDockWidget, QSpinBox, QHBoxLayout,
                               QVBoxLayout, QWidget, QLabel, QScrollArea, QMessageBox,
                               QInputDialog, QFileDialog, QDialog, QAction, QListWidget,
                               QTreeWidget, QSplitter, QAbstractItemView, QTreeWidgetItem,
                               QColorDialog, QFontDialog, QLineEdit, QFrame, QCheckBox,
                               QDialogButtonBox, QComboBox, QDoubleSpinBox, QHeaderView,
                               QTextEdit, QMenu, QStyleFactory, QTabWidget, QSlider)
from PySide2.QtPrintSupport import (QPrintDialog, QPrinter, QPrintPreviewDialog)

# Program imports of our modules.
from PaintBrush import PaintBrush

# For the Mac OS
os.environ['QT_MAC_WANTS_LAYER'] = '1'

class appcss:
    """
    Stylesheet for the program.
    """

    def __init__(self):
        super().__init__()
        self.css = """
            QMenu::separator { 
                background-color: #BBBBBB; 
                height: 1px; 
                margin: 3px 5px 3px 5px;
            }

        """

    def getCSS(self):
        return self.css

class ObjectListViewer(QWidget):
    """
    This is the control for the rendered image.  It takes the geometric data stored in
    the render list produced in the rendering algorithms and plots it. The default
    window is [-1,1] with aspect ratio expansion in one direction.  The control
    also has features for zooming and translation.
    """

    def __init__(self, parent=None, ma=None):
        super(ObjectListViewer, self).__init__(parent)
        self.Parent = parent
        self.mainapp = ma

        self.screen = [-1, 1, -1, 1]
        self.lastRenderListSize = 0
        self.renderAll = True
        self.zoomfactor = 1
        self.center = [0, 0]

        self.mousePosition = [0, 0]
        self.mouseDown = False
        self.setMouseTracking(True)
        self.backgroundcolor = QColor()
        self.backgroundcolor.setRgbF(1, 1, 1, 1)

    def SetBackCol(self):
        self.backgroundcolor = QColorDialog.getColor()
        self.update()

    def resetCenter(self):
        """
        Resets center to the origin.
        """
        self.center = [0, 0]
        self.repaint()

    def resetZoom(self):
        """
        Resets the zoom factor to 1.
        """
        self.zoomfactor = 1
        self.repaint()

    def resetCenterAndZoom(self):
        """
        Resets the center to the origin and zoom factor to 1.
        """
        self.center = [0, 0]
        self.zoomfactor = 1
        self.repaint()

    def mousePressEvent(self, e):
        """
        On a mouse down event on the left button, track its state.
        """
        self.mousePosition = QPoint(e.x(), e.y())
        if e.button() == Qt.LeftButton:
            self.mouseDown = True

    def wheelEvent(self, e) -> None:
        """
        On a mouse wheel event update the zoom factor.
        """
        self.zoomfactor *= (1 + e.delta() / 5000)
        if self.zoomfactor < 1:
            self.zoomfactor = 1
        if self.zoomfactor > 1000:
            self.zoomfactor = 1000
        self.repaint()

    def mouseReleaseEvent(self, e):
        """
        On a mouse up event track its state.
        """
        self.mouseDown = False

    def mouseMoveEvent(self, e):
        """
        On a mouse move event update the zoom factor if the control key is down
        and translate if the control key is not down.
        """
        lastmouseposition = self.mousePosition
        self.mousePosition = QPoint(e.x(), e.y())

        if self.mouseDown:
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                pixmove = (self.mousePosition.x() - lastmouseposition.x()) + (
                        self.mousePosition.y() - lastmouseposition.y())
                self.zoomfactor *= (1 + pixmove / 100)
                if self.zoomfactor < 1:
                    self.zoomfactor = 1
                if self.zoomfactor > 1000:
                    self.zoomfactor = 1000
                self.repaint()
            else:
                xr = self.screen[1] - self.screen[0]
                yr = self.screen[3] - self.screen[2]
                self.center[0] += (self.mousePosition.x() - lastmouseposition.x()) * xr / self.width()
                self.center[1] += (self.mousePosition.y() - lastmouseposition.y()) * yr / self.height()
                self.repaint()

    def XYtoQPoint(self, x, y):
        """
        Covert real coordinates to screen coordinates.
        """
        xr = self.screen[1] - self.screen[0]
        yr = self.screen[3] - self.screen[2]
        # ptx = x / xr * self.width() + self.width() / 2
        # pty = -y / yr * self.height() + self.height() / 2
        ptx = (x + self.center[0]) / xr * self.width() + self.width() / 2
        pty = (self.center[1] - y) / yr * self.height() + self.height() / 2
        return QPoint(ptx, pty)

    def updateScreenBounds(self):
        """
        Update the screen bounds based on the center and zoom factor being used.
        """
        fullscreen = [-1, 1, -1, 1]
        ww = self.width()
        wh = self.height()
        if ww >= wh:
            fullscreen = [-ww / wh, ww / wh, -1, 1]
        else:
            fullscreen = [-1, 1, -wh / ww, wh / ww]
        for i in range(4):
            fullscreen[i] = fullscreen[i] * (1 / self.zoomfactor)
        self.screen[0] = self.center[0] - fullscreen[1]
        self.screen[1] = self.center[0] + fullscreen[1]
        self.screen[2] = self.center[1] - fullscreen[3]
        self.screen[3] = self.center[1] + fullscreen[3]

    def RenderPoint(self, qp, obj):
        """
        Draw a point to the screen.
        """
        qp.setPen(obj[3])
        qp.drawPoint(self.XYtoQPoint(obj[1], obj[2]))

    def RenderLine(self, qp, obj):
        """
        Draw a line to the screen.
        """
        qp.setPen(obj[5])
        pt1 = self.XYtoQPoint(obj[1], obj[2])
        pt2 = self.XYtoQPoint(obj[3], obj[4])
        line = QLine(pt1, pt2)
        qp.drawLine(line)

    def RenderCircle(self, qp, obj):
        """
        Draw a circle to the screen.
        """
        qp.setPen(obj[5])
        ulpt = self.XYtoQPoint(obj[1] - obj[3], obj[2] + obj[3])
        lrpt = self.XYtoQPoint(obj[1] + obj[3], obj[2] - obj[3])
        # rect = QRect(ulpt.x(), ulpt.y(), lrpt.x() - ulpt.x(), lrpt.y() - ulpt.y())
        rect = QRect(ulpt, lrpt)
        if obj[4]:
            qp.setBrush(obj[5])
            qp.drawEllipse(rect)
            qp.setBrush(QColor(0, 0, 0, 0))
        else:
            qp.drawEllipse(rect)

    def RendeRectangle(self, qp, obj):
        """
        Draw a rectangle to the screen.
        """
        qp.setPen(obj[6])
        ulpt = self.XYtoQPoint(obj[1], obj[2])
        lrpt = self.XYtoQPoint(obj[3], obj[4])
        # rect = QRect(ulpt.x(), ulpt.y(), lrpt.x() - ulpt.x(), lrpt.y() - ulpt.y())
        rect = QRect(ulpt, lrpt)
        if obj[5]:
            qp.fillRect(rect, obj[6])
        else:
            qp.drawRect(rect)

    def RenderTriangle(self, qp, obj):
        if obj[7]:
            self.RiemannFill(qp, obj)
            # self.FanFill(qp, obj)
        else:
            obj1 = [1, obj[1], obj[2], obj[3], obj[4], obj[8]]
            obj2 = [1, obj[3], obj[4], obj[5], obj[6], obj[8]]
            obj3 = [1, obj[5], obj[6], obj[1], obj[2], obj[8]]
            self.RenderLine(qp, obj1)
            self.RenderLine(qp, obj2)
            self.RenderLine(qp, obj3)

    def RiemannFill(self, qp, obj):
        Resolution = 250
        Range = abs(obj[1] - obj[5])
        MidPoint = obj[3]
        MidPointY = obj[4]
        if (obj[1] > obj[5]):
            BegPoint = obj[5]
            BegPointY = obj[6]
            EndPoint = obj[1]
            EndPointY = obj[2]
        else:
            BegPoint = obj[1]
            BegPointY = obj[2]
            EndPoint = obj[5]
            EndPointY = obj[6]
        for i in range(2):
            if (abs(obj[(i * 2) + 1] - obj[((i + 1) * 2) + 1]) > Range):
                Range = abs(obj[(i * 2) + 1] - obj[((i + 1) * 2) + 1])
                if (i * 2 + 1) == 1:
                    MidPoint = obj[5]
                    MidPointY = obj[6]
                    if (obj[1] > obj[3]):
                        BegPoint = obj[3]
                        BegPointY = obj[4]
                        EndPoint = obj[1]
                        EndPointY = obj[2]
                    else:
                        BegPoint = obj[1]
                        BegPointY = obj[2]
                        EndPoint = obj[3]
                        EndPointY = obj[4]
                elif (i * 2 + 1) == 3:
                    MidPoint = obj[1]
                    MidPointY = obj[2]
                    if (obj[3] > obj[5]):
                        BegPoint = obj[5]
                        BegPointY = obj[6]
                        EndPoint = obj[3]
                        EndPointY = obj[4]
                    else:
                        BegPoint = obj[3]
                        BegPointY = obj[4]
                        EndPoint = obj[5]
                        EndPointY = obj[6]
        width = Range / Resolution
        for i in range(Resolution):
            StartingX = BegPoint + (i * width)
            EndingX = BegPoint + ((i + 1) * width)
            if EndPoint == MidPoint:
                EndingY = ((((MidPointY - BegPointY) / (MidPoint - BegPoint)) * (EndingX - BegPoint)) + BegPointY)
                StartingY = ((((EndPointY - BegPointY) / (EndPoint - BegPoint)) * (StartingX - BegPoint)) + BegPointY)
            elif BegPoint == MidPoint:
                EndingY = ((((EndPointY - BegPointY) / (EndPoint - BegPoint)) * (EndingX - BegPoint)) + BegPointY)
                StartingY = ((((EndPointY - MidPointY) / (EndPoint - MidPoint)) * (StartingX - MidPoint)) + MidPointY)
            else:
                EndingY = ((((EndPointY - BegPointY) / (EndPoint - BegPoint)) * (EndingX - BegPoint)) + BegPointY)
                if (StartingX >= MidPoint):
                    StartingY = ((((EndPointY - MidPointY) / (EndPoint - MidPoint)) * (
                            StartingX - MidPoint)) + MidPointY)
                else:
                    StartingY = ((((MidPointY - BegPointY) / (MidPoint - BegPoint)) * (
                            StartingX - BegPoint)) + BegPointY)
            objFill = [3, StartingX, StartingY, EndingX, EndingY, True, obj[8]]
            self.RendeRectangle(qp, objFill)

    def paintEvent(self, event):
        """
        Paint event override, clears the screen, loops through the render list of
        objects, and draws a border around the image.
        """
        self.updateScreenBounds()
        rl = self.mainapp.rl

        qp = QPainter()
        qp.begin(self)

        renderstart = 0
        if self.renderAll:
            # Clear Screen
            qp.fillRect(0, 0, self.width(), self.height(), self.backgroundcolor)
        else:
            renderstart = self.lastRendetListSize

        for i in range(renderstart, rl.length()):
            obj = rl.get(i)
            if obj[0] == 0:
                self.RenderPoint(qp, obj)
            elif obj[0] == 1:
                self.RenderLine(qp, obj)
            elif obj[0] == 2:
                self.RenderCircle(qp, obj)
            elif obj[0] == 3:
                self.RendeRectangle(qp, obj)
            elif obj[0] == 4:
                self.RenderTriangle(qp, obj)

        outline = QColor()
        outline.setRgb(0, 0, 0, 255)
        qp.setPen(outline)
        qp.drawRect(0, 0, self.width() - 1, self.height() - 1)
        qp.end()
        self.lastRenderListSize = rl.length()


class RenderList:
    """
    Convenience class for storing a list of items to be rendered.
    """
    def __init__(self):
        self.renderlist = []

    def add(self, item):
        self.renderlist.append(item)

    def clear(self):
        self.renderlist = []

    def length(self):
        return len(self.renderlist)

    def get(self, i):
        if i < 0 or i >= len(self.renderlist):
            return None
        return self.renderlist[i]

class MusicPainter(QMainWindow):
    """
    Main program application window.
    """

    def __init__(self, parent=None):
        super().__init__()
        self.Parent = parent
        self.mainapp = self
        self.setAcceptDrops(True)
        # self.setStyleSheet('Background-color: grey;')

        # About information for the app.
        self.authors = "Luke Zolenski, Don Spickler, Kyle Tranfaglia, & Timothy McKirgan"
        self.version = "1.1.1"
        self.program_title = "Music Painter"
        self.copyright = "2023"

        # Set GUI style
        self.Platform = platform.system()
        styles = QStyleFactory.keys()
        if "Fusion" in styles:
            app.setStyle('Fusion')

        # Set recording constants
        self.RECORDFORMAT = pyaudio.paInt16
        self.RECORDCHANNELS = 2
        self.RECORDRATE = 44100
        self.fullrecording = None

        # Setup Global Objects
        self.freqlist = None
        self.clipboard = QApplication.clipboard()
        self.rl = RenderList()
        self.paintbrush = PaintBrush(self)
        self.loadedFilename = ""
        self.loadedFiles = []
        self.titleoverridetext = ""
        self.music_thread = None
        self.playsoundstop = False
        self.initializeUI()
        self.volumeMultiplier = 0.5
        self.chooseAudioDevice()
        # self.createLeftToolBar()

        # Set Animation blink flag and timer
        self.flag = True
        self.timer = QTimer(self, interval=1000)
        self.timer.timeout.connect(self.AnimateRecordButton)
        # self.timer1Flag = False
        # self.timer1 = QTimer(self, interval=500)
        # self.timer1.timeout.connect(self.setFlag)
        self.algorithmFlag = True

    # https://gist.github.com/peace098beat/db8ef7161508e6500ebe
    # Author: Terraskull
    # Last Updated: 11/27/2020

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    # https://gist.github.com/peace098beat/db8ef7161508e6500ebe
    # Author: Terraskull
    # Last Updated: 11/27/2020

    def dropEvent(self, event):
        mp3FileDetected = False
        NoFilesLoaded = True
        FileString = ""
        PotentialFiles = []
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            FileString += f
        TestString = FileString + "."
        TestString = TestString[-5:-1]
        if (TestString == ".wav"):
            self.loadedFilename = FileString
            self.updateProgramWindowTitle()
            NoFilesLoaded = False
        elif (TestString == ".mp3"):
            mp3FileDetected = True
        elif (os.path.isdir(FileString)):
            for filename in os.listdir(FileString):
                f = os.path.join(FileString, filename)
                TestString = f + "."
                TestString = TestString[-5:-1]
                if (os.path.isfile(f) and TestString == ".wav"):
                    PotentialFiles.append(f)
                elif (os.path.isfile(f) and TestString == ".mp3"):
                    mp3FileDetected = True
            if (len(PotentialFiles) > 0):
                NoFilesLoaded = False
                self.loadedFiles = PotentialFiles
                self.ChosenFile.clear()
                for i in range(len(self.loadedFiles)):
                    self.ChosenFile.addItem(self.loadedFiles[i])
        if (mp3FileDetected):
            QMessageBox.information(self, ".mp3 Files not Compatible",
                                    "Convert your file to a .wav for use with this program.", QMessageBox.Ok)
        elif (NoFilesLoaded):
            QMessageBox.warning(self, "No Files Loaded",
                                "Open a Directory that contains .wav files or a Wav File to load into the program.",
                                QMessageBox.Ok)

    # Opens the help page
    def openURL(self):
        webbrowser.open('https://musicpainterwebsite2023.on.drv.tw/musicpainter/Help.html')

    # Adjoin a relative path for icons and help system.
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    # Updates the title bar to contain the loaded file path or test.
    def updateProgramWindowTitle(self):
        title = self.program_title
        if self.titleoverridetext != "":
            title = title + " - " + self.titleoverridetext
        elif self.loadedFilename != "":
            title = title + " - " + self.loadedFilename
        self.setWindowTitle(title)

    # Sets the display name of the selected file
    def SetFile(self):
        if (len(self.loadedFiles) >= 1):
            self.loadedFilename = self.loadedFiles[self.ChosenFile.currentIndex()]
            self.updateProgramWindowTitle()
        else:
            self.loadedFilename = ""

    def chooseAudioDevice(self):
        self.dlg = QDialog(self)
        self.dlg.setFixedSize(450,300)
        self.dlg.setWindowTitle("Choose an Audio Input Device")

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("Apply",QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel",QDialogButtonBox.RejectRole)

        self.tempIndex = self.InputAudioDevices.currentIndex()
        self.tempIndex1 = self.OutputAudioDevices.currentIndex()
        self.tempIndex2 = self.volumeMultiplier

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.dlg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.format = QVBoxLayout()
        self.format.addStretch()

        label1 = QLabel("Input Audio Devices: ")
        label1.setStyleSheet("font-size: 9pt;")
        label2 = QLabel("No Audio Input Devices Detected")
        label2.setStyleSheet("font-size: 9pt; font-weight: bold")
        label3 = QLabel("Output Audio Devices: ")
        label3.setStyleSheet("font-size: 9pt;")
        label4 = QLabel("No Audio Output Devices Detected")
        label4.setStyleSheet("font-size: 9pt; font-weight: bold")

        if (self.inputDeviceCount > 0):
            self.format.addWidget(label1, alignment=Qt.AlignCenter)
            self.format.addWidget(self.InputAudioDevices, alignment=Qt.AlignCenter)
        else:
            self.format.addWidget(label2, alignment=Qt.AlignCenter)

        self.format.addSpacing(25)

        if (self.outputDeviceCount > 0):
            self.format.addWidget(label3, alignment=Qt.AlignCenter)
            self.format.addWidget(self.OutputAudioDevices, alignment=Qt.AlignCenter)
        else:
            self.format.addWidget(label4, alignment=Qt.AlignCenter)

        self.volumeLabel = QLabel(f'Volume: {int(self.volumeMultiplier * 100)}%', self)
        self.volumeSlider = QSlider(Qt.Horizontal, self)
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(self.volumeMultiplier * 100)
        self.volumeSlider.valueChanged.connect(self.changeVolume)

        self.format.addSpacing(25)
        self.format.addWidget(self.volumeLabel)
        self.format.addWidget(self.volumeSlider)

        self.format.addStretch()
        self.format.addSpacing(10)
        self.format.addWidget(self.buttonBox)

        self.dlg.setLayout(self.format)
        self.dlg.exec()

    def accept(self):
        self.dlg.close()

    def reject(self):
        self.InputAudioDevices.setCurrentIndex(self.tempIndex)
        self.OutputAudioDevices.setCurrentIndex(self.tempIndex1)
        self.volumeMultiplier = self.tempIndex2
        self.dlg.close()

    # Initialize the window, calls create methods to set up the GUI.
    def initializeUI(self):
        self.canvas = ObjectListViewer(self, self)
        self.setMinimumSize(950, 700)
        self.updateProgramWindowTitle()
        icon = QIcon(self.resource_path("icons/Logo-blackv2.png"))
        self.setWindowIcon(icon)

        self.clearButton = QPushButton()
        self.clearButton.setStyleSheet('Background-color: #d1e7f0')
        self.clearButton.setText('Clear Image')
        # self.clearButton.setFixedSize(90, 28)
        self.clearButton.clicked.connect(self.clearImage)

        self.ColorButton = QPushButton()
        self.ColorButton.setStyleSheet('Background-color: #fac8c9')
        self.ColorButton.setText('Background Color')
        # self.ColorButton.setFixedSize(120, 28)
        self.ColorButton.clicked.connect(self.canvas.SetBackCol)

        self.DirectorySelect = QPushButton()
        self.DirectorySelect.setStyleSheet('Background-color: #f5f0d0')
        self.DirectorySelect.setText('Open Directory')
        # self.DirectorySelect.setFixedSize(100, 28)
        self.DirectorySelect.clicked.connect(self.openDirectory)

        self.ChosenFile = QComboBox()
        # self.ChosenFile.setFixedSize(90, 28)
        for i in range(len(self.loadedFiles)):
            self.ChosenFile.addItem(self.loadedFiles[i])

        self.ChosenFile.currentIndexChanged.connect(self.SetFile)

        self.algorithmNum = QComboBox()
        # self.algorithmNum.setFixedSize(130, 28)
        # for i in range(self.paintbrush.numberAlgorithms):
        #     self.algorithmNum.addItem(str(i + 1))

        self.algorithmNum.addItem(str('Frequency Dots'))
        self.algorithmNum.addItem(str('Dynamite'))
        self.algorithmNum.addItem(str('Ball of Yarn'))
        self.algorithmNum.addItem(str('3-D Symmetry'))
        self.algorithmNum.addItem(str('Spirograph'))
        self.algorithmNum.addItem(str('Colorful Void'))
        self.algorithmNum.addItem(str('Vortex'))
        self.algorithmNum.addItem(str('Illuminate Snake'))
        self.algorithmNum.addItem(str('Triangle Stacker'))
        self.algorithmNum.addItem(str('Spiraling Circles'))
        self.algorithmNum.addItem(str('Circulating Squares'))
        self.algorithmNum.addItem(str('Sporadic Squares'))
        self.algorithmNum.addItem(str('Emotional Progression'))

        self.algorithmNum.currentIndexChanged.connect(self.resetRLData)

        self.ChunkSizesList = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
        self.chunkSize = QComboBox()
        # self.chunkSize.setFixedSize(130, 28)
        for val in self.ChunkSizesList:
            self.chunkSize.addItem(str(val))
        self.chunkSize.setCurrentIndex(4)

        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        self.InputAudioDevices = QComboBox()
        self.InputAudioDevices.setFixedSize(260, 30)
        self.inputDeviceCount = 0

        self.OutputAudioDevices = QComboBox()
        self.OutputAudioDevices.setFixedSize(260, 30)
        self.outputDeviceCount = 0

        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                self.InputAudioDevices.addItem(str(p.get_device_info_by_host_api_device_index(0, i).get('name')))
                self.inputDeviceCount += 1
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
                self.OutputAudioDevices.addItem(str(p.get_device_info_by_host_api_device_index(0, i).get('name')))
                self.outputDeviceCount += 1

        self.createMenu()
        self.createToolBar()
        self.createSecondaryToolBar()

        # self.statusBar = QStatusBar()
        # self.setStatusBar(self.statusBar)
        self.addDockWidget(Qt.TopDockWidgetArea, self.leftWidget)

        self.setCentralWidget(self.canvas)
        self.show()

    def resetRLData(self):
        if (self.algorithmNum.currentIndex() == 5):
            self.paintbrush.SetAlg6()
        elif (self.algorithmNum.currentIndex() == 1 or self.algorithmNum.currentIndex() == 2 or self.algorithmNum.currentIndex() == 3
              or self.algorithmNum.currentIndex() == 4):
            self.paintbrush.SetAlg2345()
        elif (self.algorithmNum.currentIndex() == 6):
            self.paintbrush.SetAlg7()
        elif (self.algorithmNum.currentIndex() == 7):
            self.paintbrush.SetAlg8()
        elif (self.algorithmNum.currentIndex() == 8):
            self.paintbrush.SetAlg9()
        elif (self.algorithmNum.currentIndex() == 9):
            self.paintbrush.SetAlg10()
        elif (self.algorithmNum.currentIndex() == 12):
            self.paintbrush.SetAlg13()

        current = self.chunkSize.currentIndex()

        if ((self.algorithmNum.currentIndex() == 5) or (self.algorithmNum.currentIndex() == 8)):
            if self.ChunkSizesList[0] == 1024:
                ListChanged = True
            else:
                ListChanged = False
            self.ChunkSizesList = [16384, 32768, 65536, 131072]
            self.chunkSize.clear()
            for val in self.ChunkSizesList:
                self.chunkSize.addItem(str(val))
            if ListChanged:
                if current >= 5 and current <= 7:
                    self.chunkSize.setCurrentIndex(current - 4)
                else:
                    self.chunkSize.setCurrentIndex(0)
            else:
                self.chunkSize.setCurrentIndex(current)
        else:
            if self.ChunkSizesList[0] == 16384:
                ListChanged = True
            else:
                ListChanged = False
            self.ChunkSizesList = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
            self.chunkSize.clear()
            for val in self.ChunkSizesList:
                self.chunkSize.addItem(str(val))
            if ListChanged:
                if current >= 1 and current <= 3:
                    self.chunkSize.setCurrentIndex(current + 4)
                else:
                    self.chunkSize.setCurrentIndex(4)
            else:
                self.chunkSize.setCurrentIndex(current)

    # Setup all menu and toolbar actions as well as create the menu.
    def createMenu(self):
        self.file_open_act = QAction(QIcon(self.resource_path('icons/48x48/OpenFile.png')), "&Open Wav File...", self)
        # self.file_open_act = QAction(QIcon(self.resource_path('OpenFile.png')), "&Open Wav File...", self)
        self.file_open_act.setShortcut('Ctrl+O')
        self.file_open_act.triggered.connect(self.openFile)
        self.file_open_act.setStatusTip("Open a wav file for rendering.")

        self.printImage_act = QAction(QIcon(self.resource_path('icons/48x48/Printer.png')), "&Print...", self)
        # self.printImage_act = QAction(QIcon(self.resource_path('Printer.png')), "&Print...", self)
        self.printImage_act.setShortcut('Ctrl+P')
        self.printImage_act.triggered.connect(self.printImage)
        self.printImage_act.setStatusTip("Print the image.")

        self.printPreviewImage_act = QAction(QIcon(self.resource_path('icons/48x48/Printer-View.png')),
                                             "Print Pre&view...", self)
        # self.printPreviewImage_act = QAction(QIcon(self.resource_path('Printer-View.png')), "Print Pre&view...", self)
        self.printPreviewImage_act.triggered.connect(self.printPreviewImage)
        self.printPreviewImage_act.setStatusTip("Print preview the image.")

        quit_act = QAction("E&xit", self)
        quit_act.triggered.connect(self.close)
        quit_act.setStatusTip("Shut down the application.")

        self.copyImage_act = QAction(QIcon(self.resource_path('icons/48x48/Copy.png')), "Copy &Image", self)
        # self.copyImage_act = QAction(QIcon(self.resource_path('Copy.png')), "Copy &Image", self)
        self.copyImage_act.setShortcut('Ctrl+C')
        self.copyImage_act.triggered.connect(self.copyImageToClipboard)
        self.copyImage_act.setStatusTip("Copy the image to the clipboard.")

        self.saveImage_act = QAction(QIcon(self.resource_path('icons/48x48/Download-Blue.png')), "Save Image &As...",
                                     self)
        # self.saveImage_act = QAction(QIcon(self.resource_path('Download-Blue.png')), "Save Image &As...", self)
        self.saveImage_act.triggered.connect(self.saveAsImage)
        self.saveImage_act.setStatusTip("Save the image.")

        self.render_act = QAction(QIcon(self.resource_path('icons/48x48/Brush-Purple.png')), "&Render", self)
        # self.render_act = QAction(QIcon(self.resource_path('Brush-Purple.png')), "&Render", self)
        self.render_act.triggered.connect(self.renderImage)
        self.render_act.setStatusTip("Render the image.")

        self.clear_act = QAction("&Clear Image", self)
        self.clear_act.triggered.connect(self.clearImage)
        self.clear_act.setStatusTip("Clear the image.")

        self.setColor = QAction("Background Color", self)
        self.setColor.triggered.connect(self.canvas.SetBackCol)
        self.setColor.setStatusTip("Choose background color for image.")

        self.dir_open_act = QAction("Open Directory", self)
        self.dir_open_act.triggered.connect(self.openDirectory)
        self.dir_open_act.setStatusTip("Open directory containing .wav files.")

        self.resetCenter_act = QAction(QIcon(self.resource_path('icons/48x48/Center.png')), "Reset Center", self)
        # self.resetCenter_act = QAction(QIcon(self.resource_path('Center.png')), "Reset Center", self)
        self.resetCenter_act.triggered.connect(self.canvas.resetCenter)
        self.resetCenter_act.setStatusTip("Reset the center to the origin.")

        self.resetZoom_act = QAction(QIcon(self.resource_path('icons/48x48/Zoom.png')), "Reset Zoom", self)
        # self.resetZoom_act = QAction(QIcon(self.resource_path('Zoom.png')), "Reset Zoom", self)
        self.resetZoom_act.triggered.connect(self.canvas.resetZoom)
        self.resetZoom_act.setStatusTip("Reset the zoom factor to 1.")

        self.resetCenterZoom_act = QAction(QIcon(self.resource_path('icons/48x48/ZoomCenter.png')),
                                           "Reset Center and Zoom", self)
        # self.resetCenterZoom_act = QAction(QIcon(self.resource_path('ZoomCenter.png')), "Reset Center and Zoom", self)
        self.resetCenterZoom_act.triggered.connect(self.canvas.resetCenterAndZoom)
        self.resetCenterZoom_act.setStatusTip("Reset the center to the origin and zoom factor to 1.")

        self.properties_act = QAction(QIcon(self.resource_path('icons/48x48/InfoCard.png')), "File &Information...",
                                      self)
        # self.properties_act = QAction(QIcon(self.resource_path('InfoCard.png')), "File &Information...",self)
        self.properties_act.triggered.connect(self.SoundDataProperties)
        self.properties_act.setStatusTip("View the wav file information.")

        self.play_act = QAction(QIcon(self.resource_path('icons/48x48/Play.png')), "Render and &Play", self)
        # self.play_act = QAction(QIcon(self.resource_path('Play.png')), "Render and &Play", self)
        self.play_act.triggered.connect(self.PlaySoundData)
        self.play_act.setStatusTip("Render the image while playing the wav file.")

        self.stop_act = QAction(QIcon(self.resource_path('icons/48x48/Stop-Center.png')), "&Stop Render", self)
        # self.stop_act = QAction(QIcon(self.resource_path('Stop-Center.png')), "&Stop Render", self)
        self.stop_act.triggered.connect(self.StopSoundData)
        self.stop_act.setStatusTip("Stop the rendering of the image.")

        self.selectaudiodevice_act = QAction(QIcon(self.resource_path('icons/48x48/Microphone.png')),
                                             "&Choose Audio Device", self)
        # self.record_act = QAction(QIcon(self.resource_path('Record.png')), "&Record", self)
        self.selectaudiodevice_act.triggered.connect(self.chooseAudioDevice)
        self.selectaudiodevice_act.setStatusTip("Choose an audio input device for recording.")

        self.record_act = QAction(QIcon(self.resource_path('icons/48x48/Record.png')), "&Record", self)
        # self.record_act = QAction(QIcon(self.resource_path('Record.png')), "&Record", self)
        self.record_act.triggered.connect(self.RecordSoundData)
        self.record_act.setStatusTip("Record sound and render image.")

        self.saverecording_act = QAction(QIcon(self.resource_path('icons/48x48/Download.png')), "&Save Recording", self)
        # self.saverecording_act = QAction(QIcon(self.resource_path('Download.png')), "&Save Recording", self)
        self.saverecording_act.triggered.connect(self.SaveRecording)
        self.saverecording_act.setStatusTip("Save recorded sound to wav file.")

        self.stoprecord_act = QAction(QIcon(self.resource_path('icons/48x48/Pause.png')), "&Stop Recording", self)
        # self.stoprecord_act = QAction(QIcon(self.resource_path('Pause.png')), "&Stop Recording", self)
        self.stoprecord_act.triggered.connect(self.StopRecordData)
        self.stoprecord_act.setStatusTip("Stop recording.")

        selectTheme_act = QAction("&Theme...", self)
        selectTheme_act.triggered.connect(self.SelectTheme)

        # Create help menu actions
        self.help_about_act = QAction(QIcon(self.resource_path('icons/48x48/Information.png')), "&About...", self)
        # self.help_about_act = QAction(QIcon(self.resource_path('Information.png')), "&About...", self)
        self.help_about_act.triggered.connect(self.aboutDialog)
        self.help_about_act.setStatusTip("Information about the program.")

        self.help_website_act = QAction(QIcon(self.resource_path('icons/48x48/Help.png')), "&Help", self)
        self.help_website_act.triggered.connect(self.openURL)
        self.help_website_act.setStatusTip("Help (Opens External Link)")

        self.website_link = QAction(QIcon(self.resource_path('icons/48x48/help.png')), "&Help Webpage", self)
        self.website_link.triggered.connect(self.openURL)
        self.website_link.setStatusTip("Opens Help Page on Music Painter Website")

        # Create the menu bar
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        # Create file menu and add actions
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.file_open_act)
        file_menu.addAction(self.properties_act)
        file_menu.addAction(self.render_act)
        file_menu.addAction(self.play_act)
        file_menu.addAction(self.stop_act)
        file_menu.addSeparator()
        file_menu.addAction(quit_act)

        record_menu = menu_bar.addMenu('&Record')
        record_menu.addAction(self.selectaudiodevice_act)
        record_menu.addAction(self.record_act)
        record_menu.addAction(self.stoprecord_act)
        record_menu.addAction(self.saverecording_act)

        image_menu = menu_bar.addMenu('&Image')
        image_menu.addAction(self.copyImage_act)
        image_menu.addAction(self.saveImage_act)
        image_menu.addSeparator()
        image_menu.addAction(self.printImage_act)
        image_menu.addAction(self.printPreviewImage_act)
        image_menu.addSeparator()
        image_menu.addAction(self.resetCenter_act)
        image_menu.addAction(self.resetZoom_act)
        image_menu.addAction(self.resetCenterZoom_act)
        image_menu.addSeparator()

        help_menu = menu_bar.addMenu('&Help')
        help_menu.addAction(self.help_about_act)
        help_menu.addAction(self.website_link)

    def createSecondaryToolBar(self):

        self.leftWidget = QDockWidget()
        self.leftWidget.setStyleSheet("QDockWidget::title" "{" "background : lightblue;" "}")
        self.leftWidget.setFeatures(self.leftWidget.DockWidgetFloatable | self.leftWidget.DockWidgetMovable)

        layoutWidget = QWidget()
        layout = QHBoxLayout()

        layout.addStretch()
        layout.addWidget(self.clearButton, 0, Qt.AlignRight)
        layout.addWidget(QLabel("Algorithm:"), 0, Qt.AlignRight)
        layout.addWidget(self.algorithmNum)
        layout.addWidget(QLabel("Chunk Size:"), 0, Qt.AlignRight)
        layout.addWidget(self.chunkSize, 0, Qt.AlignLeft)
        layout.addWidget(self.DirectorySelect, 0, Qt.AlignRight)
        layout.addWidget(QLabel("File Choice:"), 0, Qt.AlignRight)
        layout.addWidget(self.ChosenFile, 0, Qt.AlignLeft)
        layout.addWidget(self.ColorButton, 0, Qt.AlignLeft)
        layout.addStretch()

        layoutWidget.setLayout(layout)

        self.leftWidget.setWidget(layoutWidget)
        self.leftWidget.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)

    # Set up toolbar
    def createToolBar(self):
        tool_bar = QToolBar("Main Toolbar")
        tool_bar.setStyleSheet("QToolBar{spacing:7px;}")
        # tool_bar.setIconSize(QSize(20, 20))
        tool_bar.setIconSize(tool_bar.iconSize())

        self.addToolBar(tool_bar)

        tool_bar.addAction(self.file_open_act)
        tool_bar.addAction(self.render_act)
        tool_bar.addAction(self.play_act)
        tool_bar.addAction(self.stop_act)
        tool_bar.addSeparator()
        tool_bar.addAction(self.selectaudiodevice_act)
        tool_bar.addAction(self.record_act)
        tool_bar.addAction(self.stoprecord_act)
        tool_bar.addAction(self.saverecording_act)

        tool_bar.addSeparator()
        tool_bar.addAction(self.copyImage_act)
        tool_bar.addAction(self.saveImage_act)
        tool_bar.addAction(self.printImage_act)
        tool_bar.addAction(self.printPreviewImage_act)
        tool_bar.addSeparator()
        tool_bar.addAction(self.help_website_act)
        tool_bar.addAction(self.help_about_act)
        tool_bar.addSeparator()

    # Display information about program dialog box.
    def aboutDialog(self):
        QMessageBox.about(self, self.program_title + "  Version " + self.version,
                          self.authors + "\nVersion " + self.version +
                          "\nCopyright " + self.copyright +
                          "\nDeveloped in Python using the \nPySide, SciPy, and PyAudio toolsets.")

    # def setStatusText(self, text):
    #     self.statusBar.showMessage(text)

    # Theme setter, not currently being used in the program.
    def SelectTheme(self):
        items = QStyleFactory.keys()
        if len(items) <= 1:
            return

        items.sort()
        item, ok = QInputDialog.getItem(self, "Select Theme", "Available Themes", items, 0, False)

        if ok:
            self.Parent.setStyle(item)

    # Uses NumPy fft to compute frequency spectrum.
    def getSpectrum(self, data, samplingfreq):
        spectrum = np.abs(np.fft.rfft(data))
        freq = np.fft.rfftfreq(data.size, d=1.0 / samplingfreq)
        return spectrum, freq

    # Returns the dominate frequency from a spectrum and frequency list.
    def getMaxFreq(self, spec, freq):
        if len(spec) == 0 or len(freq) == 0:
            return 0

        maxfreq = freq[0]
        maxspec = spec[0]
        for j in range(len(spec)):
            if spec[j] > maxspec:
                maxspec = spec[j]
                maxfreq = freq[j]

        return maxfreq

    # Executed in a separate thread.  Reads in the wav file, precomputes the frequencies
    # for the entire file, depending on the mode will either render the data all at once
    # with the current algorithm and chunk size or it will render while the file is being
    # played.
    def dotheplay(self, playmusic):
        chunk = self.ChunkSizesList[self.chunkSize.currentIndex()]
        self.paintbrush.currentAlgorithm = self.algorithmNum.currentIndex() + 1

        samplingfreq, sound = wavfile.read(self.loadedFilename)

        if (len(sound.shape) > 1):
            channels = sound.shape[1]
            samples = sound.shape[0]
        else:
            channels = 1
            samples = sound.shape[0]

        channelData = []

        if (len(sound.shape) > 1):
            for i in range(channels):
                channelData.append(sound[:, i])
        else:
            channelData.append(sound)

        channelChunks = []
        for i in range(channels):
            soundslices = []
            start = 0
            while start + chunk <= samples:
                soundslices.append(channelData[i][start:start + chunk])
                start += chunk
            channelChunks.append(soundslices)

        af = wave.open(self.loadedFilename, 'rb')
        samplingfreq = af.getframerate()
        samples = af.getnframes()
        self.musictime = samples / samplingfreq
        pa = pyaudio.PyAudio()
        output_device_info = pa.get_device_info_by_index(self.OutputAudioDevices.currentIndex())
        if (output_device_info['maxOutputChannels'] == af.getnchannels()):
            stream = pa.open(format=pa.get_format_from_width(af.getsampwidth()),
                             channels=af.getnchannels(),
                             rate=af.getframerate(),
                             output=True,
                             output_device_index=self.OutputAudioDevices.currentIndex())
        else:
            stream = pa.open(format=pa.get_format_from_width(af.getsampwidth()),
                             channels=af.getnchannels(),
                             rate=af.getframerate(),
                             output=True)

        self.freqlist = []
        self.SpectList = []
        freqcap = 8500

        # precompute the frequency data.

        for i in range(len(channelChunks[0])):
            channelFreqs = []
            CorSpect = 0
            for k in range(channels):
                spect, freq = self.getSpectrum(channelChunks[k][i], samplingfreq)
                maxfreq = self.getMaxFreq(spect, freq)
                channelFreqs.append(maxfreq)

            maxfreqch = max(channelFreqs)

            for i in range(len(channelFreqs)):
                if channelFreqs[i] == maxfreqch:
                    CorSpect = spect[i]

            if maxfreqch > freqcap:
                channelFreqs = [0, 0]
            self.freqlist.append(channelFreqs)
            self.SpectList.append(CorSpect)
            # self.setStatusText("Processing segment "+ str(i+1) + " of " + str(len(channelChunks[0])))

        # rd_data = []
        # rd_temp = []
        # if playmusic:
        #     af.rewind()
        #     rd_temp = af.readframes(chunk)
        #     data_np = np.frombuffer(rd_temp, dtype=np.int16)  # Convert the binary data to a NumPy array
        #     amplified_data_np = (data_np * self.volumeMultiplier).astype(np.int16)  # Amplify the audio data
        #     rd_data = amplified_data_np.tobytes()  # Convert the amplified NumPy array back to binary data

        self.paintbrush.resetlistlinks()

        # intervalTime = self.musictime * 100
        # print(intervalTime)
        # self.timer1.setInterval(intervalTime)
        # self.timer1.start()
        # print(self.timer1.remainingTime())

        i = 0
        while i < len(self.freqlist) and (not self.playsoundstop):
            if (i == len(self.freqlist) - 1 or i == math.floor(len(self.freqlist) / 9) or i == math.floor(len(self.freqlist) / 8)
            or i == math.floor(len(self.freqlist) / 7) or i == math.floor(len(self.freqlist) / 6) or i == math.floor(len(self.freqlist) / 5)
            or i == math.floor(len(self.freqlist) / 4) or i == math.floor(len(self.freqlist) / 3) or i == math.floor(len(self.freqlist) / 2)):
                    self.algorithmFlag = False
            else:
                self.algorithmFlag = True
            if i < len(self.freqlist):
                self.paintbrush.draw(self.freqlist[i], i, self.SpectList[i], self.algorithmFlag)
                self.canvas.renderAll = False
                self.canvas.update()
                self.canvas.renderAll = True

            if playmusic:
                # stream.write(rd_data)
                # rd_data = af.readframes(chunk)
                rd_raw = af.readframes(chunk)  # Read frames from the wave file
                data_np = np.frombuffer(rd_raw, dtype=np.int16)  # Convert the binary data to a NumPy array
                amplified_data_np = (data_np * self.volumeMultiplier).astype(np.int16)  # Amplify the audio data
                rd_data = amplified_data_np.tobytes()  # Convert the amplified NumPy array back to binary data
                stream.write(rd_data)  # Write the amplified audio data to the stream
            #     self.setStatusText("")
            # else:
            #     self.setStatusText("")
            # eltime = "%.3f" %  (i * chunk / wavframerate)
            # self.setStatusText(eltime + " sec.")
            i += 1
            # if (not self.timer1Flag):
            #     self.timer1Flag = True

        stream.stop_stream()
        stream.close()
        af.close()
        pa.terminate()
        # self.setStatusText("")
        # Remove Thread
        self.music_thread = None
        self.canvas.update()

        # self.play_act.setEnabled(True)

    # Checks id the file is readable with both scipy and pyaudio
    def checkFile(self):
        if self.loadedFilename == '':
            QMessageBox.warning(self, "File Not Opened", "A Wav file needs to opened before rendering.",
                                QMessageBox.Ok)
            return False

        try:
            samplingfreq, sound = wavfile.read(self.loadedFilename)
            af = wave.open(self.loadedFilename, 'rb')
            af.close
        except:
            QMessageBox.warning(self, "File Could Not be Loaded",
                                "The file " + self.loadedFilename + " could not be loaded.",
                                QMessageBox.Ok)
            return False

        return True

    # Sets the rendering thread to render the entire wav file immediately.
    def renderImage(self):
        if not self.checkFile():
            return

        if not self.music_thread:
            self.music_thread = Thread(target=self.dotheplay, args=(False,), daemon=True)
            # self.clearImage()

        if self.music_thread.is_alive():
            return

        self.playsoundstop = False
        self.music_thread.start()

    # Sets the rendering and playing thread to play while rendering.
    def PlaySoundData(self):
        if not self.checkFile():
            return

        if not self.music_thread:
            self.music_thread = Thread(target=self.dotheplay, args=(True,), daemon=True)
            # self.clearImage()

        if self.music_thread.is_alive():
            return

        self.playsoundstop = False
        self.music_thread.start()

    # Stops the playing and rendering of the wav file.
    def StopSoundData(self):
        self.playsoundstop = True
        self.music_thread = None
        self.titleoverridetext = ""
        self.updateProgramWindowTitle()
        self.StopAnimateRecordButton()

    # Executed in a separate thread. This will use the current chunk size and algorithm
    # to stream data from the microphone through the numpy fft to the rendering algorithms.
    # At the end it will join the frames into a single data file that can be saved to a
    # wav file.
    def dotherecord(self):
        chunk = self.ChunkSizesList[self.chunkSize.currentIndex()]
        self.paintbrush.currentAlgorithm = self.algorithmNum.currentIndex() + 1

        p = pyaudio.PyAudio()
        stream = p.open(format=self.RECORDFORMAT,
                        channels=self.RECORDCHANNELS,
                        rate=self.RECORDRATE,
                        input=True,
                        frames_per_buffer=chunk,
                        input_device_index=self.InputAudioDevices.currentIndex())

        frames = []
        self.freqlist = []
        freqcap = 8500
        self.paintbrush.resetlistlinks()

        while not self.playsoundstop:
            data = stream.read(chunk)
            numpydata = np.frombuffer(data, dtype=np.int16)
            # frame = np.stack((numpydata[::2], numpydata[1::2]), axis=0)
            # frame = []
            # for i in range(self.RECORDCHANNELS):
            #     frame.append(numpydata[i::2])

            channelFreqs = []
            CorSpect = 0
            for i in range(self.RECORDCHANNELS):
                # channelData.append(numpydata[:, i])
                # spect, freq = self.getSpectrum(frame[i], self.RECORDRATE)
                spect, freq = self.getSpectrum(numpydata[i::self.RECORDCHANNELS], self.RECORDRATE)
                maxfreq = self.getMaxFreq(spect, freq)
                channelFreqs.append(maxfreq)

            maxfreqch = max(channelFreqs)

            for i in range(len(channelFreqs)):
                if channelFreqs[i] == maxfreqch:
                    CorSpect = spect[i]

            if maxfreqch > freqcap:
                channelFreqs = [0, 0]
            self.freqlist.append(channelFreqs)

            if channelFreqs != [0, 0]:
                pos = len(self.freqlist) - 1
                if (pos % 10 == 0):
                    self.algorithmFlag = False
                else:
                    self.algorithmFlag = True
                self.paintbrush.draw(self.freqlist[pos], pos, CorSpect, self.algorithmFlag)
                self.canvas.renderAll = False
                self.canvas.update()
                self.canvas.renderAll = True
                # print(self.freqlist[pos])

            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        self.fullrecording = b''.join(frames)
        self.music_thread = None

    def changeVolume(self):
        volumeValue = self.volumeSlider.value()
        self.volumeLabel.setText(f'Volume: {volumeValue}%')

        self.volumeMultiplier = volumeValue / 100.0

    def AnimateRecordButton(self):
        if self.flag:
            self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record-Stop.png')))
            # self.record_act.setIcon(QIcon(self.resource_path('Record-Stop.png')))
        else:
            self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record.png')))
            # self.record_act.setIcon(QIcon(self.resource_path('Record.png')))

        self.flag = not self.flag

    def StopAnimateRecordButton(self):
        self.timer.stop()
        self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record.png')))
        # self.record_act.setIcon(QIcon(self.resource_path('Record.png')))

    def setFlag(self):
        self.timer1Flag = False

    # Sets up the thread to record the sound data from the microphone.
    def RecordSoundData(self):
        if not self.music_thread:
            self.music_thread = Thread(target=self.dotherecord, daemon=True)

        if self.music_thread.is_alive():
            self.StopRecordData()
            return

        self.timer.start()
        self.playsoundstop = False
        self.titleoverridetext = "Recording"
        self.updateProgramWindowTitle()
        self.music_thread.start()
        # self.titleoverridetext = ""
        # self.updateProgramWindowTitle()

    # Stops the recording.
    def StopRecordData(self):
        self.playsoundstop = True
        self.music_thread = None
        self.titleoverridetext = ""
        self.updateProgramWindowTitle()
        self.StopAnimateRecordButton()

    # Saves the current recorded data to a wav file.
    def SaveRecording(self):
        if self.fullrecording is None:
            return

        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QDir.Hidden)
        dialog.setDefaultSuffix('wav')
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(['Wav Files (*.wav)'])
        dialog.setWindowTitle('Save As')

        if dialog.exec() == QDialog.Accepted:
            filelist = dialog.selectedFiles()
            if len(filelist) > 0:
                file_name = filelist[0]
                wf = wave.open(file_name, "wb")
                wf.setnchannels(self.RECORDCHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.RECORDFORMAT))
                wf.setframerate(self.RECORDRATE)
                wf.writeframes(self.fullrecording)
                wf.close()

    # Reports the properties of the currently loaded wav file.
    def SoundDataProperties(self):
        try:
            af = wave.open(self.loadedFilename, 'rb')
            samplingfreq = af.getframerate()
            channels = af.getnchannels()
            samples = af.getnframes()
            musictime = samples / samplingfreq
            af.close()

            timesec = "%.3f" % musictime
            timemin = musictime // 60
            timeminsec = "%.3f" % (musictime - timemin * 60)

            reportstring = "Sampling Frequency: " + str(samplingfreq) + "\n"
            reportstring += "Number of Samples: " + str(samples) + "\n"
            reportstring += "Length: " + timesec + " sec. = " + str(int(timemin)) + " min. " + timeminsec + " sec.\n"
            reportstring += "Number of Channels: " + str(channels) + "\n"
            QMessageBox.information(self, "File Information", reportstring, QMessageBox.Ok)
        except:
            pass

    # Clears the render list and screen.
    def clearImage(self):
        self.rl.clear()
        self.canvas.update()

    # Opens a wav file for rendering and playing.  The file data ia not stored internally
    # since it must be streamed from the file in other functions.  The filename is all that
    # is stored.
    def openFile(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Wav File",
                                                   "", "Wav Files (*.wav);;All Files (*.*)")

        if file_name:
            try:
                # Check opening
                samplingfreq, sound = wavfile.read(file_name)
                af = wave.open(file_name, 'rb')
                af.close()

                self.loadedFilename = file_name
                self.updateProgramWindowTitle()
            except:
                QMessageBox.warning(self, "File Not Loaded", "The file " + file_name + " could not be loaded.",
                                    QMessageBox.Ok)

    # Copies the current image to the system clipboard.
    def copyImageToClipboard(self):
        pixmap = QPixmap(self.canvas.size())
        self.canvas.render(pixmap)
        self.clipboard.setPixmap(pixmap)

    # https://www.geeksforgeeks.org/how-to-iterate-over-files-in-directory-using-python/
    # Author: chetankhanna767
    # Last Updated: 05/17/2021
    def openDirectory(self):
        NoFilesLoaded = True
        mp3FileDetected = False
        self.loadedFiles = []
        _OutputFolder = QFileDialog.getExistingDirectory(self, "Select Output Folder", QDir.currentPath())
        if (_OutputFolder != ''):
            for filename in os.listdir(_OutputFolder):
                f = os.path.join(_OutputFolder, filename)
                TestString = f + "."
                TestString = TestString[-5:-1]
                if (os.path.isfile(f) and TestString == ".wav"):
                    self.loadedFiles.append(f)
                    NoFilesLoaded = False
                elif (os.path.isfile(f) and TestString == ".mp3"):
                    mp3FileDetected = True
            self.ChosenFile.clear()
            for i in range(len(self.loadedFiles)):
                self.ChosenFile.addItem(self.loadedFiles[i])
        if (mp3FileDetected):
            QMessageBox.information(self, ".mp3 Files not Compatible",
                                    "Convert your file to a .wav for use with this program.", QMessageBox.Ok)
        elif (NoFilesLoaded):
            QMessageBox.warning(self, "No Files Loaded",
                                "Open a Directory that contains .wav files to load them in the program.",
                                QMessageBox.Ok)

    # Saves the current image to an image file.  Defaults to a png file but the file type
    # is determined by the extension on the filename the user selects.
    def saveAsImage(self):
        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QDir.Hidden)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(['PNG Files (*.png)', 'JPEG Files (*.jpg)', 'Bitmap Files (*.bmp)'])
        dialog.setWindowTitle('Save Image As')

        if dialog.exec() == QDialog.Accepted:
            ext = "png"
            list = dialog.selectedNameFilter().split(" ")
            ext = list[len(list) - 1][3:-1]
            dialog.setDefaultSuffix(ext)

            filelist = dialog.selectedFiles()
            if len(filelist) > 0:
                file_name = filelist[0]
                try:
                    pixmap = QPixmap(self.canvas.size())
                    self.canvas.render(pixmap)
                    pixmap.save(file_name)
                except:
                    QMessageBox.warning(self, "File Not Saved", "The file " + file_name + " could not be saved.",
                                        QMessageBox.Ok)

    # Prints the current image to the printer using the selected printer options from the
    # options list.  This function does some initial setup, calls the print dialog box for
    # user input, and then calls printPreview which invokes the printing.
    def printImage(self):
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        printer.setDocName("MusicImage")

        leftoffset = 36
        topoffset = 36

        printer.setResolution(300)
        pl = QPageLayout(QPageSize(QPageSize.Letter), QPageLayout.Landscape,
                         QMarginsF(leftoffset, topoffset, 36, 36))
        printer.setPageLayout(pl)
        if dialog.exec() == QDialog.Accepted:
            self.printPreview(printer)

    # Invokes a print preview of the current image using the selected printer options from the
    # options list.  This function does some initial setup, calls the print preview dialog box,
    # and then calls printPreview which invokes the printing.
    def printPreviewImage(self):
        printer = QPrinter()
        dialog = QPrintPreviewDialog(printer)
        printer.setDocName("MusicImage")

        leftoffset = 36
        topoffset = 36

        printer.setResolution(300)
        pl = QPageLayout(QPageSize(QPageSize.Letter), QPageLayout.Portrait,
                         QMarginsF(leftoffset, topoffset, 36, 36))
        printer.setPageLayout(pl)

        dialog.paintRequested.connect(self.printPreview)
        dialog.exec()

    # This function does the printing by invoking an off-screen version of the image viewer and
    # rendering it to a pixmap.  This pixmap is then drawn as an image to the painter object
    # attached to the printer.
    def printPreview(self, printer):
        printviewer = ObjectListViewer(self, self.mainapp)
        printres = printer.resolution()

        wid = 7 * printres
        hei = wid * self.canvas.height() / self.canvas.width()
        printviewer.setFixedSize(QSize(round(wid), round(hei)))
        printviewer.zoomfactor = self.canvas.zoomfactor
        printviewer.center = self.canvas.center
        pixmap = QPixmap(printviewer.size())
        printviewer.render(pixmap)
        painter = QPainter(printer)
        painter.drawPixmap(QPoint(0, 0), pixmap)
        painter.end()

    # Ending dummy function for print completion.
    def print_completed(self, success):
        pass  # Nothing needs to be done.


if __name__ == '__main__':
    """
    Initiate the program. 
    """
    app = QApplication(sys.argv)
    window = MusicPainter(app)
    progcss = appcss()
    app.setStyleSheet(progcss.getCSS())
    sys.exit(app.exec_())