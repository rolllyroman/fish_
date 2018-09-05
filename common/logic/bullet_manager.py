# -*- coding:utf-8 -*-
#!/bin/python

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
子弹管理类
"""

from common.gameobject import GameObject

class BulletMgr(GameObject):
    def __init__(self, destroyCallback):
        self.bulletIds = {}
        self.destroyCallback = destroyCallback

    def destroyByPlayer(self, player):
        chair = player.chair
        delBullets = [id for id, bullet in self.bulletIds.iteritems() if bullet.chair == chair]
        for id in delBullets:
            #bullet = self.bulletIds[id]
            #子弹销毁时需要返回玩家钱
            #player.coin += bullet.realCoin
            del self.bulletIds[id]

    def destroy(self):
        self.bulletIds.clear()

    def get(self, id):
        if id not in self.bulletIds:
            return None
        return self.bulletIds[id]

    def add(self, id, bullet):
        assert id not in self.bulletIds
        self.bulletIds[id] = bullet

    def remove(self, id):
        assert id in self.bulletIds
        del self.bulletIds[id]