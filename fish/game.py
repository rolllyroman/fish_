# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description: game logic
"""

from common.gameobject import GameObject
from common.common_game import CommonGame
from common import consts
from common.log import log, LOG_LEVEL_RELEASE

from common.data.pickfish_consts import *
from common.logic.fish_manager import FishMgr
from common.logic.bullet import Bullet
from common.logic.bullet_manager import BulletMgr
from common.arith.point_math import Point
from common.data.gun_types import getGunType, FREEZE_TICK, DOUBLE_COIN_RATE, FREEZE_SPEED_RATE, getFreeGun, FREE_GUN_ODDS

from common import pickfish_pb2
from common.pb_utils import *
import random
import time
from datetime import datetime

GOLD_TIME_COUNT_LIMIT = MAX_GOLD_TIME_COUNT - 1
GOLD_TIME_CLICK_AVG_COUNT = int(round(MAX_GOLD_TIME_CLICK_COUNT * 0.85))
#黄金时刻每只增加难度（假设倍率增加）
GOLD_TIME_RATE_UP_STEP = float(GOLD_TIME_CLICK_AVG_COUNT)# / GOLD_TIME_COUNT_LIMIT
GOLD_TIME_ADD_RATE = 1
IN_MULTI_RANGE = (10, 20)
OUT_MULTI_RANGE = (1, 1)
#鱼的密度参数，原始值为150
GAME_FISH_DENSITY = 150#75

LOCK_WAIT_TIME = (30 + 2) * 1000

class Game(CommonGame):
    def __init__(self, desk, maxPlayerPerDesk, server):
        super(Game, self).__init__(desk, maxPlayerPerDesk, server)
        self.desk = desk
        self.players = [None] * maxPlayerPerDesk
        self.rolesCount = 0
        self.server = server

        self.bulletMgr = BulletMgr(None)
        self.fishMgr = FishMgr(self, GAME_FISH_DENSITY)

        self.bgIdx = random.choice(BG_IDX_RANGE)
        self.randomBgIdx()

        self.reset()

        self.__doWhenPickFish = {
            BOMB_FISH_LEVEL         :   self.__pickBomb,
            FREE_BULLET_FISH_LEVEL  :   self.__pickFreeBullet,
            GOLD_TIME_FISH_LEVEL    :   self.__pickGoldTime,
            # LUCKY_BOX_FISH_LEVEL    :   self.__pickLuckyBox,
            FREEZE_FISH_LEVEL       :   self.__pickFreezing,
        }
        self.resetPickFishData()

        #出水结束时间
        self.outCoinRefreshTimestamp = 0
        self.multiLimitRange = IN_MULTI_RANGE
        self.multiLimit = random.randint(*self.multiLimitRange)

        #最大加入ai数控制
        self.getMaxAddAITimestamp = 0
        self.maxAddAI = random.randint(0, 1)

        #锁鱼
        self.account2lockTime = {}

        #全屏冻结结束时间戳
        self.allFreezingOverTimestamp = 0
        self.pickFreezingPlayer = -1

        self.dayNumberPick = {}

        self.pump = 0.997

    def reset(self):
        pass

    def randomBgIdx(self):
        # other_bg_idx_range = list(BG_IDX_RANGE)[:]
        # other_bg_idx_range.remove(self.bgIdx)
        # self.bgIdx = random.choice(other_bg_idx_range)
        self.bgIdx += 1
        if self.bgIdx > len(BG_IDX_RANGE):
            self.bgIdx = 1

    def hasRealPlayerInGame(self):
        """
        return an empty side range[0:maxPlayerCount-1]
        return -1 for full
        """
        for player in self.players:
            if player and not player.isAI:
                return True
        return False

    def __getPlayers(self):
        return [player for player in self.players if player]

    def getTimestamp(self):
        return self.server.getTimestamp()

    def __checkTimestamp(self, timestamp):
        _timestamp = self.getTimestamp()
#        if timestamp > _timestamp + 500:
#            log(u'client timestamp[%s] > [%s]'%(timestamp, _timestamp), LOG_LEVEL_RELEASE)
#            return None
        return _timestamp

    def resetPickFishData(self):
        self.pickedBombFishId = 0
        self.pickedBombFishCoin = 0
        self.pickedFreeBulletFishId = 0
        self.pickedGoldTimeCount = 0
        self.pickedLuckyBoxFishId = 0

    def resolvedPickFishData(self, addCoin, player, bullet, pb, hitTimestamp, timestamp):
        pb.coin = 0
        pb.showCoin = pb.coin
        if self.pickedBombFishId:
            pass
            # pb.bombFishId = self.pickedBombFishId
            # pb.coin = self.pickedBombFishCoin
            # 全部鱼被捕获
            # for fishTmp in self.fishMgr.fishs[:]:
                # if fishTmp.isOut(hitTimestamp):
                    # self.fishMgr.remove(fishTmp)
                    # continue
                # if fishTmp.isIn(hitTimestamp):
                    # pbFish = pb.fishs.add()
                    # pbFish.fishId = fishTmp.id
                    # pbFish.fishRate = fishTmp.multiple
                    # pbFish.gainCoin = formatCoin(bullet.coin * bullet.multi * fishTmp.multiple)#0
                    # if fishTmp.isDice():
                        # pbFish.dice = fishTmp.dice
                    # self.fishMgr.remove(fishTmp)
                # else:
                    # break
        elif self.pickedGoldTimeCount:
            # player.goldTimeCount -= self.pickedGoldTimeCount
            player.goldTimeCount += self.pickedGoldTimeCount
            pb.goldTime.isCompleted = False
            pb.goldTime.count = player.goldTimeCount# % MAX_GOLD_TIME_COUNT
            log(u'player[%s] gold time mission[%s].'%(player.nickname, pb.goldTime.count), LOG_LEVEL_RELEASE)
            #黄金时刻任务完成
            if player.goldTimeCount >= MAX_GOLD_TIME_COUNT:#<= 0:
                log(u'player[%s] start gold time.'%(player.nickname), LOG_LEVEL_RELEASE)
                player.goldTimeCount %= MAX_GOLD_TIME_COUNT
                # if not player.goldTimeCount:
                    # player.goldTimeCount = MAX_GOLD_TIME_COUNT
                # pb.goldTime.count = player.goldTimeCount
                player.goldTimeEndTimestamp = timestamp + (GOLD_TIME_EXIST_TIME+TOLERATE_LAG_SECS) * 1000
                player.gunLevel = bullet.gunLevel
                player.gunCoin = bullet.coin
                pb.goldTime.isCompleted = True
                pb.goldTime.gunLevel = bullet.gunLevel
                pb.goldTime.gunCoin = formatCoin(bullet.coin * GOLD_TIME_ADD_RATE)
                pb.goldTime.durationSecs = GOLD_TIME_EXIST_TIME
                pb.goldTime.maxClickCount = MAX_GOLD_TIME_CLICK_COUNT
                #临时当玩家赢了这么多钱
                self.server.globalCtrl.profit(player, bullet.coin * GOLD_TIME_CLICK_AVG_COUNT)
                if not player.isTrial:
                    pass
                    # self.server.globalCtrl.bet(self, player, bullet.coin, 0, bullet.coin * GOLD_TIME_CLICK_AVG_COUNT)
        elif self.pickedLuckyBoxFishId:
            if not player.isInGoldTime():
                #聚宝盆倍率预算
                totalRate = 0
                luckyBoxes = []
                #随机倍率加成数列
                for i in xrange(5):
                    rate = random.randint(1, 5)
                    totalRate += rate
                    lucky = pickfish_pb2.LuckyBoxData()
                    lucky.coin = formatCoin(bullet.coin * rate)
                    lucky.rate = rate
                    luckyBoxes.append(lucky)

                coin = bullet.coin * totalRate
                # if not player.isTrial:
                    # gainRate, maxPickedRate = self.server.globalCtrl.getGainRate(self, player, addCoin + coin, bullet.coin, bullet.coin*self.multiLimit)
                # else:
                    # gainRate = 1.1
                    # maxPickedRate = 1.0
                gainRate = self.server.globalCtrl.canGainCoin(player, coin, coin)
                # luckyRate = (1.0/totalRate) * player.oddsUpDelta
                dieRate = gainRate #* luckyRate
                odds = random.random()
                log(u'lucky box odds[%s] totalRate[%s] dieRate[%s] gainRate[%s]'%\
                    (odds, totalRate, dieRate, gainRate), LOG_LEVEL_RELEASE)
                #达到抽水的命中率，则发放聚宝盆奖励
                if odds < dieRate:
                    addCoin += coin
                    pb.luckyBoxes.extend(luckyBoxes)
                    self.server.globalCtrl.profit(player, coin)

        #免费炮
        if self.pickedFreeBulletFishId: # and random.random() < FREE_GUN_ODDS:
            gun = getFreeGun()
            gunTypeChangedProto = pickfish_pb2.S_C_GunTypeChanged()
            gunTypeChangedProto.side = player.chair
            gunTypeChangedProto.gunType = gun.type
            player.gunType = gun.type
            player.gunTypeEndTimestamp = timestamp + (gun.duration*1000)
            #log(u'player[%s] get gun[%d] timestamp[%s] endTime[%s] duration[%s]'%(player.nickname, gun.type, hitTimestamp, player.gunTypeEndTimestamp, gun.duration))
            self.sendAll(gunTypeChangedProto)

        return addCoin

    def doWhenPickFish(self, player, fish):
        level = fish.level
        if level in self.__doWhenPickFish:
            return self.__doWhenPickFish[level](player, fish)
        return False

    def __pickBomb(self, player, fish):
        self.pickedBombFishId = fish.id
        log(u'player[%s] pick a bomb fish id[%d] level[%d]'%(player.nickname, fish.id, fish.level), LOG_LEVEL_RELEASE)
        return True

    def __pickFreeBullet(self, player, fish):
        self.pickedFreeBulletFishId = fish.id
        log(u'player[%s] pick a free bullet fish id[%d] level[%d]'%(player.nickname, fish.id, fish.level), LOG_LEVEL_RELEASE)
        return True

    def __pickGoldTime(self, player, fish):
        self.pickedGoldTimeCount += 1
        log(u'player[%s] pick a gold time fish id[%d] level[%d]'%(player.nickname, fish.id, fish.level), LOG_LEVEL_RELEASE)
        return True

    def __pickLuckyBox(self, player, fish):
        self.pickedLuckyBoxFishId = fish.id
        log(u'player[%s] pick a lucky box fish id[%d] level[%d]'%(player.nickname, fish.id, fish.level), LOG_LEVEL_RELEASE)
        return True

    def __pickFreezing(self, player, fish):
        if self.fishMgr.fishArray.isStarted:
            return True
        timestamp =self.getTimestamp()
        allFreezing = pickfish_pb2.S_C_AllFreezing()
        allFreezing.seconds = FREEZING_SECS
        allFreezing.fishLevel = fish.level
        allFreezing.id = fish.id
        allFreezing.endTime = FREEZING_SECS * 1000
        allFreezing.isStarted = False
        allFreezing.side = player.chair
        allFreezing.timestamp = int(timestamp)
        self.sendAll(allFreezing)
        self.fishMgr.freezing(timestamp)
        # 全屏冻结倒计时
        self.allFreezingOverTimestamp = timestamp + FREEZING_SECS * 1000
        self.pickFreezingPlayer = player.chair
        log(u'player[%s] pick a freezing fish id[%d] level[%d]'%(player.account, fish.id, fish.level), LOG_LEVEL_RELEASE)
        return True

    def getFreezingOverTime(self):
        timestamp = self.getTimestamp()
        if self.allFreezingOverTimestamp and timestamp < self.allFreezingOverTimestamp:
            return int(self.allFreezingOverTimestamp - timestamp)
        return 0

    def onTick(self, timestamp):
        timestamp = self.getTimestamp()

        if self.allFreezingOverTimestamp and timestamp >= self.allFreezingOverTimestamp:
            ms = FREEZING_SECS * 1000
            for fish in self.fishMgr.fishs:
                # if not fish.isOut(timestamp):#fish.isIn(timestamp):
                    # fish.timestamp += ms
                if fish.id in self.fishMgr.beFreezeFishes:
                    fish.timestamp += ms
            self.allFreezingOverTimestamp = 0
            self.pickFreezingPlayer = -1
            self.fishMgr.beFreezeFishes = []
            
            resp = pickfish_pb2.S_C_FreezeOver()
            self.sendAll(resp)

        self.fishMgr.refresh(timestamp)
        self.updateGunType(timestamp)

        #动态随机时间切换抽水模式
        if timestamp >= self.outCoinRefreshTimestamp:
            #非出水时间略长
            if self.multiLimitRange is OUT_MULTI_RANGE:
                self.outCoinRefreshTimestamp = timestamp + random.randint(2, 10) * 1000
                self.multiLimitRange = IN_MULTI_RANGE
            else:
                self.outCoinRefreshTimestamp = timestamp + random.randint(4, 16) * 1000
                self.multiLimitRange = OUT_MULTI_RANGE
            self.multiLimit = random.randint(*self.multiLimitRange)
        if timestamp >= self.getMaxAddAITimestamp:
            self.maxAddAI = random.randint(0, 1)
            self.getMaxAddAITimestamp = timestamp + 60 * 1000

        super(Game, self).onTick(timestamp)

    def updateGunType(self, timestamp):
        gunTypeChangedProto = pickfish_pb2.S_C_GunTypeChanged()
        for player in self.__getPlayers():
            if not player.isConnected:
                self.onExitGame(player)
                continue
            if player.gunTypeEndTimestamp:
                if timestamp >= player.gunTypeEndTimestamp:
                    player.gunTypeEndTimestamp = 0
                    player.gunType = GUN_TYPE_NORMAL
                    gunTypeChangedProto.side = player.chair
                    gunTypeChangedProto.gunType = GUN_TYPE_NORMAL
                    self.sendAll(gunTypeChangedProto)
            if player.isInGoldTime():
                if timestamp >= player.goldTimeEndTimestamp:
                    if not player.isTrial:
                        self.server.globalCtrl.profit(player, -(player.gunCoin * GOLD_TIME_CLICK_AVG_COUNT))
                    player.resetGoldTime()
                    goldTimeResult = pickfish_pb2.S_C_GoldTimeResult()
                    goldTimeResult.side = player.chair
                    goldTimeResult.coin = 0
                    goldTimeResult.rate = 0
                    self.sendAll(goldTimeResult)
                    log(u'player[%s] gold time timeout.'%(player.nickname), LOG_LEVEL_RELEASE)

    def onFire(self, player, timestamp, dirX, dirY, bulletIds, gunType):
        _timestamp = self.__checkTimestamp(timestamp)
        if not _timestamp:
            player.invalidCounter('player[%s] game timestamp invalid.'%(player.nickname))
            return

        if len(bulletIds) not in (1, 3):
            log(u'player[%s] fire bulletIds[%s] is invalid.'%(player.nickname, bulletIds), LOG_LEVEL_RELEASE)
            return

        if gunType == GUN_TYPE_FREE and gunType != player.gunType:
            log(u'player[%s] fire gunType is not matched[%s != %s].'%(player.nickname, gunType, player.gunType), LOG_LEVEL_RELEASE)
            return

        if gunType != GUN_TYPE_FREE and player.coin < player.gunCoin:
            log(u'[try fire]player[%s] coin[%d]-[%d] is not enough.'%(player.nickname, player.coin, player.gunCoin), LOG_LEVEL_RELEASE)
            return

        #子弹id校验
        for bulletId in bulletIds:
            bullet = self.bulletMgr.get(bulletId)
            if bullet:
                log(u'player[%s] fire bulletId[%d] already existed.'%(player.nickname, bulletId), LOG_LEVEL_RELEASE)
                return

        player.gunDirX = dirX
        player.gunDirY = dirY

        for bulletId in bulletIds:
            bullet = Bullet(player.chair, player.gunLevel, player.gunCoin, \
                player.gunCoin if player.gunType != GUN_TYPE_FREE else 0, \
                timestamp, Point(0, 0), Point(dirX, dirY), \
                DOUBLE_COIN_RATE if player.gunType == GUN_TYPE_DOUBLE else 1, \
                FREEZE_SPEED_RATE if player.gunType == GUN_TYPE_FREEZE else 1)
            self.bulletMgr.add(bulletId, bullet)

        fireProto = pickfish_pb2.S_C_Fire()
        fireProto.timestamp = timestamp
        fireProto.bulletIds.extend(bulletIds)
        fireProto.side = player.chair
        fireProto.dirX = player.gunDirX
        fireProto.dirY = player.gunDirY
        fireProto.gunType = gunType
        self.sendExclude((player,), fireProto)
        # 开火之后发一次当前的金币记录
        coinRefresh = pickfish_pb2.S_C_CoinRefresh()
        coinRefresh.side = player.chair
        coinRefresh.deltaCoin = formatCoin(-bullet.realCoin)
        self.sendAll(coinRefresh)

        # 奖池代码
        divided = float(bullet.realCoin * 0.003)
        player.curDivied += divided
        player.curPrizePool += int(bullet.realCoin - divided)
        self.PrizePool += int(bullet.realCoin - divided)

        # 计算该玩家的输赢情况
        loseCoin = player.initCoin - player.coin
        botScore = player.initCoin * self.pump

        print(u"玩家金币:%s, 输赢情况:%s, 机率情况:%s" % (player.coin, loseCoin, botScore))
        #uppScore = player.initCoin / 0.997
        #if loseCoin > 0:
            # 输钱
            # number = (player.chanceInterface - player.chanceDefault) / player.chanceDefault
        if player.coin < botScore:
            player.upChance()
            # if not player.lastBotScore:
            #     player.lastBotScore = botScore
            #     if player.coin < botScore:
            #         player.upChance()
            # else:
            #     botScore = player.lastBotScore * 0.9
            #     if player.coin < botScore:
            #         player.upChance()
            #         player.lastBotScore = botScore

        else:
            player.clearChance()
            #if player.coin > uppScore:
            #    player.clearChance()

        log(u'player[%s] fire coin[%s] timestamp[%d] bulletId[%d] dir[%f,%f].'%(player.nickname, player.gunCoin if gunType != GUN_TYPE_FREE else 0, timestamp, bulletId, dirX, dirY), LOG_LEVEL_RELEASE)

    def onFishOut(self, player, timestamp, fishIds):
        timestamp = self.__checkTimestamp(timestamp)
        if not timestamp:
            player.invalidCounter('player[%s] game timestamp invalid.'%(player.nickname))
            return

        for fishId in fishIds:
            fish = self.fishMgr.getFish(fishId)
            if not fish:
                log(u'[try fish out]fish id[%d] is not exist.'%(fishId), LOG_LEVEL_RELEASE)
                continue

            self.fishMgr.remove(fish)
            self.fishMgr.outRemove(fish)
            log(u'[try fish out]fish id[%d] level[%s] remove succeed.'%(fishId, fish.level), LOG_LEVEL_RELEASE)

        self.fishMgr.refresh(timestamp)

    def onHitFish(self, player, timestamp, bulletId, fishIds):
        if not fishIds:
            return

        hitTimestamp = timestamp
        timestamp = self.__checkTimestamp(timestamp)
        if not timestamp:
            player.invalidCounter('player[%s] game timestamp invalid.'%(player.nickname))
            return

        #子弹id校验
        bullet = self.bulletMgr.get(bulletId)
        if not bullet:
            log(u'bulletId[%d] is not existed.'%(bulletId), LOG_LEVEL_RELEASE)
            return

        if bullet.chair != player.chair:
            log(u'player[%s] bulletId[%d] chair[%d] != [%d]'%(player.nickname, bulletId, player.chair, bullet.chair), LOG_LEVEL_RELEASE)
            return

        if bullet.isOver(timestamp):
            log(u'player[%s] bulletId[%d] is out of time.'%(player.nickname, bulletId), LOG_LEVEL_RELEASE)
            return

        #校验是否够钱消耗该子弹
        if player.coin < bullet.realCoin:
            log(u'player[%s] bullet[%d] coin[%d]<[%d] is not enough.'\
                    %(player.nickname, bulletId, player.coin, bullet.realCoin), LOG_LEVEL_RELEASE)
            return

        #减速处理
#        if bullet.decelerate != 1:
#            fish = self.fishMgr.getFish(fishIds[0])
#            if fish:
#                fish.outTimestamp = fish.outTimestamp + FREEZE_TICK*bullet.decelerate

        globalCtrl = self.server.globalCtrl

        # 获取奖池信息
        # globalCtrl.getJoackpot(redis, )

        pickProto = pickfish_pb2.S_C_PickFish()
        pickProto.side = player.chair
        addCoin = 0
        addTmpCoin = 0
        totalRate = 0
        # odds = 1.0
        pickedFishLevels = []
        pickedFishOrders = []
        #记录被击中的第一支鱼
        firstFishLevel = -1
        betDatas = []

        rate = random.random()
        #最多网捕2-4条
        maxCount = random.randint(2, 4)
        for fishId in fishIds[:maxCount]:
            fish = self.fishMgr.getFish(fishId)
            if not fish:
                log(u'fish id[%d] is not exist'%(fishId), LOG_LEVEL_RELEASE)
                break
            if fish.isOut(hitTimestamp):
                self.fishMgr.remove(fish)
                break
            if not fish.isIn(hitTimestamp):
                log(u'fish id[%d] is not in screen'%(fishId), LOG_LEVEL_RELEASE)
                break

            if firstFishLevel == -1:
                firstFishLevel = fish.level
                fish.hitCount += 1
                if self.server.showFishHitCoiunt:
                    fishHitProto = pickfish_pb2.S_C_FishHitCount()
                    fishHitProto.fishId = fish.id
                    fishHitProto.count = fish.hitCount
                    self.sendAll(fishHitProto)
                self.server.globalCtrl.bet(player, bullet.realCoin)

            coin = bullet.coin * bullet.multi * fish.multiple
            tmpCoin = coin
            pickAddCoin = tmpCoin
            #黄金时刻小金蟾越来越难中
            if fish.level == GOLD_TIME_FISH_LEVEL:
                goldTimeMulti = int(GOLD_TIME_RATE_UP_STEP*player.goldTimeCount)#(MAX_GOLD_TIME_COUNT-player.goldTimeCount))
                # tmpCoin = bullet.coin * (bullet.multi*fish.multiple+goldTimeMulti)
                if player.goldTimeCount+ 1 >= MAX_GOLD_TIME_COUNT:
                    pickAddCoin = tmpCoin + bullet.coin * GOLD_TIME_ADD_RATE * MAX_GOLD_TIME_CLICK_COUNT
                fishPickedRate = (1/float(fish.multiple*bullet.multi+goldTimeMulti)) * player.oddsUpDelta
            else:
                fishPickedRate = (fish.pickedRate/bullet.multi) * player.oddsUpDelta
            # if not player.isTrial:
                # gainRate, maxPickedRate = self.server.globalCtrl.getGainRate(self, player, addTmpCoin + tmpCoin, bullet.coin, bullet.coin*self.multiLimit)
            # else:
                # gainRate = 1.1
                # maxPickedRate = 1.0
            if not addCoin:
                print(u"存在奖池")
                fishHitPickedRate = fish.hitPickedRate * player.oddsUpDelta
                #有奖池的情况下,有1/3几率必中第一条鱼
                #if maxPickedRate and rate < 0.334:
                #    fishHitPickedRate = maxPickedRate + 1
            else:
                fishHitPickedRate = 0
            # dieRate = gainRate * (fishPickedRate * odds)

            if fish.level == BOMB_FISH_LEVEL: #炸弹的倍率实际是所有鱼的倍率
                for fishTmp in self.fishMgr.fishs[:]:
                    if fishTmp.isIn(hitTimestamp):
                        pickAddCoin += bullet.coin * bullet.multi * fishTmp.multiple

            level2needCount = globalCtrl.level2needCount
            if fish.level in level2needCount and fish.hitCount < level2needCount[fish.level]:
                # random.seed(int(time.time()))
                # gainRate = random.randint(1, level2needCount[fish.level])

                # 红包鱼

                # 随机组
                # sample = random.sample(xrange(1, (level2needCount[fish.level] + 1) * 10),
                #                        int((level2needCount[fish.level] + 1) * 10 / (( (1 * player.chanceInterface) * 10))))
                # # 从随机组里面取一个
                # gainRate = random.choice(sample)
                playerRate = ((1 * player.chanceInterface) * 10) + 1

                # canPicked = gainRate < playerRate
                gainRate = globalCtrl.canGainCoin(player, pickAddCoin, coin)
                # pickedRate = gainRate * player.oddsUpDelta * player.chanceInterface

                pickedRate = fishPickedRate * player.oddsUpDelta * player.chanceInterface
                ginRandom = random.choice([random.random() for i in range(30)])
                canPicked = ginRandom < pickedRate

                if int(fish.level) == 34 and canPicked:
                    pickedRate = gainRate * player.chanceInterface
                ginRandom = random.choice([ random.random() for i in range(30)])
                canPicked = ginRandom < pickedRate

                print(u"是否击中：%s, 击中随机值:%s, 次数:%s, 总需要次数：%s, 玩家机率:%s, 机率数：%s, 鱼等级:%s" % (canPicked, ginRandom, fish.hitCount, level2needCount[fish.level], player.chanceInterface, playerRate, fish.level))
                # gainRate = 0
                if int(fish.level) == 34 and canPicked:
                    number = self.server.getRedPickFishNumber()
                    print(u"击中红包鱼：已经杀死%s " % number)
                    if number >= 6000:
                        print(u"已经没有红包鱼了.")
                        canPicked = False
                        break
            else:
                if fish.level not in level2needCount:
                    print(u"没有这个等级的鱼：%s" % fish.level)
                    gainRate = globalCtrl.canGainCoin(player, pickAddCoin, coin)
                    pickedRate = gainRate * player.oddsUpDelta * player.chanceInterface

                    pickedRate = fishPickedRate * player.oddsUpDelta * player.chanceInterface
                    ginRandom = random.choice([random.random() for i in range(30)])
                    canPicked = ginRandom < pickedRate
                    print(u"是否击中:%s 机率:%s, 需要机率:%s, 默认机率:%s 提升机率:%s, 玩家机率:%s 计算概率:%s" % (canPicked, ginRandom, pickedRate, gainRate, player.oddsUpDelta, player.chanceInterface, pickedRate))
                else:
                    gainRate = globalCtrl.canGainCoin(player, pickAddCoin, coin)
                    pickedRate = gainRate * player.oddsUpDelta
                    canPicked = True

                if int(fish.level) == 34:
                    # timestamp = time.strftime("%Y-%m-%d", time.localtime())
                    # number = self.dayNumberPick.get(timestamp, 0)
                    number = self.server.getRedPickFishNumber()
                    print(u"击中红包鱼：已经杀死%s " % number)
                    if number >= 6000:
                        print(u"已经没有红包鱼了.")
                        canPicked = False
                        break
            log(u'fish id[%d] level[%d] gainRate[%s] pickedRate[%s] hitPickedRate[%s] rate[%s]'%\
                (fishId, fish.level, gainRate, fishPickedRate, fishHitPickedRate, rate), LOG_LEVEL_RELEASE)
            #达到命中率或鱼被击超额
            #if rate < dieRate or (maxPickedRate and fishHitPickedRate > maxPickedRate):
            # if fish.picked100Percent() or (rate < dieRate or (maxPickedRate and fishHitPickedRate > maxPickedRate)):
            if canPicked:
                pbFish = pickProto.fishs.add()
                pbFish.fishId = fishId
                pbFish.fishRate = fish.multiple
                pbFish.gainCoin = formatCoin(coin)
                pbFish.showGainCoin = pbFish.gainCoin
                if fish.isDice():
                    pbFish.dice = fish.dice

                totalRate += fish.multiple
                # odds *= dieRate
                addCoin += coin
                addTmpCoin += tmpCoin
                pickedFishLevels.append(fish.level)
                pickedFishOrders.append(fish.order)
                self.fishMgr.remove(fish)
                self.fishMgr.pickRemove(fish)
                log(u'player[%s] bulletId[%d] pick fishId[%d] gain coin[%s].'%(player.nickname, bulletId, fishId, coin), LOG_LEVEL_RELEASE)
                self.server.globalCtrl.profit(player, tmpCoin)
                # if not betDatas:
                #     betData = self.tryGetTicket(player, pbFish, coin, bullet.coin)
                #     if betData:
                #         betDatas.append(betData)
                if fish.level == 34:
                    #_timestamp = time.strftime("%Y-%m-%d", time.localtime())
                    #self.dayNumberPick[_timestamp] = self.dayNumberPick.get(_timestamp, 1) + 1
                    self.server.setRedPickFishNumber(player)
                    betData = self.tryGetTicketOnReady(player, pbFish, coin, bullet.coin)
                    if betData:
                        betDatas.append(betData)

                if fish.level == BOMB_FISH_LEVEL:
                    # self.pickedBombFishCoin = formatCoin(coin)
                    pickProto.bombFishId = fishId#self.pickedBombFishId
                    pickProto.coin = formatCoin(coin)
                    pickProto.showCoin = pickProto.coin
                    #全部鱼被捕获
                    for fishTmp in self.fishMgr.fishs[:]:
                        if fishTmp.isOut(hitTimestamp):
                            self.fishMgr.remove(fishTmp)
                            continue
                        if fishTmp.isIn(hitTimestamp):
                            pbFish = pickProto.fishs.add()
                            pbFish.fishId = fishTmp.id
                            pbFish.fishRate = fishTmp.multiple
                            pbFish.gainCoin = formatCoin(bullet.coin * bullet.multi * fishTmp.multiple)#0
                            pbFish.showGainCoin = pbFish.gainCoin
                            if fishTmp.isDice():
                                pbFish.dice = fishTmp.dice
                            self.fishMgr.remove(fishTmp)
                            pickedFishLevels.append(fishTmp.level)
                            pickedFishOrders.append(fishTmp.order)
                            self.server.globalCtrl.profit(player, pbFish.gainCoin)
                            addCoin += pbFish.gainCoin
                        else:
                            break
                if self.doWhenPickFish(player, fish):
                    break
            else:
                #被子弹打中的鱼若没中，提高命中率
                if not addCoin:
                    pass
                    # fish.upRatePerHit()
                break

        #未击中有效鱼，子弹耗币退还，不用处理其它逻辑
        if firstFishLevel == -1:
            self.bulletMgr.remove(bulletId)
            return

        addCoin = self.resolvedPickFishData(addCoin, player, bullet, pickProto, hitTimestamp, timestamp)
        self.resetPickFishData()

        self.bulletMgr.remove(bulletId)

        realAddCoin = player.bet(bullet.realCoin, addCoin, pickedFishLevels if pickedFishLevels else [firstFishLevel], self.server.tax_rate * 0.01)
        taxCoin = addCoin - realAddCoin # - bullet.realCoin
        if betDatas:
            player.betDetail.extend(betDatas)

        #投注通知客户端减币
        # if bullet.realCoin > 0 and addCoin <= 0:
        #     coinRefresh = pickfish_pb2.S_C_CoinRefresh()
        #     coinRefresh.side = player.chair
        #     coinRefresh.deltaCoin = formatCoin(-bullet.realCoin)
        #     self.sendAll(coinRefresh)

        if pickProto.fishs:
            if addCoin > 0:
                for pf in pickProto.fishs:
                    fcoin = reformatCoin(pf.gainCoin)
                    if fcoin > taxCoin:
                        pf.gainCoin = formatCoin(fcoin)
                        break
                if pickProto.coin > taxCoin:
                    pickProto.coin = formatCoin(pickProto.coin-taxCoin)
                # 玩家奖池递减
                self.PrizePool -= fcoin
                player.curPrizePool -= fcoin
            gun = None
            #目前是普通炮才有可能换炮
            if player.gunType == GUN_TYPE_NORMAL:
                gun = getGunType(totalRate)
            # pickProto.coin = formatCoin(realAddCoin) if addCoin > 0 else 0
            self.sendAll(pickProto)
            if gun:
                gunTypeChangedProto = pickfish_pb2.S_C_GunTypeChanged()
                gunTypeChangedProto.side = player.chair
                gunTypeChangedProto.gunType = gun.type
                player.gunType = gun.type
                player.gunTypeEndTimestamp = timestamp + (gun.duration*1000)
                #log(u'player[%s] get gun[%d] timestamp[%s] endTime[%s] duration[%s]'%(player.nickname, gun.type, timestamp, player.gunTypeEndTimestamp, gun.duration))
                self.sendAll(gunTypeChangedProto)

        # if not player.isTrial:
            # self.server.globalCtrl.bet(self, player, bullet.coin, bullet.realCoin, addCoin)
            #self.server.userDBbatchFireNGain(player, bullet.realCoin, addCoin, pickedFishLevels if pickedFishLevels else [firstFishLevel])
        log(u'[betInfo]player[%s][%s] bulletId[%d] bulletCoin[%s][%s] pick fishs[%s] rate[%s] gain coin[%s] bombFishId[%d].'% \
            (player.account, player.coin, bulletId, bullet.coin, bullet.realCoin, pickedFishLevels if pickedFishLevels else [firstFishLevel], totalRate, addCoin, pickProto.bombFishId), LOG_LEVEL_RELEASE)

        self.fishMgr.refresh(timestamp)

    def tryGetTicket(self, player, pickProto, addCoin, betCoin): #获得奖票
        if not addCoin:
            return {}
        if player.nextGetTicketTimestamp > self.getTimestamp():
            return {}
        globalCtrl = self.server.globalCtrl
        if not globalCtrl.ticketCoin: #未开启
            return {}

        coinPool = (-player.totalProfitCoin4Ticket - addCoin + betCoin - globalCtrl.pickTicketNeedCoin)*globalCtrl.pickTicketGetRate
        if coinPool < globalCtrl.ticketCoin: #额度不够
            return {}

        if random.random() > globalCtrl.pickTicketRate: #未击中
            return {}

        maxGetTicketCount = int(coinPool / globalCtrl.ticketCoin)
        if globalCtrl.maxGetTicketCount > 0:
            getTicketCount = min(maxGetTicketCount, globalCtrl.maxGetTicketCount)
        else:
            getTicketCount = maxGetTicketCount
        pickProto.ticket.count = getTicketCount
        pickProto.ticket.coin = globalCtrl.ticketCoin
        betData = {}
        betData['timestamp'] = int(time.time()*1000)
        betData['bet'] = 0
        betData['profit'] = getTicketCount
        betData['fishes'] =[]
        betData['fishes'].extend([TICKET_LEVEL]*getTicketCount)
        # player.betDetail.append(betData)
        player.ticketCount += getTicketCount
        player.addTicketCount += getTicketCount
        player.totalProfitCoin4Ticket += getTicketCount*globalCtrl.ticketCoin#= betCoin - addCoin
        player.nextGetTicketTimestamp = self.getTimestamp() + random.choice(globalCtrl.getTicketWaitTime)
        log(u'[try get ticket]player[%s] ticketCount[%s] addTicketCount[%s] getTicketCount[%s].'\
                %(player.nickname, player.ticketCount, player.addTicketCount, getTicketCount), LOG_LEVEL_RELEASE)
        return betData

    def tryGetTicketOnReady(self, player, pickProto, addCoin, betCoin): #获得奖票

        globalCtrl = self.server.globalCtrl
        if not globalCtrl.ticketCoin:  # 未开启
            return {}

        coinPool = (
                  -player.totalProfitCoin4Ticket - addCoin + betCoin - globalCtrl.pickTicketNeedCoin) * globalCtrl.pickTicketGetRate
        # if coinPool < globalCtrl.ticketCoin:  # 额度不够
        #     return {}

        # maxGetTicketCount = int(coinPool / globalCtrl.ticketCoin)
        # if globalCtrl.maxGetTicketCount > 0:
        #     getTicketCount = min(maxGetTicketCount, globalCtrl.maxGetTicketCount)
        # else:
        #     getTicketCount = maxGetTicketCount
        # 每只红包鱼我都送8张奖券
        getTicketCount = 16

        pickProto.ticket.count = getTicketCount
        pickProto.ticket.coin = globalCtrl.ticketCoin
        betData = {}
        betData['timestamp'] = int(time.time()*1000)
        betData['bet'] = 0
        betData['profit'] = getTicketCount
        betData['fishes'] =[]
        betData['fishes'].extend([TICKET_LEVEL]*getTicketCount)
        # player.betDetail.append(betData)
        player.ticketCount += getTicketCount
        player.addTicketCount += getTicketCount
        player.totalProfitCoin4Ticket += getTicketCount*globalCtrl.ticketCoin#= betCoin - addCoin
        player.nextGetTicketTimestamp = self.getTimestamp() + random.choice([1,2,3,4,5])
        log(u'[try get ticket]player[%s] ticketCount[%s] addTicketCount[%s] getTicketCount[%s].'\
                %(player.nickname, player.ticketCount, player.addTicketCount, getTicketCount), LOG_LEVEL_RELEASE)
        return betData

    def onGoldTimeCount(self, player, count):
        if not player.isInGoldTime():
            log(u'[try gold time count][error]player[%s] is not in gold time.'%(player.nickname), LOG_LEVEL_RELEASE)
            count = 0

        #超出合法点击个数
        if count > MAX_GOLD_TIME_CLICK_COUNT:
            log(u'[try gold time count][error]player[%s] clicked count[%s] is invalid.'%(player.nickname, count), LOG_LEVEL_RELEASE)
            count = MAX_GOLD_TIME_CLICK_COUNT

        #黄金时刻奖励，黄金时刻炮分*点击次数
        addCoin = player.gunCoin * count * GOLD_TIME_ADD_RATE
        realAddCoin = player.bet(0, addCoin, [GOLD_TIME_ITEM_LEVEL], self.server.tax_rate * 0.01)
        #reset
        player.resetGoldTime()

        goldTimeResult = pickfish_pb2.S_C_GoldTimeResult()
        goldTimeResult.side = player.chair
        goldTimeResult.coin = formatCoin(realAddCoin)
        goldTimeResult.rate = count
        self.sendAll(goldTimeResult)

        #临时赢钱反扣回来
        self.server.globalCtrl.profit(player, addCoin - player.gunCoin * GOLD_TIME_CLICK_AVG_COUNT)
        # self.server.globalCtrl.bet(self, player, player.gunCoin, 0, addCoin - player.gunCoin * GOLD_TIME_CLICK_AVG_COUNT)
        #写入账目流水
        if not player.isTrial:
            #self.server.userDBgoldTimeCompleted(player, addCoin)
            log(u'[betInfo]player[%s] completed gold time count[%d] gain coin[%d].'% \
                (player.nickname, count, addCoin), LOG_LEVEL_RELEASE)

    def onSwitchGun(self, player, upgrade):
        if player.isInGoldTime():
            log(u'[try switch gun][error]player[%s] is in gold time.'%(player.nickname), LOG_LEVEL_RELEASE)
            return

        if upgrade:
            player.gunLevel, player.gunCoin = self.server.globalCtrl.upGunLevelNCoin(player.gunLevel, player.gunCoin)
        else:
            player.gunLevel, player.gunCoin = self.server.globalCtrl.deGunLevelNCoin(player.gunLevel, player.gunCoin)

        switchGun = pickfish_pb2.S_C_SwitchGun()
        switchGun.side = player.chair
        switchGun.gunLevel = player.gunLevel
        switchGun.gunCoin = formatCoin(player.gunCoin)
        self.sendExclude((player,), switchGun)

        log(u'player[%s] chair[%d] upgrade[%s] gun to level[%d] coin[%d] succeed.'% \
            (player.nickname, player.chair, upgrade, player.gunLevel, player.gunCoin), LOG_LEVEL_RELEASE)

    def onLockFish(self, player, timestamp, fishId, isLocked):
        # if not player.lockCount: #次数已用完
            # return

        timestamp = self.__checkTimestamp(timestamp)
        if not timestamp:
            player.invalidCounter('player[%s] game timestamp invalid.'%(player.nickname))
            return

        # if player.account in self.account2lockTime:
            # lockTimesTamp = self.account2lockTime[player.account]
        # else:
            # lockTimesTamp = 0
        # nowTimesTamp = self.getTimestamp()
        # if not lockTimesTamp or nowTimesTamp > lockTimesTamp:
            # log(u'[try lock fish][error] account[%s] is not lock time[%s] out[%s].'%(self.getTimestamp(), nowTimesTamp), LOG_LEVEL_RELEASE)
            # return

        fish = self.fishMgr.getFish(fishId)
        if not fish:
            log(u'fish id[%d] is not exist'%(fishId), LOG_LEVEL_RELEASE)
            return

        # player.lockCount -= 1

        lockFishProto = pickfish_pb2.S_C_LockFish()
        lockFishProto.side = player.chair
        lockFishProto.fishId = fishId
        lockFishProto.isLocked = isLocked
        self.sendExclude((player,), lockFishProto)

    def onLockFishStart(self, player):
        lockFishProto = pickfish_pb2.S_C_LockFishStart()
        # if player.lockCount <= 0: #次数已用完
            # log(u'[try lock fish start][error] account[%s] is not lockCount.'%(player.account), LOG_LEVEL_RELEASE)
            # lockFishProto.result = False
            # lockFishProto.count = 0
            # self.sendOne(player, lockFishProto)

        self.account2lockTime[player.account] = self.getTimestamp() + LOCK_WAIT_TIME
        # self.server.saveLockFishData(player)
        lockFishProto.result = True
        lockFishProto.count = player.lockCount
        self.sendOne(player, lockFishProto)

    def destroy(self):
        self.fishMgr.destroy()
        self.bulletMgr.destroy()

    def doAfterJoinGame(self, player, isSendMsg):
        if self.allFreezingOverTimestamp:
            allFreezing = pickfish_pb2.S_C_AllFreezing()
            allFreezing.seconds = FREEZING_SECS
            allFreezing.fishLevel = FREEZE_FISH_LEVEL
            allFreezing.id = 0
            allFreezing.endTime = self.getFreezingOverTime()
            allFreezing.isStarted = True
            allFreezing.side = self.pickFreezingPlayer
            allFreezing.timestamp = int(self.allFreezingOverTimestamp - FREEZING_SECS * 1000)
            self.sendOne(player, allFreezing)

