#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Author: $Author$
Date: $Date$
Revision: $Revision$

Description:
    国际化文本模板
"""

#注册文本信息
REG_TIPS_ALREADY_LOGON = '已登录。'
REG_TIPS_EMPTY_ACCOUNT_PASSWD = '账号和密码不能为空。'
REG_TIPS_INVALID_ACCOUNT = "账号不合法（必须为字母开头，总长度4-18的大小写字母、数字、下划线）。"
REG_TIPS_INVALID_PASSWD = "密码不合法（必须为总长度6-20的合法字符）。"
REG_TIPS_ACCOUNT_EXIST = '账号已存在，请重新输入。'


LOGIN_TIPS_INVALID_ACCOUNT_PASSWD = '账号或密码不正确，请重新输入。'
LOGIN_TIPS_ALREADY_LOGON = '账号已登录。'
LOGIN_TIPS_TIMEOUT = '登录超时或不合法，请重新进入游戏。'
LOGIN_TIPS_INVALID_ACCOUNT = '登录失败，账号已被冻结，请联系管理员。'

TRANSFER_TIPS_NOT_ENOUGH = '钱包余额不足，请充值或调小转账金额。'
TRANSFER_TIPS_INTERNAL_ERROR = '钱包系统正在维护中，请稍后再试。'
TRANSFER_TIPS_ALREADY_DO = '正在转账处理中，请稍后。'

GAME_CLOSE_TIPS = '游戏服务因进行维护即将关闭，我们将尽快重新开启服务，详情请留意网站公告。'
