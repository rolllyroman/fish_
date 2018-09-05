# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
子弹
"""

from common.gameobject import GameObject
from common.data.pickfish_consts import BULLET_EXIST_TICK

class Bullet(GameObject):
    def __init__(self, chair, gunLevel, coin, realCoin, timestamp, startPoint, direction, multi, decelerate):
        self.chair = chair
        self.gunLevel = gunLevel
        self.coin = coin
        self.realCoin = realCoin
        self.timestamp = timestamp
        self.startPoint = startPoint
        self.direction = direction
        self.multi = multi
        self.decelerate = decelerate

    def isOver(self, timestamp):
        return timestamp - self.timestamp >= BULLET_EXIST_TICK
