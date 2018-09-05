#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    protobuf utilities
"""
from common.fish_data_pb2 import RouteNode

def pbAppendRoute(route, rotSpeed, speed, duration):
    node = RouteNode()
    node.rotSpeed = rotSpeed
    node.speed = speed
    node.duration = duration
    route.append(node)
    return route

def pbPlayMessage(resp, game, side, score, bird, player = None, hu = None):
    resp.kong = game.giveKongCount[side]
    resp.concealedKong.extend(game.players[side].mahjongList.concealedKongTiles)
    resp.exposed.extend(game.players[side].mahjongList.kongTiles)
    resp.score = score
    resp.bird = bird
    resp.nickname = game.players[side].nickname
    resp.side = side
    resp.mahjong.extend(game.players[side].mahjongList.getTiles())
    resp.points = game.points[side]
    resp.pong.extend(game.players[side].mahjongList.pongTiles)
    if hu:
        resp.hu = hu
    return resp

def pbAppendFishesBatch(fishesBatch, fishList):
    """
    """
    _batch = fishesBatch.add()
    for fish in fishList:
        _fish = _batch.fishes.add()
        _fish.level = fish.level
        _fish.rot = fish.initRot
        _fish.x = fish.x
        _fish.y = fish.y
        _fish.dice = fish.dice
        _fish.duration = fish.duration
        _fish.offset = fish.timestampOffset
        _fish.route.extend(fish.route)
    return fishesBatch

def pbAppendFishesData(fishes, fishList):
    """
    """
    for fish in fishList:
        _fish = fishes.add()
        _fish.level = fish.level
        _fish.rot = fish.initRot
        _fish.x = fish.x
        _fish.y = fish.y
        _fish.dice = fish.dice
        _fish.duration = fish.duration
        _fish.offset = fish.timestampOffset
        _fish.route.extend(fish.route)
    return fishes

def pbPlayedData(resp, mySide, side, game):
    player = game.players[side]
    concealedKongTiles = player.mahjongList.concealedKongTiles
    playedData = resp.add()
    playedData.side = side
    playedData.kong.extend(player.mahjongList.kongTiles)
    playedData.pong.extend(player.mahjongList.pongTiles)
    playedData.playedTile.extend(player.mahjongList.playedTile)
    # 暗杠
    # if player.account != player.account:
        # concealedKongTiles = [''] * len(concealedKongTiles)
    playedData.concealedKong.extend(concealedKongTiles)
    if side != mySide:
        playedData.isOnline = game.isInGame[playerSide]
    else:
        playedData.isOnline = True
    return resp

def formatCoin(coin):
    return int(coin)

def pbPlayerInfo(resp, game, side, isNeedMyData = False):
    player = game.players[side]
    resp.side = side
    resp.nickname = player.nickname
    resp.coin = int(player.coin)
    resp.ip = player.ip #gamePlayer.region
    resp.sex = player.sex
    resp.headImgUrl = player.headImgUrl
    if isNeedMyData:
        resp.roomCards = player.roomCards
        resp.isGM = player.isGM
        resp.id = int(player.uid)
        resp.account = player.account
    resp.gunLevel = formatCoin(player.gunLevel)
    resp.gunCoin = formatCoin(player.gunCoin)
    resp.goldTimeCount = player.goldTimeCount
    resp.ticket = player.ticketCount
    resp.lockCount = player.lockCount
    return resp

def pbCopyGunLevels(pbObj, gunLevels):
    for gunLevel in gunLevels:
        _gunLevel = pbObj.gunLevels.add()
        _gunLevel.level = gunLevel.level
        _gunLevel.coinMin = formatCoin(gunLevel.coinRange[0])
        _gunLevel.coinMax = formatCoin(gunLevel.coinRange[1])
        _gunLevel.stepCoin = formatCoin(gunLevel.stepCoin)

    return pbObj

def pbAppendFishList(fishList, fish, showHitCount):
    _fish = fishList.add()
    _fish.id = fish.id
    _fish.idx = fish.idx
    _fish.timestamp = fish.timestamp
    _fish.outTimestamp = fish.outTimestamp
    _fish.isDice = fish.isDice()
    if showHitCount:
        _fish.hitCount = fish.hitCount
    return fishList

def pbRoomInfo(resp, server, game):
    resp.roomId =  "%06d"%(int(game.roomId))
    resp.roomName = game.roomName.decode('utf-8')
    resp.timestamp = game.server.getTimestamp()
    resp.roomSetting = game.ruleDescs
    resp.playerCount = game.maxPlayerCount
    resp.bulletSpeeds.extend(game.server.globalCtrl.bulletSpeeds)
    resp.fishesCapacity.extend(game.server.globalCtrl.fishesCapacity)
    pbCopyGunLevels(resp, game.server.globalCtrl.gunLevels)
    resp.bgIdx = game.bgIdx
    resp.isArray = game.fishMgr.fishArray.isStarted
    fishes = game.fishMgr.getValidFishes()
    for fish in fishes:
        pbAppendFishList(resp.fishList, fish, game.server.showFishHitCoiunt)
    return resp

def pbBalanceData(player, resp):
    resp.nickname = player.nickname
    resp.side = player.chair
    resp.id = int(player.uid)
    if player.game and player.game.ownner:
        resp.isOwner =False
    else:
        resp.isOwner = (player.chair == 0)
    resp.roomSetting = player.game.ruleDescs
    resp.timestamp = player.game.server.getTimestamp()
    resp.headImgUrl = player.headImgUrl
    resp.isDealer = (player == player.game.dealer)
    return resp

def reformatCoin(coin):
    return float(coin)

def pbAppendPlayerList(playerList, player):
    _playerInfo = playerList.add()
    _playerInfo.side = player.chair
    _playerInfo.nickname = player.nickname
    _playerInfo.coin = formatCoin(player.coin)
    _playerInfo.gunLevel = player.gunLevel
    _playerInfo.gunCoin = formatCoin(player.gunCoin)
    _playerInfo.goldTimeCount = player.goldTimeCount
    return playerList

def pbAppendRank(rankList, rank, nickname, score, level=None):
    _rankInfo = rankList.add()
    _rankInfo.rank = rank
    _rankInfo.nickname = nickname
    _rankInfo.score = score
    if level is not None:
        _rankInfo.level = level
    return rankList

