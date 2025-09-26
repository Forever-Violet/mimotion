# -*- coding: utf8 -*-
import datetime
import json
import math
import random
import re
import sys
import time
import requests
import pytz
from random import choice

# 开启根据地区天气情况降低步数（默认关闭）
open_get_weather = sys.argv[3]
# 设置获取天气的地区（上面开启后必填）如：area = "宁波"
area = sys.argv[4]

# 用户代理池
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.93 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.92 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Pixel 4 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.89 Mobile Safari/537.36",
]

def get_random_user_agent():
    return choice(USER_AGENTS)

def get_request_headers():
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

headers = get_request_headers()

# 系数K查询到天气后降低步数比率
K_dict = {"多云": 0.9, "阴": 0.8, "小雨": 0.7, "中雨": 0.5, "大雨": 0.4, "暴雨": 0.3, "大暴雨": 0.2, "特大暴雨": 0.2}

# 北京时间
time_bj = datetime.datetime.today() + datetime.timedelta(hours=8)
now = time_bj.strftime("%Y-%m-%d %H:%M:%S")

# 获取区域天气情况
def getWeather():
    if area == "NO":
        print("天气功能未启用")
        return
    else:
        global K, type
        url = 'http://wthrcdn.etouch.cn/weather_mini?city=' + area
        hea = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url=url, headers=hea, timeout=10)
            if r.status_code == 200:
                result = r.text
                res = json.loads(result)
                weather_type = res['data']['forecast'][0]['type']
                
                # 根据天气类型设置系数K
                for key in K_dict:
                    if key in weather_type:
                        K = K_dict[key]
                        type = key
                        print(f"检测到天气: {type}, 设置系数K为: {K}")
                        return
                
                # 如果没有匹配的天气类型，使用默认值
                K = 1.0
                type = "未知"
                print(f"未匹配到天气类型: {weather_type}, 使用默认系数K=1.0")
            else:
                print(f"获取天气失败，状态码: {r.status_code}")
                K = 1.0
                type = "获取失败"
        except Exception as e:
            print(f"获取天气异常: {str(e)}")
            K = 1.0
            type = "异常"

# 获取北京时间确定随机步数&启动主函数
def getBeijinTime():
    global K, type
    K = 1.0
    type = ""
    
    if open_get_weather == "True":
        getWeather()
    
    # 直接使用本地时间计算
    hour = time_bj.hour
    min_ratio = max(math.ceil((hour / 3) - 1), 0)
    max_ratio = math.ceil(hour / 3)
    min_1 = 3500 * min_ratio
    max_1 = 3500 * max_ratio
    min_1 = int(K * min_1)
    max_1 = int(K * max_1)
    
    print(f"计算步数范围: {min_1}~{max_1} (K={K})")
    
    if min_1 != 0 and max_1 != 0:
        user_mi = sys.argv[1]
        passwd_mi = sys.argv[2]
        user_list = user_mi.split('#')
        passwd_list = passwd_mi.split('#')
        
        if len(user_list) != len(passwd_list):
            print("用户名和密码数量不匹配")
            return
            
        if K != 1.0:
            msg_mi = f"由于天气{type}，已设置降低步数,系数为{K}。\n"
        else:
            msg_mi = ""
            
        for user_mi, passwd_mi in zip(user_list, passwd_list):
            result = main(user_mi, passwd_mi, min_1, max_1)
            if result:
                msg_mi += result
            else:
                msg_mi += f"账号 {user_mi} 处理失败\n"
                
        print(msg_mi)
    else:
        print("当前设置了0步数，本次不提交")

# 获取登录code
def get_code(location):
    code_pattern = re.compile("(?<=access=).*?(?=&)")
    code = code_pattern.findall(location)[0]
    return code

