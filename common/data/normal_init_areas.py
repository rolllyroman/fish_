#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    正常鱼出生点
"""

from scene import WIDTH, HEIGHT, CENTER_X, CENTER_Y
from fish_init_areas import FishInitArea
from common.arith.point_math import Point

"""
FishInitArea(Point(起点1)，Point(起点2)，Point(终点1)，Point(终点2))
鱼会在起点1和起点2中间随机一点生成，游到终点1到终点2中的随机一点
(0,0)点在屏幕左下角，屏幕分辨率1280x720

(0,720)______(1280,720)
        |屏幕|
        |____|
   (0,0)      (1280,0)

WIDTH       =   1280
HEIGHT      =   720
CENTER_X    =   WIDTH/2
CENTER_Y    =   HEIGHT/2
"""

FISh_INIT_AREAS = [
    #左下角靠左
    FishInitArea(Point(0, 0), Point(0, 320), Point(WIDTH, CENTER_Y), Point(WIDTH, HEIGHT)), \
    #下方1
    FishInitArea(Point(265, 0), Point(425, 0), Point(0, HEIGHT), Point(WIDTH-320, HEIGHT)), \
    #下方2
    FishInitArea(Point(665, 0), Point(845, 0), Point(320, HEIGHT), Point(WIDTH, HEIGHT)), \
    #右下角靠下
    FishInitArea(Point(1065, 0), Point(WIDTH, 0), Point(0, HEIGHT), Point(CENTER_X, HEIGHT)), \
    #右下角靠右
    FishInitArea(Point(WIDTH, 0), Point(WIDTH, 190), Point(0, CENTER_Y), Point(0, HEIGHT)), \
    #正右
    FishInitArea(Point(WIDTH, CENTER_Y-100), Point(WIDTH, CENTER_Y+100), Point(0, 0), Point(0, HEIGHT)), \
    #右上角靠右
    FishInitArea(Point(WIDTH, 430), Point(WIDTH, HEIGHT), Point(0, 0), Point(0, CENTER_Y)), \
    #上方1
    FishInitArea(Point(820, HEIGHT), Point(990, HEIGHT), Point(320, 0), Point(WIDTH, 0)), \
    #上方2
    FishInitArea(Point(430, HEIGHT), Point(610, HEIGHT), Point(0, 0), Point(WIDTH-320, 0)), \
    #左上角靠上
    FishInitArea(Point(0, HEIGHT), Point(210, HEIGHT), Point(CENTER_X, 0), Point(WIDTH, 0)), \
    #左上角靠左
    FishInitArea(Point(0, 512), Point(0, HEIGHT), Point(WIDTH, 0), Point(WIDTH, CENTER_Y)), \
    #正左
    FishInitArea(Point(0, CENTER_Y-100), Point(0, CENTER_Y+100),Point(WIDTH, 0), Point(WIDTH, HEIGHT)), \
]