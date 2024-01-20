#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created: 10/1/2022
Revised: 12/30/2023

@authors: Luke Zolenski, Don Spickler & Kyle Tranfaglia

This program is a music/sound visualizer for frequency data from either a wav file or
an input stream from a microphone. It allows the user to set chunk size and rendering algorithm
and render images based on the wav or stream data. It also has features to render as the
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
import pyaudio
import webbrowser
from PySide2.QtCore import (Qt, QSize, QDir, QPoint, QMarginsF, QRect, QLine, QTimer)
from PySide2.QtGui import (QIcon, QPainter, QColor, QPageSize, QPageLayout, QPixmap)
from PySide2.QtWidgets import (QApplication, QMainWindow, QPushButton, QToolBar, QDockWidget, QHBoxLayout,
                               QVBoxLayout, QWidget, QLabel, QMessageBox, QInputDialog, QFileDialog, QDialog,
                               QAction, QColorDialog, QDialogButtonBox, QComboBox, QStyleFactory, QSlider)
from PySide2.QtPrintSupport import (QPrintDialog, QPrinter, QPrintPreviewDialog)

# Program imports of our modules
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
    This is the control for the rendered image. It takes the geometric data stored in
    the render list produced in the rendering algorithms and plots it. The default
    window is [-1,1] with aspect ratio expansion in one direction. The control
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

    # Opens a color dialog for background color selection and handles selection and rejections
    def SetBackgroundColor(self):
        self.colorDialog = QColorDialog(self)
        self.colorDialog.setOption(QColorDialog.DontUseNativeDialog)  # Use the Qt dialog instead of native
        self.colorDialog.rejected.connect(self.colorRejected)  # Connect the rejected signal to handler function
        # User clicked OK, set the selected color to background color and update canvas
        if (self.colorDialog.exec_() == QColorDialog.Accepted):
            self.backgroundcolor = self.colorDialog.currentColor()
            self.update()

    # Handles cancel or close of the color dialog such that no update is made to the canvas
    def colorRejected(self):
        self.colorDialog.close()

    # Reset Canvas center to default
    def resetCenter(self):
        self.center = [0, 0]
        self.repaint()

    # Reset Canvas zoom to default
    def resetZoom(self):
        self.zoomfactor = 1
        self.repaint()

    # Reset Canvas zoom and center to default
    def resetCenterAndZoom(self):
        self.center = [0, 0]
        self.zoomfactor = 1
        self.repaint()

    # On a mouse down event on the left button, track its state
    def mousePressEvent(self, e):
        self.mousePosition = QPoint(e.x(), e.y())
        if e.button() == Qt.LeftButton:
            self.mouseDown = True

    # On a mouse wheel event update the zoom factor
    def wheelEvent(self, e) -> None:
        self.zoomfactor *= (1 + e.delta() / 5000)
        if self.zoomfactor < 1:
            self.zoomfactor = 1
        if self.zoomfactor > 1000:
            self.zoomfactor = 1000
        self.repaint()

    # On a mouse up event track its state
    def mouseReleaseEvent(self, e):
        self.mouseDown = False

    # On a mouse move event, update the zoom factor if the control key is down, otherwise translate
    def mouseMoveEvent(self, e):
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

    # Covert real coordinates to screen coordinates.
    def XYtoQPoint(self, x, y):
        xr = self.screen[1] - self.screen[0]
        yr = self.screen[3] - self.screen[2]
        # ptx = x / xr * self.width() + self.width() / 2
        # pty = -y / yr * self.height() + self.height() / 2
        ptx = (x + self.center[0]) / xr * self.width() + self.width() / 2
        pty = (self.center[1] - y) / yr * self.height() + self.height() / 2
        return QPoint(ptx, pty)

    # Update the screen bounds based on the center and zoom factor being used
    def updateScreenBounds(self):
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

    # Draw a point to the screen
    def RenderPoint(self, qp, obj):
        qp.setPen(obj[3])
        qp.drawPoint(self.XYtoQPoint(obj[1], obj[2]))

    # Draw a line to the screen
    def RenderLine(self, qp, obj):
        qp.setPen(obj[5])
        pt1 = self.XYtoQPoint(obj[1], obj[2])
        pt2 = self.XYtoQPoint(obj[3], obj[4])
        line = QLine(pt1, pt2)
        qp.drawLine(line)

    # Draw a circle to the screen
    def RenderCircle(self, qp, obj):
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

    # Draw a rectangle to the screen
    def RendeRectangle(self, qp, obj):
        qp.setPen(obj[6])
        ulpt = self.XYtoQPoint(obj[1], obj[2])
        lrpt = self.XYtoQPoint(obj[3], obj[4])
        # rect = QRect(ulpt.x(), ulpt.y(), lrpt.x() - ulpt.x(), lrpt.y() - ulpt.y())
        rect = QRect(ulpt, lrpt)
        if obj[5]:
            qp.fillRect(rect, obj[6])
        else:
            qp.drawRect(rect)

    # Dra a triangle to the screen
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

    # Fill a triangle with a Riemann filling algorithm
    def RiemannFill(self, qp, obj):
        RESOLUTION = 250
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
        width = Range / RESOLUTION
        for i in range(RESOLUTION):
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

    # Paint event override: clears the screen, loops through the render list of objects & draws a border around the image
    def paintEvent(self, event):
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
        self.authors = "Luke Zolenski, Don Spickler & Kyle Tranfaglia"
        self.version = "1.2.1"
        self.program_title = "Music Painter"
        self.copyright = "2023"

        # Set GUI style
        self.Platform = platform.system()
        styles = QStyleFactory.keys()
        if "Fusion" in styles:
            app.setStyle('Fusion')

        # Set recording constants
        self.RECORDFORMAT = pyaudio.paInt16
        self.RECORDCHANNELS = 1
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

        # Set flags and timer
        self.flag = True
        self.timer = QTimer(self, interval=1000)
        self.timer.timeout.connect(self.AnimateRecordButton)
        self.algorithmFlag = True

    # https://gist.github.com/peace098beat/db8ef7161508e6500ebe
    # Author: Terraskull
    # Last Updated: 11/27/2020
    # Drag file or directory event
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    # https://gist.github.com/peace098beat/db8ef7161508e6500ebe
    # Author: Terraskull
    # Last Updated: 11/27/2020
    # Drop file or directory to screen event
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

    # Adjoin a relative path for icons and help system
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    # Updates the title bar to contain the loaded file path or test
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

    # Opens a dialog box to display sound settings: Prompts adjustment of sound volume and select input & output devices
    def chooseAudioDevice(self):
        # Dialog box creation
        self.dlg = QDialog(self)
        self.dlg.setFixedSize(450,300)
        self.dlg.setWindowTitle("Choose an Audio Input Device")
        # Create buttons
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("Apply",QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel",QDialogButtonBox.RejectRole)
        # Create and store temporary variables in event of reject
        self.tempIndex = self.InputAudioDevices.currentIndex()
        self.tempIndex1 = self.OutputAudioDevices.currentIndex()
        self.tempIndex2 = self.volumeMultiplier
        # Set behavior for reject and accept and remove default help button
        self.buttonBox.accepted.connect(self.audioAccept)
        self.buttonBox.rejected.connect(self.audioReject)
        self.dlg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        # Create formatting
        self.format = QVBoxLayout()
        self.format.addStretch()
        # Create Labels
        label1 = QLabel("Input Audio Devices: ")
        label1.setStyleSheet("font-size: 9pt;")
        label2 = QLabel("No Audio Input Devices Detected")
        label2.setStyleSheet("font-size: 9pt; font-weight: bold")
        label3 = QLabel("Output Audio Devices: ")
        label3.setStyleSheet("font-size: 9pt;")
        label4 = QLabel("No Audio Output Devices Detected")
        label4.setStyleSheet("font-size: 9pt; font-weight: bold")
        # Check if any input or output devices are found and adjust formatting with list of devices
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
        # Set up volume slider
        self.volumeLabel = QLabel(f'Volume: {int(self.volumeMultiplier * 100)}%', self)
        self.volumeSlider = QSlider(Qt.Horizontal, self)
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(self.volumeMultiplier * 100)
        self.volumeSlider.valueChanged.connect(self.changeVolume)
        # Add volume slider
        self.format.addSpacing(25)
        self.format.addWidget(self.volumeLabel)
        self.format.addWidget(self.volumeSlider)
        # Add buttons
        self.format.addStretch()
        self.format.addSpacing(10)
        self.format.addWidget(self.buttonBox)

        self.dlg.setLayout(self.format)
        self.dlg.exec()

    # Handles accept role for audio device dialog box
    def audioAccept(self):
        self.dlg.close()

    # Handles reject role for audio device dialog box
    def audioReject(self):
        self.InputAudioDevices.setCurrentIndex(self.tempIndex)
        self.OutputAudioDevices.setCurrentIndex(self.tempIndex1)
        self.volumeMultiplier = self.tempIndex2
        self.dlg.close()

    # Initialize the window, calls create methods to set up the GUI.
    def initializeUI(self):
        # Initialize main window
        self.canvas = ObjectListViewer(self, self)
        self.setMinimumSize(950, 700)
        self.updateProgramWindowTitle()
        icon = QIcon(self.resource_path("icons/Logo-Blackv2.png"))
        self.setWindowIcon(icon)
        # Set up clear button
        self.clearButton = QPushButton()
        self.clearButton.setStyleSheet('Background-color: #d1e7f0')
        self.clearButton.setText('Clear Image')
        self.clearButton.clicked.connect(self.clearImage)
        # Set up background color button
        self.ColorButton = QPushButton()
        self.ColorButton.setStyleSheet('Background-color: #fac8c9')
        self.ColorButton.setText('Background Color')
        self.ColorButton.clicked.connect(self.canvas.SetBackgroundColor)
        # Set up directory selector
        self.DirectorySelect = QPushButton()
        self.DirectorySelect.setStyleSheet('Background-color: #f5f0d0')
        self.DirectorySelect.setText('Open Directory')
        self.DirectorySelect.clicked.connect(self.openDirectory)
        # Create loaded file dropdown list
        self.ChosenFile = QComboBox()
        for i in range(len(self.loadedFiles)):
            self.ChosenFile.addItem(self.loadedFiles[i])

        self.ChosenFile.currentIndexChanged.connect(self.SetFile)
        # Create algorithm dropdown list
        self.algorithmNum = QComboBox()

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
        # Set up chunk size list
        self.ChunkSizesList = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
        self.chunkSize = QComboBox()
        for val in self.ChunkSizesList:
            self.chunkSize.addItem(str(val))
        self.chunkSize.setCurrentIndex(4)
        # Get host audio device information: device count
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        # Create and initialize input audio devices list
        self.InputAudioDevices = QComboBox()
        self.InputAudioDevices.setFixedSize(260, 30)
        self.inputDeviceCount = 0
        # Create and initialize output audio devices list
        self.OutputAudioDevices = QComboBox()
        self.OutputAudioDevices.setFixedSize(260, 30)
        self.outputDeviceCount = 0
        # Get all input and output devices and append them to a list (output list and input list)
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                self.InputAudioDevices.addItem(str(p.get_device_info_by_host_api_device_index(0, i).get('name')))
                self.inputDeviceCount += 1
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
                self.OutputAudioDevices.addItem(str(p.get_device_info_by_host_api_device_index(0, i).get('name')))
                self.outputDeviceCount += 1
        # Create menu and toolbars
        self.createMenu()
        self.createToolBar()
        self.createSecondaryToolBar()
        # Add the Dock area and canvas
        self.addDockWidget(Qt.TopDockWidgetArea, self.toolBarWidget)
        self.setCentralWidget(self.canvas)
        self.show()

    # Resets temporary variables for algorithm calculations upon each algorithm index change: Calls PaintBrush function
    def resetRLData(self):
        # Assesses current index and calls corresponding PaintBrush function to reset the data variable list
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

        current = self.chunkSize.currentIndex()  # Update current index variable
        # Check algorithm index and set chunk size list: If triangle algorithm, limit chunk size list
        if ((self.algorithmNum.currentIndex() == 5) or (self.algorithmNum.currentIndex() == 8)):
            # Check if chunk size list has changed by assessing the first list value
            if self.ChunkSizesList[0] == 1024:
                ListChanged = True
            else:
                ListChanged = False
            # Setup new chunk size list
            self.ChunkSizesList = [16384, 32768, 65536, 131072]
            self.chunkSize.clear()
            # Fill chunk size list with all possible chunk sizes for the algorithm
            for val in self.ChunkSizesList:
                self.chunkSize.addItem(str(val))
            # Adjust the current index to a chunk size in the new list range if not already
            if ListChanged:
                if current >= 5 and current <= 7:
                    self.chunkSize.setCurrentIndex(current - 4)
                else:
                    self.chunkSize.setCurrentIndex(0)
            else:
                self.chunkSize.setCurrentIndex(current)
        # Non-triangle algorithm case
        else:
            # Check if chunk size list has changed by assessing the first list value
            if self.ChunkSizesList[0] == 16384:
                ListChanged = True
            else:
                ListChanged = False
            # Setup new chunk size list
            self.ChunkSizesList = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
            self.chunkSize.clear()
            # Fill chunk size list with all possible chunk sizes for the algorithm
            for val in self.ChunkSizesList:
                self.chunkSize.addItem(str(val))
            # Adjust the current index to a chunk size in the new list range if not already
            if ListChanged:
                if current >= 1 and current <= 3:
                    self.chunkSize.setCurrentIndex(current + 4)
                else:
                    self.chunkSize.setCurrentIndex(4)
            else:
                self.chunkSize.setCurrentIndex(current)

    # Setup all menu and toolbar actions as well as create the menu
    def createMenu(self):
        # Setup all toolbar actions by setting an icon, possibly a shortcut, an action upon trigger, and a status tip
        self.file_open_act = QAction(QIcon(self.resource_path('icons/48x48/OpenFile.png')), "&Open Wav File...", self)
        self.file_open_act.setShortcut('Ctrl+O')
        self.file_open_act.triggered.connect(self.openFile)
        self.file_open_act.setStatusTip("Open a wav file for rendering.")

        self.printImage_act = QAction(QIcon(self.resource_path('icons/48x48/Printer.png')), "&Print...", self)
        self.printImage_act.setShortcut('Ctrl+P')
        self.printImage_act.triggered.connect(self.printImage)
        self.printImage_act.setStatusTip("Print the image.")

        self.printPreviewImage_act = QAction(QIcon(self.resource_path('icons/48x48/Printer-View.png')),
                                             "Print Pre&view...", self)
        self.printPreviewImage_act.triggered.connect(self.printPreviewImage)
        self.printPreviewImage_act.setStatusTip("Print preview the image.")

        quit_act = QAction("E&xit", self)
        quit_act.triggered.connect(self.close)
        quit_act.setStatusTip("Shut down the application.")

        self.copyImage_act = QAction(QIcon(self.resource_path('icons/48x48/Copy.png')), "Copy &Image", self)
        self.copyImage_act.setShortcut('Ctrl+C')
        self.copyImage_act.triggered.connect(self.copyImageToClipboard)
        self.copyImage_act.setStatusTip("Copy the image to the clipboard.")

        self.saveImage_act = QAction(QIcon(self.resource_path('icons/48x48/Download-Blue.png')), "Save Image &As...",
                                     self)
        self.saveImage_act.triggered.connect(self.saveAsImage)
        self.saveImage_act.setStatusTip("Save the image.")

        self.render_act = QAction(QIcon(self.resource_path('icons/48x48/Brush-Purple.png')), "&Render", self)
        self.render_act.triggered.connect(self.renderImage)
        self.render_act.setStatusTip("Render the image.")

        self.clear_act = QAction("&Clear Image", self)
        self.clear_act.triggered.connect(self.clearImage)
        self.clear_act.setStatusTip("Clear the image.")

        self.setColor = QAction("Background Color", self)
        self.setColor.triggered.connect(self.canvas.SetBackgroundColor)
        self.setColor.setStatusTip("Choose background color for image.")

        self.dir_open_act = QAction("Open Directory", self)
        self.dir_open_act.triggered.connect(self.openDirectory)
        self.dir_open_act.setStatusTip("Open directory containing .wav files.")

        self.resetCenter_act = QAction(QIcon(self.resource_path('icons/48x48/Center.png')), "Reset Center", self)
        self.resetCenter_act.triggered.connect(self.canvas.resetCenter)
        self.resetCenter_act.setStatusTip("Reset the center to the origin.")

        self.resetZoom_act = QAction(QIcon(self.resource_path('icons/48x48/Zoom.png')), "Reset Zoom", self)
        self.resetZoom_act.triggered.connect(self.canvas.resetZoom)
        self.resetZoom_act.setStatusTip("Reset the zoom factor to 1.")

        self.resetCenterZoom_act = QAction(QIcon(self.resource_path('icons/48x48/ZoomCenter.png')),
                                           "Reset Center and Zoom", self)
        self.resetCenterZoom_act.triggered.connect(self.canvas.resetCenterAndZoom)
        self.resetCenterZoom_act.setStatusTip("Reset the center to the origin and zoom factor to 1.")

        self.properties_act = QAction(QIcon(self.resource_path('icons/48x48/InfoCard.png')), "File &Information...",
                                      self)
        self.properties_act.triggered.connect(self.SoundDataProperties)
        self.properties_act.setStatusTip("View the wav file information.")

        self.play_act = QAction(QIcon(self.resource_path('icons/48x48/Play.png')), "Render and &Play", self)
        self.play_act.triggered.connect(self.PlaySoundData)
        self.play_act.setStatusTip("Render the image while playing the wav file.")

        self.stop_act = QAction(QIcon(self.resource_path('icons/48x48/Stop-Center.png')), "&Stop Render", self)
        self.stop_act.triggered.connect(self.StopSoundData)
        self.stop_act.setStatusTip("Stop the rendering of the image.")

        self.selectaudiodevice_act = QAction(QIcon(self.resource_path('icons/48x48/Microphone.png')),
                                             "&Choose Audio Device", self)
        self.selectaudiodevice_act.triggered.connect(self.chooseAudioDevice)
        self.selectaudiodevice_act.setStatusTip("Choose an audio input device for recording.")

        self.record_act = QAction(QIcon(self.resource_path('icons/48x48/Record.png')), "&Record", self)
        self.record_act.triggered.connect(self.RecordSoundData)
        self.record_act.setStatusTip("Record sound and render image.")

        self.saverecording_act = QAction(QIcon(self.resource_path('icons/48x48/Download.png')), "&Save Recording", self)
        self.saverecording_act.triggered.connect(self.SaveRecording)
        self.saverecording_act.setStatusTip("Save recorded sound to wav file.")

        self.stoprecord_act = QAction(QIcon(self.resource_path('icons/48x48/Pause.png')), "&Stop Recording", self)
        self.stoprecord_act.triggered.connect(self.StopRecordData)
        self.stoprecord_act.setStatusTip("Stop recording.")

        selectTheme_act = QAction("&Theme...", self)
        selectTheme_act.triggered.connect(self.SelectTheme)

        self.help_about_act = QAction(QIcon(self.resource_path('icons/48x48/Information.png')), "&About...", self)
        self.help_about_act.triggered.connect(self.aboutDialog)
        self.help_about_act.setStatusTip("Information about the program.")

        self.help_website_act = QAction(QIcon(self.resource_path('icons/48x48/Help.png')), "&Help", self)
        self.help_website_act.triggered.connect(self.openURL)
        self.help_website_act.setStatusTip("Help (Opens External Link)")

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

        # Create record menu and add actions
        record_menu = menu_bar.addMenu('&Record')
        record_menu.addAction(self.selectaudiodevice_act)
        record_menu.addAction(self.record_act)
        record_menu.addAction(self.stoprecord_act)
        record_menu.addAction(self.saverecording_act)

        # Create image menu and add actions
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

        # Create help menu and add actions
        help_menu = menu_bar.addMenu('&Help')
        help_menu.addAction(self.help_about_act)
        help_menu.addAction(self.help_website_act)

    # Create and set up the secondary toolbar
    def createSecondaryToolBar(self):
        # Create and set up docking widget for toolbar
        self.toolBarWidget = QDockWidget()
        self.toolBarWidget.setWindowTitle(" ")
        self.toolBarWidget.setStyleSheet("QDockWidget::title""{" "background : lightblue;" "}")
        self.toolBarWidget.setFeatures(self.toolBarWidget.DockWidgetFloatable | self.toolBarWidget.DockWidgetMovable)
        # Create layout for toolbar
        layoutWidget = QWidget()
        layout = QHBoxLayout()
        # Set up the layout: Add all widgets and format
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

        layoutWidget.setLayout(layout)  # Set the layout
        # Instate the layout to the toolbar and set docking bounds
        self.toolBarWidget.setWidget(layoutWidget)
        self.toolBarWidget.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)

    # Create and set up primary toolbar
    def createToolBar(self):
        # Create and initialize toolbar
        tool_bar = QToolBar("Main Toolbar")
        tool_bar.setStyleSheet("QToolBar{spacing:7px;}")
        tool_bar.setIconSize(tool_bar.iconSize())
        self.addToolBar(tool_bar)
        # Add file and render actions
        tool_bar.addAction(self.file_open_act)
        tool_bar.addAction(self.render_act)
        tool_bar.addAction(self.play_act)
        tool_bar.addAction(self.stop_act)
        tool_bar.addSeparator()
        # Add audio and record actions
        tool_bar.addAction(self.selectaudiodevice_act)
        tool_bar.addAction(self.record_act)
        tool_bar.addAction(self.stoprecord_act)
        tool_bar.addAction(self.saverecording_act)
        tool_bar.addSeparator()
        # Add image actions
        tool_bar.addAction(self.copyImage_act)
        tool_bar.addAction(self.saveImage_act)
        tool_bar.addAction(self.printImage_act)
        tool_bar.addAction(self.printPreviewImage_act)
        tool_bar.addSeparator()
        # Add help and information actions
        tool_bar.addAction(self.help_website_act)
        tool_bar.addAction(self.help_about_act)
        tool_bar.addSeparator()

    # Display information about program as a dialog box
    def aboutDialog(self):
        # Set message box
        QMessageBox.about(self, self.program_title + "  Version " + self.version,
                          self.authors + "\nVersion " + self.version +
                          "\nCopyright " + self.copyright +
                          "\nDeveloped in Python using the \nPySide, SciPy, and PyAudio toolsets.")

    # Theme setter, not currently being used in the program.
    def SelectTheme(self):
        items = QStyleFactory.keys()  # Get themes
        # If one theme or less, return
        if len(items) <= 1:
            return
        # Sort themes and create an input dialogue to list the themes for selection
        items.sort()
        item, ok = QInputDialog.getItem(self, "Select Theme", "Available Themes", items, 0, False)
        # If a theme is selected, set theme
        if ok:
            self.Parent.setStyle(item)

    # Uses NumPy fft to compute frequency spectrum.
    def getSpectrum(self, data, samplingfreq):
        spectrum = np.abs(np.fft.rfft(data))
        freq = np.fft.rfftfreq(data.size, d=1.0 / samplingfreq)
        return spectrum, freq

    # Returns the dominate frequency from a spectrum and frequency list.
    def getMaxFreq(self, spec, freq):
        # Check if spec and freq data exists (non zero)
        if len(spec) == 0 or len(freq) == 0:
            return 0
        # Initialize max values
        maxfreq = freq[0]
        maxspec = spec[0]
        # Loop through spec list
        for j in range(len(spec)):
            # If spec at index is greater than max, set new max spec at index and max freq at corresponding index
            if spec[j] > maxspec:
                maxspec = spec[j]
                maxfreq = freq[j]

        return maxfreq

    # Executed in a separate thread.  Reads in the wav file, precomputes the frequencies
    # for the entire file, depending on the mode will either render the data all at once
    # with the current algorithm and chunk size, or it will render while the file is played
    def dotheplay(self, playmusic):
        # Set chunk and current algorithm
        chunk = self.ChunkSizesList[self.chunkSize.currentIndex()]
        self.paintbrush.currentAlgorithm = self.algorithmNum.currentIndex() + 1

        samplingfreq, sound = wavfile.read(self.loadedFilename)  # Read loaded file
        channelData = []
        # Get channel count, then set channels, initialize samples, and append sound to channel data list
        if (len(sound.shape) > 1):
            channels = sound.shape[1]
            samples = sound.shape[0]
            for i in range(channels):
                channelData.append(sound[:, i])
        else:
            channels = 1
            samples = sound.shape[0]
            channelData.append(sound)

        channelChunks = []
        # Use chunk size to slice the channel data while there is data to slice
        for i in range(channels):
            soundslices = []
            start = 0
            while start + chunk <= samples:
                soundslices.append(channelData[i][start:start + chunk])
                start += chunk
            channelChunks.append(soundslices)

        # Set up pyAudio stream: open file, set sampling frequency, set samples, calculate play time, prepare stream
        af = wave.open(self.loadedFilename, 'rb')
        samplingfreq = af.getframerate()
        samples = af.getnframes()
        self.musictime = samples / samplingfreq
        pa = pyaudio.PyAudio()
        # Get output device information for selected device: If input and output channels match (no conflicts), proceed
        output_device_info = pa.get_device_info_by_index(self.OutputAudioDevices.currentIndex())
        if (output_device_info['maxOutputChannels'] == af.getnchannels()):
            # Create audio stream using selected output device
            stream = pa.open(format=pa.get_format_from_width(af.getsampwidth()),
                             channels=af.getnchannels(),
                             rate=af.getframerate(),
                             output=True,
                             output_device_index=self.OutputAudioDevices.currentIndex())
        else:
            # Create audio stream without an output device
            stream = pa.open(format=pa.get_format_from_width(af.getsampwidth()),
                             channels=af.getnchannels(),
                             rate=af.getframerate(),
                             output=True)

        self.freqList = []
        self.SpectList = []
        freqcap = 8500

        # precompute the frequency data
        for i in range(len(channelChunks[0])):
            channelFreqs = []
            CorSpect = 0
            # Loop through each channel
            for k in range(channels):
                spect, freq = self.getSpectrum(channelChunks[k][i], samplingfreq)  # Get spectrum and frequency data
                maxfreq = self.getMaxFreq(spect, freq)  # Find the maximum frequency in the spectrum
                channelFreqs.append(maxfreq)  # Append the maximum frequency to the channelFreqs list

            maxfreqch = max(channelFreqs)  # Find the maximum frequency among all channels
            # Iterate through the frequency list to find the corresponding spectrum value at the overall max frequency
            for i in range(len(channelFreqs)):
                if channelFreqs[i] == maxfreqch:
                    CorSpect = spect[i]
            # If the maximum frequency exceeds the frequency cap, set list to [0, 0]
            if maxfreqch > freqcap:
                channelFreqs = [0, 0]
            # Append the channelFreqs list and CorSpect to freqList and SpectList respectively
            self.freqList.append(channelFreqs)
            self.SpectList.append(CorSpect)
            # self.setStatusText("Processing segment "+ str(i+1) + " of " + str(len(channelChunks[0])))

        self.paintbrush.resetlistlinks()

        # Loop through the frequency list and draw the corresponding data using the paintbrush
        i = 0
        while i < len(self.freqList) and (not self.playsoundstop):
            # Assess if data is at a tenth split position and set a flag
            if (i == len(self.freqList) - 1 or i == math.floor(len(self.freqList) / 9) or i == math.floor(len(self.freqList) / 8)
            or i == math.floor(len(self.freqList) / 7) or i == math.floor(len(self.freqList) / 6) or i == math.floor(len(self.freqList) / 5)
            or i == math.floor(len(self.freqList) / 4) or i == math.floor(len(self.freqList) / 3) or i == math.floor(len(self.freqList) / 2)):
                    self.algorithmFlag = False
            else:
                self.algorithmFlag = True
            # Draw with the data using paintbrush
            if i < len(self.freqList):
                self.paintbrush.draw(self.freqList[i], i, self.SpectList[i], self.algorithmFlag)
                self.canvas.renderAll = False
                self.canvas.update()
                self.canvas.renderAll = True
            # If audio is playing, read and amplify audio data from the wave file
            if playmusic:
                rd_raw = af.readframes(chunk)  # Read frames from the wave file
                data_np = np.frombuffer(rd_raw, dtype=np.int16)  # Convert the binary data to a NumPy array
                amplified_data_np = (data_np * self.volumeMultiplier).astype(np.int16)  # Amplify the audio data
                rd_data = amplified_data_np.tobytes()  # Convert the amplified NumPy array back to binary data
                stream.write(rd_data)  # Write the amplified audio data to the stream

            i += 1
        # Close audio stream
        stream.stop_stream()
        stream.close()
        af.close()
        pa.terminate()
        # Remove Thread
        self.music_thread = None
        self.canvas.update()

    # Checks if the file is readable with both scipy and pyaudio
    def checkFile(self):
        # Checks that a file is loaded in order to assess it
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

    # Sets the rendering thread to render the entire wav file immediately
    def renderImage(self):
        # Check if file is valid and loaded
        if not self.checkFile():
            return
        # Check if there is a music thread
        if not self.music_thread:
            self.music_thread = Thread(target=self.dotheplay, args=(False,), daemon=True)
        # Check if music thread is active
        if self.music_thread.is_alive():
            return
        # Start music thread
        self.playsoundstop = False
        self.music_thread.start()

    # Sets the rendering and playing thread to play while rendering
    def PlaySoundData(self):
        # Check if file is valid and loaded
        if not self.checkFile():
            return
        # Check if there is a music thread
        if not self.music_thread:
            self.music_thread = Thread(target=self.dotheplay, args=(True,), daemon=True)
        # Check if music thread is active
        if self.music_thread.is_alive():
            return
        # Start music thread
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
        # Set chunk and current algorithm
        chunk = self.ChunkSizesList[self.chunkSize.currentIndex()]
        self.paintbrush.currentAlgorithm = self.algorithmNum.currentIndex() + 1
        # Create and set up audio stream
        p = pyaudio.PyAudio()
        stream = p.open(format=self.RECORDFORMAT,
                        channels=self.RECORDCHANNELS,
                        rate=self.RECORDRATE,
                        input=True,
                        frames_per_buffer=chunk,
                        input_device_index=self.InputAudioDevices.currentIndex())
        # Declare variables
        frames = []
        self.freqlist = []
        freqcap = 8500
        self.paintbrush.resetlistlinks()
        # Loop as long as sound is not signaled to stop
        while not self.playsoundstop:
            data = stream.read(chunk)  # Read a chunk of audio data from the stream
            numpydata = np.frombuffer(data, dtype=np.int16)  # Convert binary data to a NumPy array of 16-bit integers
            channelFreqs = []
            CorSpect = 0
            # Loop through each recording channel
            for i in range(self.RECORDCHANNELS):
                # Get spectrum and frequency data for the current channel, find max freq in spec, then append max freq
                spect, freq = self.getSpectrum(numpydata[i::self.RECORDCHANNELS], self.RECORDRATE)
                maxfreq = self.getMaxFreq(spect, freq)
                channelFreqs.append(maxfreq)

            maxfreqch = max(channelFreqs)  # Find the maximum frequency among all channels
            # Iterate through the channelFreqs list to find the corresponding spectrum value
            for i in range(len(channelFreqs)):
                if channelFreqs[i] == maxfreqch:
                    CorSpect = spect[i]
            # If the maximum frequency exceeds the frequency cap, set channelFreqs to [0, 0]
            if maxfreqch > freqcap:
                channelFreqs = [0, 0]
            self.freqlist.append(channelFreqs)  # Append the channelFreqs list to freqlist
            # Check if channelFreqs list is not empty
            if channelFreqs != [0, 0]:
                pos = len(self.freqlist) - 1
                # Check if the position is a multiple of 10 to set the algorithmFlag accordingly
                if (pos % 10 == 0):
                    self.algorithmFlag = False
                else:
                    self.algorithmFlag = True
                # Draw with the data using paintbrush
                self.paintbrush.draw(self.freqlist[pos], pos, CorSpect, self.algorithmFlag)
                self.canvas.renderAll = False
                self.canvas.update()
                self.canvas.renderAll = True

            frames.append(data)
        # Close audio stream
        stream.stop_stream()
        stream.close()
        p.terminate()

        self.fullrecording = b''.join(frames)
        self.music_thread = None

    # Adjust output volume using a volume slider
    def changeVolume(self):
        volumeValue = self.volumeSlider.value()  # Get volume slider value
        self.volumeLabel.setText(f'Volume: {volumeValue}%')  # Update the displayed volume value
        self.volumeMultiplier = volumeValue / 100.0  # Translate the volume value to a volume multiplier (% to decimal)

    # Animate the record button by using flags to switch the record icons over an interval to simulate a blink
    def AnimateRecordButton(self):
        # Set an icon for the record button - uncolored icon for true and colored for false
        if self.flag:
            self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record-Stop.png')))
        else:
            self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record.png')))

        self.flag = not self.flag  # Invert the flag to create a boolean loop

    # Stop animating the record button: Stop timer and set record icon to colored
    def StopAnimateRecordButton(self):
        self.timer.stop()
        self.record_act.setIcon(QIcon(self.resource_path('icons/48x48/Record.png')))

    # Sets up the thread to record the sound data from the audio input device
    def RecordSoundData(self):
        # Checks if there a music thread and sets one
        if not self.music_thread:
            self.music_thread = Thread(target=self.dotherecord, daemon=True)
        # Checks if a music thread is an active music thread and stops recording if true
        if self.music_thread.is_alive():
            self.StopRecordData()
            return
        # Set up for recording thread
        self.timer.start()
        self.playsoundstop = False
        self.titleoverridetext = "Recording"
        self.updateProgramWindowTitle()
        self.music_thread.start()

    # Stops the recording
    def StopRecordData(self):
        self.playsoundstop = True
        self.music_thread = None
        self.titleoverridetext = ""
        self.updateProgramWindowTitle()
        self.StopAnimateRecordButton()

    # Saves the current recorded data to a wav file
    def SaveRecording(self):
        # Check that there is a recording to save
        if self.fullrecording is None:
            return
        # Create a file dialog for saving the recording
        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QDir.Hidden)
        dialog.setDefaultSuffix('wav')
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(['Wav Files (*.wav)'])
        dialog.setWindowTitle('Save As')
        # Check if the user accepted the file save dialog
        if dialog.exec() == QDialog.Accepted:
            filelist = dialog.selectedFiles()  # Get the list of selected files from the dialog
            # Check if there is at least one selected file
            if len(filelist) > 0:
                file_name = filelist[0]  # Get the first selected file as the file name
                wf = wave.open(file_name, "wb")  # Open a wave file for writing
                # Set the number of channels, sample width, frame rate, and write the frames
                wf.setnchannels(self.RECORDCHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.RECORDFORMAT))
                wf.setframerate(self.RECORDRATE)
                wf.writeframes(self.fullrecording)
                wf.close()  # Close the wave file

    # Reports the properties of the currently loaded wav file.
    def SoundDataProperties(self):
        # Calculates and sets the sound data properties, then concatenate to a string for display via message box
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

    # Clears the render list and screen
    def clearImage(self):
        self.rl.clear()
        self.canvas.update()

    # Opens a wav file for rendering and playing. The file data is not stored internally since it
    # must be streamed from the file in other functions. The filename is all that is stored
    def openFile(self):
        # Open a file dialog to get the path of a Wav file
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Wav File", "", "Wav Files (*.wav);;All Files (*.*)")
        # Check if a file was selected
        if file_name:
            try:
                # Attempt to read the Wav file
                samplingfreq, sound = wavfile.read(file_name)
                # Open the Wav file to check for errors
                af = wave.open(file_name, 'rb')
                af.close()
                # Set the loaded filename and update the program window title
                self.loadedFilename = file_name
                self.updateProgramWindowTitle()
            except:
                # Show a message box warning if there is an issue loading the file
                QMessageBox.warning(self, "File Not Loaded", "The file " + file_name + " could not be loaded.",
                                    QMessageBox.Ok)

    # Copies the current image to the system clipboard
    def copyImageToClipboard(self):
        # Create pixmap of canvas size, render canvas onto pixmap, then clipboard the pixmap
        pixmap = QPixmap(self.canvas.size())
        self.canvas.render(pixmap)
        self.clipboard.setPixmap(pixmap)

    # https://www.geeksforgeeks.org/how-to-iterate-over-files-in-directory-using-python/
    # Author: chetankhanna767
    # Last Updated: 05/17/2021
    def openDirectory(self):
        # Initialize variables to track loaded files and mp3 file detection
        NoFilesLoaded = True
        mp3FileDetected = False
        self.loadedFiles = []  # Clear the list of loaded files
        # Open a dialog to select the output folder and Check if the output folder is not empty
        _OutputFolder = QFileDialog.getExistingDirectory(self, "Select Output Folder", QDir.currentPath())
        if (_OutputFolder != ''):
            # Iterate through files in the selected folder
            for filename in os.listdir(_OutputFolder):
                # Create the full path to the file
                f = os.path.join(_OutputFolder, filename)
                # Extract the last four characters of the filename
                TestString = f + "."
                TestString = TestString[-5:-1]
                # Check if the file is a .wav file
                if (os.path.isfile(f) and TestString == ".wav"):
                    self.loadedFiles.append(f)
                    NoFilesLoaded = False
                # Check if the file is a .mp3 file
                elif (os.path.isfile(f) and TestString == ".mp3"):
                    mp3FileDetected = True
            # Clear the ChosenFile dropdown and populate it with the loaded files
            self.ChosenFile.clear()
            for i in range(len(self.loadedFiles)):
                self.ChosenFile.addItem(self.loadedFiles[i])

        # Display an incompatibility message if .mp3 files are detected
        if (mp3FileDetected):
            QMessageBox.information(self, ".mp3 Files not Compatible",
                                    "Convert your file to a .wav for use with this program.", QMessageBox.Ok)
        # Display a warning if no files are loaded
        elif (NoFilesLoaded):
            QMessageBox.warning(self, "No Files Loaded",
                                "Open a Directory that contains .wav files to load them in the program.",
                                QMessageBox.Ok)

    # Saves the current image to an image file. Defaults to a png file but the file type
    # is determined by the extension on the filename the user selects
    def saveAsImage(self):
        # Create a file dialog for saving the image
        dialog = QFileDialog()
        dialog.setFilter(dialog.filter() | QDir.Hidden)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters(['PNG Files (*.png)', 'JPEG Files (*.jpg)', 'Bitmap Files (*.bmp)'])
        dialog.setWindowTitle('Save Image As')
        # Check if the user accepted the file save dialog
        if dialog.exec() == QDialog.Accepted:
            ext = "png"  # Default image extension to "png"
            # Extract the selected image format from the dialog
            list = dialog.selectedNameFilter().split(" ")
            ext = list[len(list) - 1][3:-1]
            dialog.setDefaultSuffix(ext)
            filelist = dialog.selectedFiles()  # Get the list of selected files from the dialog
            # Check if there is at least one selected file
            if len(filelist) > 0:
                file_name = filelist[0] # Get the first selected file as the file name
                try:
                    # Create a QPixmap of the canvas size and render the canvas onto it, and save as an image file
                    pixmap = QPixmap(self.canvas.size())
                    self.canvas.render(pixmap)
                    pixmap.save(file_name)
                except:
                    # Show a warning if there is an issue saving the file
                    QMessageBox.warning(self, "File Not Saved", "The file " + file_name + " could not be saved.",
                                        QMessageBox.Ok)

    # Prints the current image to the printer using the selected printer options from the
    # options list. This function does some initial setup, calls the print dialog box for
    # user input, and then calls printPreview which invokes the printing.
    def printImage(self):
        printer = QPrinter()  # Create a QPrinter object for printing
        dialog = QPrintDialog(printer, self)  # Create a print dialog with the specified printer
        printer.setDocName("MusicImage")  # Set the document name for the printer
        # Define left and top offsets for the printed page
        leftoffset = 36
        topoffset = 36

        printer.setResolution(300)  # Set the printer resolution to 300 DPI
        # Set the page layout to Letter size, landscape orientation, and with specified margins
        pl = QPageLayout(QPageSize(QPageSize.Letter), QPageLayout.Landscape,
                         QMarginsF(leftoffset, topoffset, 36, 36))
        printer.setPageLayout(pl)
        # Check if the user accepted the print dialog
        if dialog.exec() == QDialog.Accepted:
            self.printPreview(printer)  # Call the printPreview method with the configured printer

    # Invokes a print preview of the current image using the selected printer options from the
    # options list.  This function does some initial setup, calls the print preview dialog box,
    # and then calls printPreview which invokes the printing.
    def printPreviewImage(self):
        printer = QPrinter()  # Create a QPrinter object for printing
        dialog = QPrintPreviewDialog(printer)  # Create a QPrintPreviewDialog with the specified printer
        printer.setDocName("MusicImage")  # Set the document name for the printer
        # Set the document name for the printer
        leftoffset = 36
        topoffset = 36

        printer.setResolution(300)  # Set the printer resolution to 300 DPI
        # Set the page layout to Letter size, portrait orientation, and with specified margins
        pl = QPageLayout(QPageSize(QPageSize.Letter), QPageLayout.Portrait,
                         QMarginsF(leftoffset, topoffset, 36, 36))
        printer.setPageLayout(pl)

        dialog.paintRequested.connect(self.printPreview)  # Connect the paintRequested signal to the printPreview method
        dialog.exec()

    # This function does the printing by invoking an off-screen version of the image viewer and
    # rendering it to a pixmap.  This pixmap is then drawn as an image to the painter object
    # attached to the printer.
    def printPreview(self, printer):
        printviewer = ObjectListViewer(self, self.mainapp)  # Create a print viewer
        printres = printer.resolution()  # Get the resolution of the printer
        # Calculate the width and height of the print viewer based on the canvas dimensions
        wid = 7 * printres
        hei = wid * self.canvas.height() / self.canvas.width()
        # Set the fixed size of the print viewer
        printviewer.setFixedSize(QSize(round(wid), round(hei)))
        # Set zoom factor and center of the print viewer to match the canvas
        printviewer.zoomfactor = self.canvas.zoomfactor
        printviewer.center = self.canvas.center
        # Create a QPixmap with the size of the print viewer and render the print viewer onto the pixmap
        pixmap = QPixmap(printviewer.size())
        printviewer.render(pixmap)
        # Create a QPainter for the printer and draw the pixmap onto the printer
        painter = QPainter(printer)
        painter.drawPixmap(QPoint(0, 0), pixmap)
        painter.end()

    # Ending dummy function for print completion
    def print_completed(self, success):
        pass  # Nothing needs to be done

# Check if the script is being run as the main program
if __name__ == '__main__':
    """
    Initiate the program. 
    """
    app = QApplication(sys.argv)
    window = MusicPainter(app)
    progcss = appcss()
    app.setStyleSheet(progcss.getCSS())
    sys.exit(app.exec_())