# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
鱼出生区域配置
FishInitArea出生点区域
start_min                   最小出生点
start_max                   最大出生点
target_min                  最小目标点
target_max                  最大目标点
"""

from common.gameobject import GameObject
import random

class FishInitArea(GameObject):
    def __init__(self, start_min, start_max, target_min, target_max):
        self.start_min = start_min
        self.start_max = start_max
        self.target_min = target_min
        self.target_max = target_max

    def getPointNDirect(self):
        targetPoint = self.target_min.lerp(self.target_max, random.random())
        startPoint = self.start_min.lerp(self.start_max, random.random())
        #startPoint = (self.start_max - self.start_min) * random.random()
        return startPoint, (targetPoint - startPoint).normalize(), targetPoint
