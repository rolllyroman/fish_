# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
点线算法及结构
"""

from common.gameobject import GameObject
import math

def clamp(val, min, max):
    if min > max:
        min, max = max, min
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val

class Point(GameObject):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, factor):
        assert isinstance(factor, float) or isinstance(factor, int)
        return Point(self.x * factor, self.y * factor)

    def __neg__(self):
        return Point(-self.x, -self.y)

    def midPoint(self, other):
        return CPoint((self.x + other.x)/2.0, (self.y + other.y)/2.0)

    def forRadian(self, r):
        self.x = math.cos(r)
        self.y = math.sin(r)

    def getLen(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        _len = self.getLen()
        if 0 == _len:
            return CPoint(1.0, 0.0)
        return Point(self.x / _len, self.y / _len)

    def cross(self, other):
        return self.x * other.y - self.y * other.x

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def toRadian(self):
        return math.atan2(self.y, self.x)

    def getRadian(self, other):
        n1 = self.normalize()
        n2 = other.normalize()
        r = math.atan2(n1.cross(n2), n1.dot(n2))
        if math.fabs(r) < 1.192092896e-7:
            return 0.0

        return radian

    def getDist(self, other):
        return self.__sub__(other).getLen()

    def perp(self):
        return Point(-self.y, self.x)

    def rPerp(self):
        return Point(self.y, -self.x)

    def project(self, other):
        factor = self.dot(other) / other.dot(other)
        return Point(other.x * factor, other.y * factor)

    def rotate(self, other):
        return Point(self.x * other.x - self.y * other.y, self.x * other.y + self.y * other.x)

    def unrotae(self, other):
        return Point(self.x * other.x + self.y * other.y, self.y * other.x + self.x * other.y)

    def getClampPoint(self, p1, p2):
        return Point(clamp(self.x, p1.x, p2.x), clamp(self.y, p1.y, p2.y))

    def lerp(self, other, alpha):
        return self.__mul__(1.0 - alpha).__add__(other.__mul__(alpha))

    def fuzzyEqual(self, other, v):
        return (self.x - v <= other.x) and (other.x <= self.x + v) and (self.y - v < other.y) and (other.y <= self.y + v)

    def rotateByRadian(self, other, r):
        rp = Point(0, 0)
        rp.forRadian(r)
        return other.__add__(self.__sub__(other).rotate(rp))

    def rotateSelfByRadian(self, r):
        rp = Point(0, 0)
        rp.forRadian(r)
        return self.rotate(rp)

    def __repr__(self):
        return "Point(%s, %s)"%(self.x, self.y)

    __str__ = __repr__

def isLineIntersect(p1, p2, p3, p4):
    if (p1.x == p2.x and p1.y == p2.y) or (p3.x == p4.x and p4.y == p4.y):
        return False, 0.0, 0.0

    l21x = p2.x - p1.x
    l21y = p2.y - p1.y
    l43x = p4.x - p3.x
    l43y = p4.y - p4.y
    l13x = p1.x - p3.x
    l13y = p1.y - p3.y

    denom = l43y * l21x - l43x * l21y
    s = l43x * l13y - l43y * l13x
    t = l21x * l13y - l21y * l13x

    if denom == 0:
        if (s == 0 and t == 0):
            return True, s, t
        return False, s, t

    s = s / denom
    t = t / denom

    return True, s, t

def isSegmentIntersect(p1, p2, p3, p4):
    ret, s, t = isLineIntersect(p1, p2, p3, p4)
    return ret and s >= 0.0 and s <= 1.0 and t >= 0.0 and t <= 1.0

def getIntersectPoint(p1, p2, p3, p4):
    ret, s, t = isLineIntersect(p1, p2, p3, p4)
    if ret:
        return Point(p1.x + s * (p2.x - p1.x), p1.y + s * (p2.y - p1.y))
    else:
        return None


