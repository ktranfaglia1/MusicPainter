import random

from PySide2.QtGui import (QColor)
import numpy as np


class PaintBrush:
    def __init__(self, parent=None):
        self.RLData = []
        self.LineList = []
        self.TriangleList = []
        self.Parent = parent
        self.mainapp = parent
        self.rl = self.mainapp.rl
        self.fl = self.mainapp.freqlist

        # self.Parent.StopSoundData()

        # To add an algorithm:
        # 1. Update numberAlgorithms below.
        # 2. Add in new algorithm function.
        # 3. Add in additional elif in the draw function.

        self.numberAlgorithms = 13
        self.currentAlgorithm = 1

    # Resets the links to the renderlist and frequency data in the main. S

    def SetAlg6(self):
        self.RLData = [1, 1, 1, -1, -1, -1, -1, 1, 0]
        self.TriangleList = []

    def SetAlg2345(self):
        self.RLData = [0, 0, 0]

    def SetAlg7(self):
        self.RLData = [3.14159265359, .1, .1, True, 0, True]

    def SetAlg8(self):
        self.RLData = [3.14159265359, .025, .1, True, 0, 0, .025]

    def SetAlg9(self):
        self.RLData = [True, 0, 0]
        self.TriangleList = []
        self.LineList = []

    def SetAlg10(self):
        self.RLData = [0, 0]

    def SetAlg13(self):
        self.RLData = [0, 0, 0, 0, 0,]
        self.avgList = []

    def getRBG(self, RBGVal):
        RBG = [0, 0, 0]
        if RBGVal >= 0 and RBGVal <= 255:
            RBG[0] = 255
            RBG[1] = 0
            RBG[2] = RBGVal
        elif RBGVal >= 255 and RBGVal <= 510:
            RBG[0] = 255 - (RBGVal - 255)
            RBG[1] = 0
            RBG[2] = 255
        elif RBGVal >= 510 and RBGVal <= 765:
            RBG[0] = 0
            RBG[1] = RBGVal - 510
            RBG[2] = 255
        elif RBGVal >= 765 and RBGVal <= 1020:
            RBG[0] = 0
            RBG[1] = 255
            RBG[2] = 255 - (RBGVal - 765)
        elif RBGVal >= 1020 and RBGVal <= 1275:
            RBG[0] = RBGVal - 1020
            RBG[1] = 255
            RBG[2] = 0
        elif RBGVal >= 1275 and RBGVal <= 1530:
            RBG[0] = 255
            RBG[1] = 255 - (RBGVal - 1275)
            RBG[2] = 0
        return RBG

    def resetlistlinks(self):
        self.rl = self.mainapp.rl
        self.fl = self.mainapp.freqlist

    # Accessor functions for the render and frequency lists.
    def getRenderList(self, n):
        if n >= 0 and n < len(self.rl):
            return self.rl[n]
        else:
            return None

    def getFrequencyList(self, n):
        if n >= 0 and n < len(self.fl):
            return self.fl[n]
        else:
            return None

    def getLastRenderList(self, n):
        if n > 0 and n <= len(self.rl):
            return self.rl[len(self.rl) - n]
        else:
            return None

    def getLastFrequencyList(self, n):
        if n > 0 and n <= len(self.fl):
            return self.fl[len(self.fl) - n]
        else:
            return None

    # Object creation for adding to the renderlist.
    #  0 = point, 1 = line, 2 = circle, 3 = rectangle
    def makePoint(self, x, y, col):
        newcol = QColor(col)
        return [0, x, y, newcol]

    def makeLine(self, x1, y1, x2, y2, col):
        newcol = QColor(col)
        return [1, x1, y1, x2, y2, newcol]

    def makeCircle(self, cx, cy, rad, fill, col):
        newcol = QColor(col)
        return [2, cx, cy, rad, fill, newcol]

    def makeRectangle(self, ULx, ULy, LRx, LRy, fill, col):
        newcol = QColor(col)
        return [3, ULx, ULy, LRx, LRy, fill, newcol]

    def makeTriangle(self, x1, y1, x2, y2, x3, y3, fill, col):
        newcol = QColor(col)
        return [4, x1, y1, x2, y2, x3, y3, fill, newcol]

    # Render function gateway.
    def draw(self, data, datapos, spectdata, active):
        if self.currentAlgorithm == 1:
            self.algorithm1(data, datapos)
        elif self.currentAlgorithm == 2:
            self.algorithm2(data, spectdata)
        elif self.currentAlgorithm == 3:
            self.algorithm3(data, spectdata)
        elif self.currentAlgorithm == 4:
            self.algorithm4(data, spectdata)
        elif self.currentAlgorithm == 5:
            self.algorithm5(data, spectdata)
        elif self.currentAlgorithm == 6:
            self.algorithm6(data, spectdata)
        elif self.currentAlgorithm == 7:
            self.algorithm7(data, spectdata)
        elif self.currentAlgorithm == 8:
            self.algorithm8(data, spectdata)
        elif self.currentAlgorithm == 9:
            self.algorithm9(data, spectdata)
        elif self.currentAlgorithm == 10:
            self.algorithm10(data, spectdata)
        elif self.currentAlgorithm == 11:
            self.algorithm11(data, datapos)
        elif self.currentAlgorithm == 12:
            self.algorithm12(data)
        elif self.currentAlgorithm == 13:
            self.algorithm13(data, active)

    # Rendering Algorithms.

    # def algorithm1(self, data):
    #    rx1 = np.random.random() * 2 - 1
    #    ry1 = np.random.random() * 2 - 1
    #    rx2 = np.random.random() * 2 - 1
    #    ry2 = np.random.random() * 2 - 1
    #    rx3 = np.random.random() * 2 - 1
    #    ry3 = np.random.random() * 2 - 1

    #    col = QColor()
    #    col.setRgbF(np.random.random(), np.random.random(), np.random.random(), 1)
    #    clear = QColor()
    #    clear.setRgbF(1, 1, 1, 1)
    #    self.rl.add(self.makeRectangle(-1, 1, 1, -1, True, clear))
    #    self.rl.add(self.makeTriangle(rx1, ry1, rx2, ry2, rx3, ry3, True, col))

    # def algorithm2(self, data, pos):
    #    numfreq = len(self.fl)
    #    maxfreq = 5000
    #    x = 2 * pos / numfreq - 1
    #    y = data[0] / maxfreq

    #    col = QColor()
    #    col.setRgbF(1, 0, 0, 1)
    #    self.rl.add(self.makeLine(x, 0.25, x, y + .25, col))

    #    if len(data) > 1:
    #        y = data[1] / maxfreq
    #        col.setRgbF(0, 1, 0, 1)
    #        self.rl.add(self.makeLine(x, -.75, x, y - .75, col))

    def algorithm1(self, data, pos):
        numfreq = len(self.fl)
        maxfreq = 2000
        x = 2 * pos / numfreq - 1
        y = data[0] / maxfreq * 2

        col = QColor()
        col.setRgbF(1, 0, 0, 1)
        y = (sum(data) / len(data)) / maxfreq

        self.rl.add(self.makeCircle(x, y - 0.5, 0.01, True, col))

    def algorithm2(self, data, spectdata):
        self.RLData[2] += 0.1
        theta = self.RLData[2] % np.pi * 2
        amp = data[0] % 1

        x = np.cos(theta) * amp
        y = np.sin(theta) * amp

        col = QColor()
        col.setRgb(200, (spectdata % 200) + 55, (data[0] % 100) + 55, 255)
        self.rl.add(self.makeLine(self.RLData[0], self.RLData[1], x, y, col))

        self.RLData[0] = x
        self.RLData[1] = y

    def algorithm3(self, data, spectdata):
        theta = data[0] % np.pi * 2
        amp = data[0] % 1

        x = np.cos(theta) * amp
        y = np.sin(theta) * amp

        col = QColor()
        col.setRgb((spectdata % 155) + 100, 100, (data[0] % 155) + 100, 255)
        self.rl.add(self.makeLine(self.RLData[0], self.RLData[1], x, y, col))

        self.RLData[0] = x
        self.RLData[1] = y

    def algorithm4(self, data, spectdata):
        self.RLData[2] += 0.1
        theta = self.RLData[2] % np.pi * 2

        x = np.sin(10 * theta)
        y = np.sin(8 * theta)

        col = QColor()
        col.setRgb(175, (spectdata % 200) + 55, (data[0] % 100) + 155, 255)
        self.rl.add(self.makeLine(self.RLData[0], self.RLData[1], x, y, col))

        self.RLData[0] = x
        self.RLData[1] = y

    def algorithm5(self, data, spectdata):
        self.RLData[2] += 0.1
        theta = self.RLData[2] % np.pi * 2

        x = (np.cos(theta) - np.cos(9 * theta)) / 2
        y = (np.sin(theta) - np.sin(9 * theta)) / 2

        col = QColor()
        col.setRgb(50, (spectdata % 155) + 100, (data[0] % 155) + 100, 255)
        self.rl.add(self.makeLine(self.RLData[0], self.RLData[1], x, y, col))

        self.RLData[0] = x
        self.RLData[1] = y

    def algorithm6(self, data, spect):
        TriCol = QColor()
        Hue = data[0] * 10
        TriCol.setHsv(Hue, 255, 130, 255)

        LineCol = QColor()
        LineCol.setHsv(Hue, 0, 200, 255)

        Distance = pow(pow(self.RLData[0], 2) + pow(self.RLData[1], 2), .5)

        if (Distance > 0.05):

            if (spect >= 200000):
                WeightedFreqVal = 15.0
            elif (spect <= 10000):
                WeightedFreqVal = 30
            else:
                WeightedFreqVal = ((((spect - 10000) / 190000) * 15) + 15)

            Newx1 = (((WeightedFreqVal * self.RLData[0]) + self.RLData[6]) / (WeightedFreqVal + 1))
            Newy1 = (((WeightedFreqVal * self.RLData[1]) + self.RLData[7]) / (WeightedFreqVal + 1))
            Newx2 = (((WeightedFreqVal * self.RLData[2]) + self.RLData[0]) / (WeightedFreqVal + 1))
            Newy2 = (((WeightedFreqVal * self.RLData[3]) + self.RLData[1]) / (WeightedFreqVal + 1))
            Newx3 = (((WeightedFreqVal * self.RLData[4]) + self.RLData[2]) / (WeightedFreqVal + 1))
            Newy3 = (((WeightedFreqVal * self.RLData[5]) + self.RLData[3]) / (WeightedFreqVal + 1))
            Newx4 = (((WeightedFreqVal * self.RLData[6]) + self.RLData[4]) / (WeightedFreqVal + 1))
            Newy4 = (((WeightedFreqVal * self.RLData[7]) + self.RLData[5]) / (WeightedFreqVal + 1))

            self.rl.add(self.makeTriangle(self.RLData[0], self.RLData[1], Newx1, Newy1, Newx2, Newy2, True, TriCol))
            self.rl.add(self.makeTriangle(self.RLData[2], self.RLData[3], Newx2, Newy2, Newx3, Newy3, True, TriCol))
            self.rl.add(self.makeTriangle(self.RLData[4], self.RLData[5], Newx3, Newy3, Newx4, Newy4, True, TriCol))
            self.rl.add(self.makeTriangle(self.RLData[6], self.RLData[7], Newx4, Newy4, Newx1, Newy1, True, TriCol))

            self.rl.add(self.makeLine(self.RLData[0], self.RLData[1], self.RLData[2], self.RLData[3], LineCol))
            self.rl.add(self.makeLine(self.RLData[2], self.RLData[3], self.RLData[4], self.RLData[5], LineCol))
            self.rl.add(self.makeLine(self.RLData[4], self.RLData[5], self.RLData[6], self.RLData[7], LineCol))
            self.rl.add(self.makeLine(self.RLData[6], self.RLData[7], self.RLData[0], self.RLData[1], LineCol))

            self.TriangleList.append([[self.RLData[0], self.RLData[1]], [Newx1, Newy1], [Newx2, Newy2]])
            self.TriangleList.append([[self.RLData[2], self.RLData[3]], [Newx2, Newy2], [Newx3, Newy3]])
            self.TriangleList.append([[self.RLData[4], self.RLData[5]], [Newx3, Newy3], [Newx4, Newy4]])
            self.TriangleList.append([[self.RLData[6], self.RLData[7]], [Newx4, Newy4], [Newx1, Newy1]])

            self.RLData[0] = Newx1
            self.RLData[2] = Newx2
            self.RLData[4] = Newx3
            self.RLData[6] = Newx4
            self.RLData[1] = Newy1
            self.RLData[3] = Newy2
            self.RLData[5] = Newy3
            self.RLData[7] = Newy4
        else:
            self.RLData[8] += 1
            if (self.RLData[8] * 4 >= len(self.TriangleList)):
                self.RLData[8] = 1
            for i in range(((self.RLData[8] - 1) * 4), (self.RLData[8] * 4)):
                Triangle = self.TriangleList[i]
                self.rl.add(
                    self.makeTriangle(Triangle[0][0], Triangle[0][1], Triangle[1][0], Triangle[1][1], Triangle[2][0],
                                      Triangle[2][1], True, TriCol))
                self.rl.add(self.makeLine(Triangle[0][0], Triangle[0][1], Triangle[1][0], Triangle[1][1], LineCol))
                self.rl.add(self.makeLine(Triangle[0][0], Triangle[0][1], Triangle[2][0], Triangle[2][1], LineCol))

    def algorithm7(self, data, spect):
        if (self.RLData[3]):
            self.RLData[4] = data[0]
        else:
            if (data[0] > self.RLData[4]):
                self.RLData[4] = data[0]
        LineCol = QColor()
        if self.RLData[4] > 0:
            RedGreen = ((data[0] / self.RLData[4]) * 510) - 255
            if (RedGreen < 0):
                LineCol.setRgb(0, abs(RedGreen), 255)
            else:
                LineCol.setRgb(RedGreen, 0, 255)
        else:
            LineCol.setRgb(0, 0, 255)

        if (self.RLData[5]):
            if (spect >= 200000):
                SizeMultiplier = 1.3
            elif (spect <= 10000):
                SizeMultiplier = 1
            else:
                SizeMultiplier = ((((spect - 10000) / 190000) * .3) + 1)
        else:
            if (spect >= 200000):
                SizeMultiplier = .7
            elif (spect <= 10000):
                SizeMultiplier = 1
            else:
                SizeMultiplier = (1 - (((spect - 10000) / 190000) * .3))

        P1x = self.RLData[1] * np.cos((self.RLData[0] * .5) + self.RLData[2])
        P1y = self.RLData[1] * np.sin((self.RLData[0] * .5) + self.RLData[2])
        P2x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 2 / 11)) + self.RLData[2])
        P2y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 2 / 11)) + self.RLData[2])
        P3x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 4 / 11)) + self.RLData[2])
        P3y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 4 / 11)) + self.RLData[2])
        P4x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 6 / 11)) + self.RLData[2])
        P4y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 6 / 11)) + self.RLData[2])
        P5x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 8 / 11)) + self.RLData[2])
        P5y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 8 / 11)) + self.RLData[2])
        P6x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 10 / 11)) + self.RLData[2])
        P6y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 10 / 11)) + self.RLData[2])
        P7x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 12 / 11)) + self.RLData[2])
        P7y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 12 / 11)) + self.RLData[2])
        P8x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 14 / 11)) + self.RLData[2])
        P8y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 14 / 11)) + self.RLData[2])
        P9x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 16 / 11)) + self.RLData[2])
        P9y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 16 / 11)) + self.RLData[2])
        P10x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 18 / 11)) + self.RLData[2])
        P10y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 18 / 11)) + self.RLData[2])
        P11x = self.RLData[1] * np.cos((self.RLData[0] * (.5 - 20 / 11)) + self.RLData[2])
        P11y = self.RLData[1] * np.sin((self.RLData[0] * (.5 - 20 / 11)) + self.RLData[2])

        self.rl.add(self.makeLine(P1x, P1y, P6x, P6y, LineCol))
        self.rl.add(self.makeLine(P6x, P6y, P11x, P11y, LineCol))
        self.rl.add(self.makeLine(P11x, P11y, P5x, P5y, LineCol))
        self.rl.add(self.makeLine(P5x, P5y, P10x, P10y, LineCol))
        self.rl.add(self.makeLine(P10x, P10y, P4x, P4y, LineCol))
        self.rl.add(self.makeLine(P4x, P4y, P9x, P9y, LineCol))
        self.rl.add(self.makeLine(P9x, P9y, P3x, P3y, LineCol))
        self.rl.add(self.makeLine(P3x, P3y, P8x, P8y, LineCol))
        self.rl.add(self.makeLine(P8x, P8y, P2x, P2y, LineCol))
        self.rl.add(self.makeLine(P2x, P2y, P7x, P7y, LineCol))
        self.rl.add(self.makeLine(P7x, P7y, P1x, P1y, LineCol))

        self.RLData[1] *= SizeMultiplier
        if (self.RLData[5] and self.RLData[1] > 1):
            self.RLData[5] = False
        if (self.RLData[5] == False and self.RLData[1] < .1):
            self.RLData[5] = True
        self.RLData[2] += .03
        if (self.RLData[3]):
            self.RLData[3] = False

    def algorithm8(self, data, spect):
        CircCol = QColor()
        CircCol2 = QColor()
        if (self.RLData[3]):
            self.RLData[4] = data[0]
        else:
            if (data[0] > self.RLData[4]):
                self.RLData[4] = data[0]

        if len(data) > 1:
            if (self.RLData[3]):
                self.RLData[5] = data[1]
            else:
                if (data[0] > self.RLData[5]):
                    self.RLData[5] = data[0]
            if self.RLData[5] > 0:
                Freq2 = int((data[1] / self.RLData[5]) * 1530)
            else:
                Freq2 = 0
            RedGreenBlue2 = self.getRBG(Freq2)

        if self.RLData[4] > 0:
            Freq = int((data[0] / self.RLData[4]) * 1530)
        else:
            Freq = 0
        RedGreenBlue = self.getRBG(Freq)

        if (spect >= 200000):
            Radius = .2
        elif (spect <= 10000):
            Radius = .1
        else:
            Radius = ((((spect - 10000) / 190000) * .1) + .1)

        P1x = self.RLData[1] * np.cos((self.RLData[0] * .5) + self.RLData[2])
        P1y = self.RLData[1] * np.sin((self.RLData[0] * .5) + self.RLData[2])
        P2x = self.RLData[6] * np.cos((self.RLData[0] * 1.5) + self.RLData[2])
        P2y = self.RLData[6] * np.sin((self.RLData[0] * 1.5) + self.RLData[2])

        for i in range(10):
            CircCol.setRgb(RedGreenBlue[0], RedGreenBlue[1], RedGreenBlue[2], int(255 * ((i + 1) * .1)))
            self.rl.add(self.makeCircle(P1x, P1y, Radius / (i + 1), True, CircCol))
        if len(data) > 1:
            for i in range(10):
                CircCol2.setRgb(RedGreenBlue2[0], RedGreenBlue2[1], RedGreenBlue2[2], int(255 * ((i + 1) * .1)))
                self.rl.add(self.makeCircle(P2x, P2y, Radius / (i + 1), True, CircCol2))

        if (self.RLData[1] > 1):
            self.RLData[1] = 1
        elif (self.RLData[1] < 1):
            self.RLData[1] += .05

        if (self.RLData[6] > .5):
            self.RLData[6] = .5
        elif (self.RLData[6] < .5):
            self.RLData[6] += .025

        self.RLData[2] += .1

        if (self.RLData[3]):
            self.RLData[3] = False

    def algorithm9(self, data, spect):

        TriCol = QColor()
        Hue = data[0] * 10
        TriCol.setHsv(Hue, 255, 130, 255)

        if (self.RLData[0]):
            Point1 = [0, .05]
            Point2 = [(pow(3, (1 / 2)) / 40), (-1 / 40)]
            Point3 = [((pow(3, (1 / 2)) / 40) * -1), (-1 / 40)]
            Line1 = [Point1, Point2]
            Line2 = [Point2, Point3]
            Line3 = [Point3, Point1]
            Triangle = [Point1, Point2, Point3]
            self.LineList.append(Line1)
            self.LineList.append(Line2)
            self.LineList.append(Line3)
            self.TriangleList.append(Triangle)
            self.rl.add(
                self.makeTriangle(Triangle[0][0], Triangle[0][1], Triangle[1][0], Triangle[1][1], Triangle[2][0],
                                  Triangle[2][1], True, TriCol))
            self.RLData[0] = False
        else:
            if len(self.LineList) > 0:
                if (spect >= 200000):
                    Height = .08
                elif (spect <= 10000):
                    Height = .02
                else:
                    Height = ((((spect - 10000) / 190000) * .06) + .02)
                FoundTri = False
                while FoundTri == False:
                    LineIndex = random.randrange(0, (len(self.LineList) - 1))
                    Line = self.LineList[LineIndex]
                    MidPoint = [((Line[0][0] + Line[1][0]) / 2), ((Line[0][1] + Line[1][1]) / 2)]
                    UsedTri = []
                    for i in self.TriangleList:
                        if ((Line[0] == i[0]) or (Line[0] == i[1]) or (Line[0] == i[2])) and (
                                (Line[1] == i[0]) or (Line[1] == i[1]) or (Line[1] == i[2])):
                            UsedTri = i
                    if (UsedTri[0][0] == UsedTri[1][0]) or (UsedTri[0][1] == UsedTri[1][1]):
                        Line1 = [UsedTri[1], UsedTri[2]]
                        Line2 = [UsedTri[2], UsedTri[0]]
                    elif (UsedTri[1][0] == UsedTri[2][0]) or (UsedTri[1][1] == UsedTri[2][1]):
                        Line1 = [UsedTri[0], UsedTri[1]]
                        Line2 = [UsedTri[2], UsedTri[0]]
                    else:
                        Line1 = [UsedTri[0], UsedTri[1]]
                        Line2 = [UsedTri[1], UsedTri[2]]
                    Line1Normal = -1 / ((Line1[1][1] - Line1[0][1]) / (Line1[1][0] - Line1[0][0]))
                    Line1MidPoint = [((Line1[0][0] + Line1[1][0]) / 2), ((Line1[0][1] + Line1[1][1]) / 2)]
                    Line2Normal = -1 / ((Line2[1][1] - Line2[0][1]) / (Line2[1][0] - Line2[0][0]))
                    Line2MidPoint = [((Line2[0][0] + Line2[1][0]) / 2), ((Line2[0][1] + Line2[1][1]) / 2)]
                    XPos = (((-1 * Line2Normal * Line2MidPoint[0]) + Line2MidPoint[1] + (
                            Line1Normal * Line1MidPoint[0]) - Line1MidPoint[1]) / (Line1Normal - Line2Normal))
                    YPos = Line1Normal * (XPos - Line1MidPoint[0]) + Line1MidPoint[1]
                    TriPoint = [XPos, YPos]
                    DeltaX = MidPoint[0] - TriPoint[0]
                    DeltaY = MidPoint[1] - TriPoint[1]
                    Distance = pow((pow(DeltaX, 2) + pow(DeltaY, 2)), .5)
                    Ratio = (Height + Distance) / Distance
                    Point = [(TriPoint[0] + (DeltaX * Ratio)), (TriPoint[1] + (DeltaY * Ratio))]
                    Line1 = Line[0], Point
                    Line2 = Line[1], Point
                    Triangle = [Line[0], Line[1], Point]
                    if ((self.ValidTriangle(Triangle)) and (self.ValidPoint(Point))):
                        self.LineList.append(Line1)
                        self.LineList.append(Line2)
                        self.TriangleList.append(Triangle)
                        self.rl.add(self.makeTriangle(Triangle[0][0], Triangle[0][1], Triangle[1][0], Triangle[1][1],
                                                      Triangle[2][0], Triangle[2][1], True, TriCol))
                        FoundTri = True
                    self.LineList.pop(LineIndex)
            else:
                Triangle = self.TriangleList[self.RLData[2]]
                self.rl.add(
                    self.makeTriangle(Triangle[0][0], Triangle[0][1], Triangle[1][0], Triangle[1][1], Triangle[2][0],
                                      Triangle[2][1], True, TriCol))
                self.RLData[2] += 1
                if (self.RLData[2] > (len(self.TriangleList) - 1)):
                    self.RLData[2] = 0

    def algorithm10(self, data, spectdata):
        self.RLData[0] += 0.51
        self.RLData[1] += 0.51
        theta = self.RLData[0] % np.pi * 2

        if (self.RLData[1] <= np.pi):
            x = np.cos(theta) / 1.06
            y = np.sin(theta) / 1.06
        elif (self.RLData[1] <= np.pi * 2):
            x = np.cos(theta) / 1.28
            y = np.sin(theta) / 1.28
        elif (self.RLData[1] <= np.pi * 3):
            x = np.cos(theta) / 1.6
            y = np.sin(theta) / 1.6
        elif (self.RLData[1] <= np.pi * 4):
            x = np.cos(theta) / 2.1
            y = np.sin(theta) / 2.1
        elif (self.RLData[1] <= np.pi * 5):
            x = np.cos(theta) / 2.95
            y = np.sin(theta) / 2.95
        elif (self.RLData[1] <= np.pi * 6):
            x = np.cos(theta) / 4.8
            y = np.sin(theta) / 4.8
        elif (self.RLData[1] <= np.pi * 7):
            x = np.cos(theta) / 12.0
            y = np.sin(theta) / 12.0
        else:
            self.RLData[1] = 0

        if (self.RLData[1] != 0):
            col = QColor()
            col.setRgb((spectdata % 155) + 100, 75, (data[0] % 75) + 180, 255)
            self.rl.add(self.makeCircle(x, y, 0.05, True, col))

    def algorithm11(self, data, pos):
        col = QColor()

        if (len(data) > 1):
            avg = (data[0] + data[1]) / 2
        else:
            avg = data[0]

        x = pos / 1000 * np.cos(5 * pos / 1000 * 2 * np.pi)
        y = pos / 1000 * np.sin(5 * pos / 1000 * 2 * np.pi)

        if (avg > 326):
            col.setRgbF(1, 0, 0, 1)
            # self.rl.add(self.makePoint(x,y,col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))
        elif (250 < avg <= 325):
            col.setRgbF(avg / 1000, 1, avg / 2000, 1)
            # self.rl.add(self.makePoint(x,y,col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))
        else:
            col.setRgbF(0, 0, 0, 1)
            # self.rl.add(self.makePoint(x, y, col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))

    def algorithm12(self, data):

        col = QColor()

        if (len(data) > 1):
            avg = (data[0] + data[1]) / 2
        else:
            avg = data[0]

        # x = np.random.random() * 2 - 1
        # y = np.random.random() * 2 - 1

        # x = np.cos(pos/len(self.fl)*2*np.pi)
        # y = np.sin(pos / len(self.fl) * 2 * np.pi)

        # x = pos/len(self.fl) * np.cos(pos/len(self.fl)*2*np.pi)
        # y = pos/len(self.fl) * np.sin(pos / len(self.fl) * 2 * np.pi)

        x = np.random.random() * 2 - 1
        y = np.random.random() * 2 - 1

        if (avg > 300):
            col.setRgbF(1, 0, 0, 1)
            # self.rl.add(self.makePoint(x,y,col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))
        elif (201 < avg <= 299):
            col.setRgbF(0.5, 0, 0, 1)
            # self.rl.add(self.makePoint(x,y,col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))
        elif (150 < avg <= 200):
            col.setRgbF(0, 1, 0, 1)
            # self.rl.add(self.makePoint(x,y,col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))
        else:
            col.setRgbF(0, 0, 0, 1)
            # self.rl.add(self.makePoint(x, y, col))
            self.rl.add(self.makeRectangle(x - 0.05, y + 0.05, x + 0.05, y - 0.05, True, col))

    def algorithm13(self, data, active):
        if (len(data) > 1):
            avg = (data[0] + data[1]) / 2
        else:
            avg = data[0]
        # print(avg)
        self.avgList.append(avg)

        if (not active):
            if (self.RLData[0] == 0):
                self.RLData[1] = -1
                self.RLData[2] = 1

                self.RLData[3] = -.33
                self.RLData[4] = .33

            elif (self.RLData[0] == 1):
                self.RLData[1] = -.33
                self.RLData[2] = .33

                self.RLData[3] = .33
                self.RLData[4] = 1

            elif (self.RLData[0] == 2):
                self.RLData[1] = .33
                self.RLData[2] = 1

                self.RLData[3] = 1
                self.RLData[4] = .33

            elif (self.RLData[0] == 3):
                self.RLData[1] = -1
                self.RLData[2] = .33

                self.RLData[3] = -.33
                self.RLData[4] = -.33

            elif (self.RLData[0] == 4):
                self.RLData[1] = -.33
                self.RLData[2] = .33

                self.RLData[3] = .33
                self.RLData[4] = -.33

            elif (self.RLData[0] == 5):
                self.RLData[1] = .33
                self.RLData[2] = .33

                self.RLData[3] = 1
                self.RLData[4] = -.33

            elif (self.RLData[0] == 6):
                self.RLData[1] = -1
                self.RLData[2] = -.33

                self.RLData[3] = -.33
                self.RLData[4] = -1

            elif (self.RLData[0] == 7):
                self.RLData[1] = -.33
                self.RLData[2] = -1

                self.RLData[3] = .33
                self.RLData[4] = -.33

            elif (self.RLData[0] == 8):
                self.RLData[1] = .33
                self.RLData[2] = -.33

                self.RLData[3] = 1
                self.RLData[4] = -1

            if (self.RLData[0] < 8):
                self.RLData[0] += 1
            else:
                self.RLData[0] = 0

            totalAvg = 0.0
            count = 0
            for i in self.avgList:
                    totalAvg += self.avgList.pop(count)
                    count += 1
            totalAvg /= count
            print(totalAvg)
            self.avgList.clear()
            col = QColor()
            if (totalAvg < 50):
                col.setRgbF(0, 0, 0, 1)
            elif (totalAvg < 210):
                col.setRgbF(.1, .1, 1, 1)
            elif (totalAvg < 550):
                col.setRgbF(.5, .8, .7, 1)
            elif (totalAvg < 2000):
                col.setRgbF(1, 0, 0, 1)
            else:
                col.setRgbF(0, 1, 0, 1)

        # if (self.RLData[0] < 8):
        #     self.RLData[0] += 1
        # else:
        #     self.RLData[0] = 0

        if (not active):
            self.rl.add(self.makeRectangle(self.RLData[1], self.RLData[2], self.RLData[3], self.RLData[4], True, col))

    def ValidTriangle(self, Triangle):
        Valid = True
        for i in self.TriangleList:
            if not (Triangle[0] == i[0] or Triangle[0] == i[1] or Triangle[1] == i[0] or Triangle[1] == i[1]):
                if (self.intersect(Triangle[0], Triangle[1], i[0], i[1])):
                    Valid = False
            if not (Triangle[0] == i[1] or Triangle[0] == i[2] or Triangle[1] == i[1] or Triangle[1] == i[2]):
                if (self.intersect(Triangle[0], Triangle[1], i[1], i[2])):
                    Valid = False
            if not (Triangle[0] == i[2] or Triangle[0] == i[0] or Triangle[1] == i[2] or Triangle[1] == i[0]):
                if (self.intersect(Triangle[0], Triangle[1], i[2], i[0])):
                    Valid = False
            if not (Triangle[1] == i[0] or Triangle[1] == i[1] or Triangle[2] == i[0] or Triangle[2] == i[1]):
                if (self.intersect(Triangle[1], Triangle[2], i[0], i[1])):
                    Valid = False
            if not (Triangle[1] == i[1] or Triangle[1] == i[2] or Triangle[2] == i[1] or Triangle[2] == i[2]):
                if (self.intersect(Triangle[1], Triangle[2], i[1], i[2])):
                    Valid = False
            if not (Triangle[1] == i[2] or Triangle[1] == i[0] or Triangle[2] == i[2] or Triangle[2] == i[0]):
                if (self.intersect(Triangle[1], Triangle[2], i[2], i[0])):
                    Valid = False
            if not (Triangle[2] == i[0] or Triangle[2] == i[1] or Triangle[0] == i[0] or Triangle[0] == i[1]):
                if (self.intersect(Triangle[2], Triangle[0], i[0], i[1])):
                    Valid = False
            if not (Triangle[2] == i[1] or Triangle[2] == i[2] or Triangle[0] == i[1] or Triangle[0] == i[2]):
                if (self.intersect(Triangle[2], Triangle[0], i[1], i[2])):
                    Valid = False
            if not (Triangle[2] == i[2] or Triangle[2] == i[0] or Triangle[0] == i[2] or Triangle[0] == i[0]):
                if (self.intersect(Triangle[2], Triangle[0], i[2], i[0])):
                    Valid = False
        return Valid

    def ValidPoint(self, Point):
        Valid = True
        if (Point[0] > 1) or (Point[0] < -1):
            Valid = False
        if (Point[1] > 1) or (Point[1] < -1):
            Valid = False
        return Valid

    # https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    # Author: Bryce Boe
    # Last Updated: 10/23/2006

    def ccw(self, Point1, Point2, Point3):
        return (Point3[1] - Point1[1]) * (Point2[0] - Point1[0]) > (Point2[1] - Point1[1]) * (Point3[0] - Point1[0])

    # https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    # Author: Bryce Boe
    # Last Updated: 10/23/2006

    def intersect(self, A, B, C, D):
        return self.ccw(A, C, D) != self.ccw(B, C, D) and self.ccw(A, B, C) != self.ccw(A, B, D)