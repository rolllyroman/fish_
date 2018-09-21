import redis
import random

redis = redis.Redis(host='127.0.0.1',password="Fkkg65NbRwQOnq01OGMPy5ZREsNUeURm",db="1")

dic = {'game_count': '0', 'last_join_date': '', 'money': '0.0', 'headImgUrl': 'http://wx.qlogo.cn/mmopen/vi_32/DYAIOgq83eoWLicNiculNnLDgu3B73KpqJT7DNFVF9iaJvy4bZR8sRMJTgJNKUoxMUOicn8GNutUwKDaWu697YG5IQ/132', 'warhead_bonus': '0', 'sex': '2', 'currency': 'CNY', 'ticket_profit': '0', 'last_present_date': '', 'lastLoginDate': '2018-06-25 16:30:26', 'last_logout_ip': 'tcp4:113.111.81.143:60078', 'coin': '533300', 'lastLoginIp': '113.111.81.143', 'cannonSkin': '0', 'warhead': '1000000', 'parentAg': '', 'last_exit_ip': '', 'reg_date': '2018-01-31 13:14:06', 'charge': '0.0', 'valid': '1', 'last_login_date': '2018-06-25 16:12:29', 'vip_level': '0', 'email': '', 'roomCard': '5', 'openid': 'olAPX0Yj8Biujy_RHhtSKRzD_wy4', 'lastLoginClientType': '0', 'diamond': '0', 'last_exit_date': '', 'exchange_ticket': '0', 'charge_count': '0', 'phone': '', 'reg_ip': '220.176.233.96', 'playCount': '0', 'password': 'df911f0151f9ef021d410b4be5060972', 'nickname': 'ping303', 'name': 'BJQ8l1', 'account': 'ping303', 'refreshToken': '9_K9MwllxI6Cf4uxrU-mLsfXRgRr5YWEAKsyIY36UUD94Temg0_RiTXnAA3B5o7Rhwx16NiKazA04EOcsql_q_BPT4Sf0GxbDjxTqhSZxTHkM', 'last_join_ip': '', 'accessToken': '9_aqhq9Rn9tA6ZoGiQN5OMfiIcX7HTttOhCopTnMHxpcj934jS2mK-cXbLpbIyFNA76_0DrUY2hTUwKFTL3VjU47BmRtlxxFP-PqihGdtoo7k', 'level': '0', 'unionID': 'o9Zoi1APEYrmimWmV2sJOihuJ3Ak', 'newcomer_present_date': '', 'last_login_ip': 'tcp4:113.111.81.143:60078', 'last_logout_date': '2018-06-25 16:12:34', 'wallet': '0.0', 'lockCount': '99', 'exp': '0', 'coin_delta': '0'}

for i in range(1,301):
    dic['nickname'] = 'test' + str(i)
    dic['account'] = 'test' + str(i)
    dic['password'] = 'df911f0151f9ef021d410b4be5060972'
    dic['coin'] = random.randint(100000,1000000)
    redis.set('users:account:%s'%dic['account'],'users:%s'%i)
    redis.hmset('users:%s'%i,dic)
    #redis.sadd('fish:robot:set',i)
