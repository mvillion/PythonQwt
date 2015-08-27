# -*- coding: utf-8 -*-
#
# Licensed under the terms of the Qwt License
# (see qwt/LICENSE for details)

from qwt.qt.QtGui import QColor, qRed, qGreen, qBlue, qRgb, qRgba, qAlpha
from qwt.qt.QtCore import Qt, qIsNaN


class ColorStop(object):
    def __init__(self, pos=0., color=None):
        self.pos = pos
        if color is None:
            self.rgb = 0
        else:
            self.rgb = color.rgba()
        self.r = qRed(self.rgb)
        self.g = qGreen(self.rgb)
        self.b = qBlue(self.rgb)
        self.a = qAlpha(self.rgb)
        
        #  when mapping a value to rgb we will have to calcualate: 
        #     - const int v = int( ( s1.v0 + ratio * s1.vStep ) + 0.5 );
        #  Thus adding 0.5 ( for rounding ) can be done in advance
        self.r0 = self.r + 0.5
        self.g0 = self.g + 0.5
        self.b0 = self.b + 0.5
        self.a0 = self.a + 0.5
        
        self.rStep = self.gStep = self.bStep = self.aStep = 0.
        self.posStep = 0.
        
    def updateSteps(self, nextStop):
        self.rStep = nextStop.r - self.r
        self.gStep = nextStop.g - self.g
        self.bStep = nextStop.b - self.b
        self.aStep = nextStop.a - self.a
        self.posStep = nextStop.pos - self.pos


class ColorStops(object):
    def __init__(self):
        self.__doAlpha = False
        self.__stops = []
        self.stops = []
    
    def insert(self, pos, color):
        if pos < 0. or pos > 1.:
            return
        if len(self.__stops) == 0:
            index = 0
            self.__stops = [None]
        else:
            index = self.findUpper(pos)
            if index == len(self.__stops) or\
               abs(self.__stops[index].pos-pos) >= .001:
                self.__stops.append(None)
                for i in range(len(self.__stops)-1, index, -1):
                    self.__stops[i] = self.__stops[i-1]
        self.__stops[index] = ColorStop(pos, color)
        if color.alpha() != 255:
            self.__doAlpha = True
        if index > 0:
            self.__stops[index-1].updateSteps(self.__stops[index])
        if index < len(self.__stops)-1:
            self.__stops[index].updateSteps(self.__stops[index+1])
    
    def stops(self):
        return [stop.pos for stop in self.__stops]
    
    def findUpper(self, pos):
        index = 0
        n = len(self.__stops)
        
        stops = self.__stops
        
        while n > 0:
            half = n >> 1
            middle = index + half
            if stops[middle].pos <= pos:
                index = middle + 1
                n -= half + 1
            else:
                n = half
        return index
    
    def rgb(self, mode, pos):
        if pos <= 0.:
            return self.__stops[0].rgb
        if pos >= 1.0:
            return self.__stops[-1].rgb
        
        index = self.findUpper(pos)
        if mode == QwtLinearColorMap.FixedColors:
            return self.__stops[index-1].rgb
        else:
            s1 = self.__stops[index-1]
            ratio = (pos-s1.pos)/s1.posStep
            r = int(s1.r0 + ratio*s1.rStep)
            g = int(s1.g0 + ratio*s1.gStep)
            b = int(s1.b0 + ratio*s1.bStep)
            if self.__doAlpha:
                if s1.aStep:
                    a = int(s1.a0 + ratio*s1.aStep)
                    return qRgba(r, g, b, a)
                else:
                    return qRgba(r, g, b, s1.a)
            else:
                return qRgb(r, g, b)


