# -*- coding:utf-8 -*-

"""
清除捕鱼投注记录
"""

import redis_instance
from common.common_db_define import *

redis = redis_instance.getInst(1)

for key in redis.keys(PLAYER_FISH_BET_DATA4ALL%('*')):
    redis.delete(key)
for key in redis.keys(PLAYER_FISH_BET_DATA4DAY%('*', '*')):
    redis.delete(key)
for key in redis.keys(PLAYER_FISH_BET_DATA_DETAIL%('*')):
    redis.delete(key)
for key in redis.keys(PLAYER_FISH_BET_DATA_DETAIL4DAY%('*', '*')):
    redis.delete(key)
for key in redis.keys(AGENT_FISH_BET_DATA4ALL%('*')):
    redis.delete(key)
for key in redis.keys(AGENT_FISH_BET_DATA4DAY%('*', '*')):
    redis.delete(key)
for key in redis.keys(AGENT_FISH_BET_DATA_DETAIL%('*', '*')):
    redis.delete(key)
redis.delete(ALL_FISH_BET_DATA4ALL)
for key in redis.keys(ALL_FISH_BET_DATA4DAY%('*')):
    redis.delete(key)
for key in redis.keys(ALL_FISH_BET_DATA_DETAIL%('*')):
    redis.delete(key)
for key in redis.keys(FISH_BET_DATA4ROOM%('*')):
    redis.delete(key)
for key in redis.keys(FISH_BET_DATA4DAY4ROOM%('*', '*')):
    redis.delete(key)
for key in redis.keys(FISH_BET_DATA_DETAIL4ROOM%('*', '*')):
    redis.delete(key)

# 清除红包数据
for key in redis.keys("fish:redpick:fish:*:number"):
    redis.delete(key)

# 清除分成与收益
redis.delete("fish:room:jackpot:divied:hesh")
redis.delete("fish:room:jackpot:hesh")
redis.delete("fish:redpick:account:hesh")

# 清除每月签到数据
for key in redis.keys("sign:fish:user:numbers:*:receive:hesh"):
    redis.delete(key)

for key in redis.keys("sign:fish:user:numbers:*:hesh"):
    redis.delete(key)

for key in redis.keys("sign:fish:*:*:hesh"):
    redis.delete(key)

for key in redis.keys("sign:fish:*:*:hesh"):
    redis.delete(key)

# 清除玩家盈利
redis.delete("users:coinDeltaTmp:zset")
redis.delete("users:coinTmp:zset")
redis.delete("users:coinDelta:zset")
redis.delete("users:coinDeltaTmp:zset")


# 清除玩家金幣和獎卷
userDict = {
    "coin_delta": 0,
    "coin": 0,
    "exchange_ticket": 0,
    "ticket_profit": 0,
}

for key in redis.keys("users:[1234567890]*"):
    redis.hmset(key,
                userDict
                )