# 登录
def login(user, password):
    is_phone = False
    if re.match(r'\d{11}', user):
        is_phone = True
        
    if is_phone:
        url1 = "https://api-user.huami.com/registrations/+86" + user + "/tokens"
    else:
        url1 = "https://api-user.huami.com/registrations/" + user + "/tokens"
        
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": get_random_user_agent()
    }
    
    data1 = {
        "client_id": "HuaMi",
        "password": f"{password}",
        "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
        "token": "access"
    }
    
    try:
        r1 = requests.post(url1, data=data1, headers=headers, allow_redirects=False, timeout=10)
        
        # 检查是否有Location头
        if 'Location' not in r1.headers:
            print(f"登录失败: 响应头中缺少Location字段")
            print(f"状态码: {r1.status_code}")
            print(f"响应内容: {r1.text[:200]}...")
            return 0, 0
            
        location = r1.headers["Location"]
        code = get_code(location)
        
        url2 = "https://account.huami.com/v2/client/login"
        if is_phone:
            data2 = {
                "app_name": "com.xiaomi.hm.health",
                "app_version": "4.6.0",
                "code": f"{code}",
                "country_code": "CN",
                "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
                "device_model": "phone",
                "grant_type": "access_token",
                "third_name": "huami_phone",
            }
        else:
            data2 = {
                "allow_registration": "false",
                "app_name": "com.xiaomi.hm.health",
                "app_version": "6.3.5",
                "code": f"{code}",
                "country_code": "CN",
                "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
                "device_model": "phone",
                "dn": "api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com",
                "grant_type": "access_token",
                "lang": "zh_CN",
                "os_version": "1.5.0",
                "source": "com.xiaomi.hm.health",
                "third_name": "email",
            }
            
        r2 = requests.post(url2, data=data2, headers=headers, timeout=10).json()
        login_token = r2["token_info"]["login_token"]
        userid = r2["token_info"]["user_id"]
        
        return login_token, userid
        
    except Exception as e:
        print(f"登录过程中发生异常: {str(e)}")
        return 0, 0

# 主函数
def main(_user, _passwd, min_1, max_1):
    user = str(_user)
    password = str(_passwd)
    step = str(random.randint(min_1, max_1))
    print(f"账号: {user[:3]}****{user[7:]} 设置随机步数({min_1}~{max_1}): {step}")
    
    if not user or not password:
        print("用户名或密码为空")
        return None
        
    login_token, userid = login(user, password)
    if login_token == 0:
        print("登陆失败")
        return None
        
    t = get_time()
    app_token = get_app_token(login_token)
    
    if not app_token:
        print("获取app_token失败")
        return None
        
    today = time.strftime("%Y-%m-%d")
    
    # 这里简化了数据构造，实际使用时需要根据API要求构造完整数据
    data = {
        "userid": userid,
        "last_sync_data_time": int(time.time()),
        "device_type": 0,
        "last_deviceid": "DA932FFFFE8816E7",
        "data_json": json.dumps({
            "date": today,
            "summary": {
                "stp": {
                    "ttl": int(step)
                }
            }
        })
    }
    
    url = f'https://api-mifit-cn.huami.com/v1/data/band_data.json?&t={t}'
    head = {
        "apptoken": app_token,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": get_random_user_agent()
    }
    
    try:
        response = requests.post(url, data=data, headers=head, timeout=10)
        if response.status_code == 200:
            result = response.json()
            message = result.get('message', '未知响应')
            return f"[{now}]\n账号：{user[:3]}****{user[7:]}\n修改步数（{step}）[{message}]\n"
        else:
            print(f"提交步数失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
            return None
    except Exception as e:
        print(f"提交步数时发生异常: {str(e)}")
        return None

# 获取时间戳
def get_time():
    # 使用本地时间生成时间戳
    return int(time.time() * 1000)

# 获取app_token
def get_app_token(login_token):
    if not login_token:
        return None
        
    url = f"https://account-cn.huami.com/v1/client/app_tokens?app_name=com.xiaomi.hm.health&dn=api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com&login_token={login_token}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['token_info']['app_token']
        else:
            print(f"获取app_token失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"获取app_token时发生异常: {str(e)}")
        return None

if __name__ == "__main__":
    getBeijinTime()
