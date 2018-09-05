# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
鱼类
"""

from common.gameobject import GameObject
from common.data.pickfish_consts import TOLERATE_LAG_SECS

ALLFISHS = range(33)

class Fish(GameObject):
    def __init__(self, id, idx, level, order, timestamp, initRot, initX, initY, outDuration, multiple, pickedRate, dice, route):
        self.id = id
        self.idx = idx
        self.level = level
        self.order = order
        self.timestamp = timestamp
        self.initRot = initRot
        self.initX = initX
        self.initY = initY
        self.outTimestamp = self.timestamp + int((outDuration+TOLERATE_LAG_SECS)*1000)
        self.multiple = multiple
        #命中率，网中以此为准
        if multiple:
            self.pickedRate = 1/float(multiple)
        else:
            self.pickedRate = pickedRate
        #击中命中率，只有子弹击中有效，网中无效
        self.hitPickedRate = 0.0
        self.upRateDeltaPerHit = self.pickedRate
        self.dice = dice
        self.route = route
        self.hitCount = 0

    def upRatePerHit(self):
        self.hitPickedRate += self.upRateDeltaPerHit

    def isIn(self, timestamp):
        return timestamp >= self.timestamp

    def isNearCenter(self, timestamp):
        return timestamp >= self.timestamp + 2000 and timestamp <= self.timestamp + 5000

    def isOut(self, timestamp):
        return timestamp >= self.outTimestamp

    def isDice(self):
        return self.dice > 0

    def picked100Percent(self):
        return False #return self.level in ALLFISHS

    def __str__(self):
        return 'fish id[%s] level[%s]'%(self.id, self.level)

    __repr__ = __str__
