# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
捕鱼游戏相关常量
"""
# room type
ROOM_TYPE_NORMAL = 1

# room sub type
ROOM_SUB_TYPE_SIMPLE = 1

# fish
FISH_SEQMODE_UNKNOWN        =   -1
FISH_SEQMODE_SINGLE         =   0           #单体，随机自由游动
FISH_SEQMODE_COLONY         =   1           #集群，有一个母鱼随机移动，其它集群分子会随母鱼方向及速度而变
FISH_SEQMODE_ONEBYONE       =   2           #一条条首尾相随的鱼
FISH_SEQMODE_SIDEBYSIDE     =   3           # 一条条平行并肩的鱼

GUN_TYPE_NORMAL = 0
GUN_TYPE_DOUBLE = 1
GUN_TYPE_ENERGY = 2
GUN_TYPE_FREEZE = 3
GUN_TYPE_FREE = 4

BOMB_FISH_LEVEL = 19
FREE_BULLET_FISH_LEVEL = 32
GOLD_TIME_FISH_LEVEL =30
LUCKY_BOX_FISH_LEVEL = 31
FREEZE_FISH_LEVEL = 33
GOLD_TIME_ITEM_LEVEL = 1001
TICKET_LEVEL = 5000

#全屏冻结秒数
FREEZING_SECS = 15

MAX_GOLD_TIME_COUNT = 1
GOLD_TIME_EXIST_TIME = 8
GOLD_TIME_PICK_SPACE = 0.01
MAX_GOLD_TIME_CLICK_COUNT = int(GOLD_TIME_EXIST_TIME / GOLD_TIME_PICK_SPACE)

TOLERATE_LAG_SECS = 15

BULLET_EXIST_TICK = 30 * 1000

FISH_EXT_DURATION = 60

BG_IDX_RANGE = (1,2,3,4,5)

FISH_ARRAY_APPEAR_SEC = (150, 300)

DEFAULT_TRIAL_COIN = 10

LANG_CODE = 'utf8'


FISH_ATTRIBUTE_LEVELS = "fish:level:%s:hesh"
FISH_ORDER_ATTRIBUTE_LIST = "fish:level:order:set"