class QwtColorMap(object):
    
    # enum Format
    RGB, Indexed = list(range(2))
    
    def __init__(self, format_=None):
        if format_ is None:
            format_ = self.RGB
        self.__format = format_
    
    def color(self, interval, value):
        if self.__format == self.RGB:
            return QColor.fromRgba(self.rgb(interval, value))
        else:
            index = self.colorIndex(interval, value)
            return self.colorTable(interval)[index]
    
    def format(self):
        return self.__format
    
    def colorTable(self, interval):
        table = [0] * 256
        if interval.isValid():
            step = interval.width()/(len(table)-1)
            for i in range(len(table)):
                table[i] = self.rgb(interval, interval.minValue()+step*i)
        return table


class QwtLinearColorMap_PrivateData(object):
    def __init__(self):
        self.colorStops = None
        self.mode = None


class QwtLinearColorMap(QwtColorMap):
    
    # enum Mode
    FixedColors, ScaledColors = list(range(2))
    
    def __init__(self, *args):
        color1, color2 = QColor(Qt.blue), QColor(Qt.yellow)
        format_ = QwtColorMap.RGB
        if len(args) == 1:
            format_, = args
        elif len(args) == 2:
            color1, color2 = args
        elif len(args) == 3:
            color1, color2, format_ = args
        elif len(args) != 0:
            raise TypeError("%s() takes 0, 1, 2 or 3 argument(s) (%s given)"\
                            % (self.__class__.__name__, len(args)))
        super(QwtLinearColorMap, self).__init__(format_)
        self.__data = QwtLinearColorMap_PrivateData()
        self.__data.mode = self.ScaledColors
        self.setColorInterval(color1, color2)
    
    def setMode(self, mode):
        self.__data.mode = mode
    
    def mode(self):
        return self.__data.mode
    
    def setColorInterval(self, color1, color2):
        self.__data.colorStops = ColorStops()
        self.__data.colorStops.insert(0., QColor(color1))
        self.__data.colorStops.insert(1., QColor(color2))
    
    def addColorStop(self, value, color):
        if value >= 0. and value <= 1.:
            self.__data.colorStops.insert(value, QColor(color))
    
    def colorStops(self):
        return self.__data.colorStops.stops()
    
    def color1(self):
        return QColor(self.__data.colorStops.rgb(self.__data.mode, 0.))
    
    def color2(self):
        return QColor(self.__data.colorStops.rgb(self.__data.mode, 1.))
    
    def rgb(self, interval, value):
        if qIsNaN(value):
            return 0
        width = interval.width()
        if width <= 0.:
            return 0
        ratio = (value-interval.minValue())/width
        return self.__data.colorStops.rgb(self.__data.mode, ratio)
    
    def colorIndex(self, interval, value):
        width = interval.width()
        if qIsNaN(value) or width <= 0. or value <= interval.minValue():
            return 0
        if value >= interval.maxValue():
            return 255
        ratio = (value-interval.minValue())/width
        if self.__data.mode == self.FixedColors:
            return int(ratio*255)
        else:
            return int(ratio*255+.5)
    

class QwtAlphaColorMap_PrivateData(object):
    def __init__(self):
        self.color = None
        self.rgb = None
        self.rgbMax = None

class QwtAlphaColorMap(QwtColorMap):
    def __init__(self, color):
        super(QwtAlphaColorMap, self).__init__(QwtColorMap.RGB)
        self.__data = QwtAlphaColorMap_PrivateData()
        self.setColor(color)
    
    def setColor(self, color):
        self.__data.color = color
        self.__data.rgb = color.rgb() & qRgba(255, 255, 255, 0)
        self.__data.rgbMax = self.__data.rgb | ( 255 << 24 )
    
    def color(self):
        return self.__data.color()
    
    def rgb(self, interval, value):
        if qIsNaN(value):
            return 0
        width = interval.width()
        if width <= 0.:
            return 0
        if value <= interval.minValue():
            return self.__data.rgb
        if value >= interval.maxValue():
            return self.__data.rgbMax
        ratio = (value-interval.minValue())/width
        return self.__data.rgb | (int(round(255*ratio)) << 24)
