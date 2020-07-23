from .QQEventHandler import QQEventHandler
from .QQUtils import *
from ffxivbot.models import *
import logging
import json
import random
import dice
import feedparser
import traceback
import requests
import time
import re
from bs4 import BeautifulSoup


def localize_world_name(world_name):
    world_dict = {
        "HongYuHai": "红玉海",
        "ShenYiZhiDi": "神意之地",
        "LaNuoXiYa": "拉诺西亚",
        "HuanYingQunDao": "幻影群岛",
        "MengYaChi": "萌芽池",
        "YuZhouHeYin": "宇宙和音",
        "WoXianXiRan": "沃仙曦染",
        "ChenXiWangZuo": "晨曦王座",
        "BaiYinXiang": "白银乡",
        "BaiJinHuanXiang": "白金幻象",
        "ShenQuanHen": "神拳痕",
        "ChaoFengTing": "潮风亭",
        "LvRenZhanQiao": "旅人栈桥",
        "FuXiaoZhiJian": "拂晓之间",
        "Longchaoshendian": "龙巢神殿",
        "MengYuBaoJing": "梦羽宝境",
        "ZiShuiZhanQiao": "紫水栈桥",
        "YanXia": "延夏",
        "JingYuZhuangYuan": "静语庄园",
        "MoDuNa": "摩杜纳",
        "HaiMaoChaWu": "海猫茶屋",
        "RouFengHaiWan": "柔风海湾",
        "HuPoYuan": "琥珀原",
    }
    for (k, v) in world_dict.items():
        pattern = re.compile(k, re.IGNORECASE)
        world_name = pattern.sub(v, world_name)
    return world_name


def get_item_id(item_name):
    url = "https://cafemaker.wakingsands.com/search?indexes=Item&string=" + item_name
    r = requests.get(url, timeout=3)
    j = r.json()
    if len(j["Results"]) > 0:
        return j["Results"][0]["Name"], j["Results"][0]["ID"]
    return "", -1


def get_intl_item_id(item_name):
    url = "https://xivapi.com/search?indexes=Item&string=" + item_name
    r = requests.get(url, timeout=3)
    j = r.json()
    if len(j["Results"]) > 0:
        return j["Results"][0]["Name"], j["Results"][0]["ID"]
    return "", -1


def get_market_data(server_name, item_name, hq=False):
    new_item_name, item_id = get_item_id(item_name)
    if item_id < 0:
        item_name = item_name.replace("_", " ")
        new_item_name, item_id = get_intl_item_id(item_name)
        if item_id < 0:
            msg = '所查询物品"{}"不存在'.format(item_name)
            return msg
    url = "https://universalis.app/api/{}/{}".format(server_name, item_id)
    print("market url:{}".format(url))
    r = requests.get(url, timeout=3)
    j = r.json()
    msg = "{} 的 {}{} 数据如下：\n".format(server_name, new_item_name, "(HQ)" if hq else "")
    listing_cnt = 0
    for listing in j["listings"]:
        if hq and not listing["hq"]:
            continue
        retainer_name = listing["retainerName"]
        if "dcName" in j:
            retainer_name += "({})".format(localize_world_name(listing["worldName"]))
        msg += "{:,}x{} = {:,} {} {}\n".format(
            listing["pricePerUnit"],
            listing["quantity"],
            listing["total"],
            "HQ" if listing["hq"] else "  ",
            retainer_name,
        )
        listing_cnt += 1
        if listing_cnt >= 10:
            break
    TIMEFORMAT_YMDHMS = "%Y-%m-%d %H:%M:%S"
    last_upload_time = time.strftime(
        TIMEFORMAT_YMDHMS, time.localtime(j["lastUploadTime"] / 1000)
    )
    msg += "更新时间:{}".format(last_upload_time)
    if listing_cnt == 0:
        msg = "未查询到数据，请使用/market upload命令查看如何上报数据"
    return msg


def handle_command(command_seg, user, group):
    help_msg = """/market item $name $server: 查询$server服务器的$name物品交易数据
/market upload: 如何上报数据
Powered by https://universalis.app"""
    msg = help_msg
    if len(command_seg) == 0 or command_seg[0].lower() == "help":
        return msg
    elif command_seg[0].lower() == "item":
        # if time.time() < user.last_api_time + user.api_interval:
        if time.time() < user.last_api_time + 15:
            msg = "[CQ:at,qq={}] 技能冷却中，请勿频繁调用".format(user.user_id)
            return msg
        server = None
        if len(command_seg) != 3:
            msg = "参数错误：\n/market item $name $server: 查询$server服务器的$name物品交易数据"
            return msg
        server_name = command_seg[2]
        if server_name == "陆行鸟" or server_name == "莫古力" or server_name == "猫小胖":
            pass
        elif server_name == "鸟":
            server_name = "陆行鸟"
        elif server_name == "猪":
            server_name = "莫古力"
        elif server_name == "猫":
            server_name = "猫小胖"
        else:
            pass
            # server = Server.objects.filter(name=server_name)
            # if not server.exists():
            #     msg = '找不到服务器"{}"'.format(server_name)
            #     return msg
        item_name = command_seg[1]
        hq = "hq" in item_name or "HQ" in item_name
        if hq:
            item_name = item_name.replace("hq", "", 1)
            item_name = item_name.replace("HQ", "", 1)
        msg = get_market_data(server_name, item_name, hq)
        user.last_api_time = time.time()
        user.save(update_fields=["last_api_time"])
        return msg
    elif command_seg[0].lower() == "upload":
        msg = """您可以使用以下几种方式上传交易数据：
1.如果您使用过国际服的 XIVLauncher，您可以使用国服支持的Dalamud版本 https://url.cn/6L7nD0gF
2.如果您使用过ACT，您可以加载ACT插件 UniversalisPlugin
3.如果您想不依赖于其他程序，您可以使用 UniversalisStandalone
4.如果您使用过Teamcraft客户端，您也可以使用其进行上传
其中 2. 3. 两点所需软件请于 https://url.cn/TEY1QKKV 下载 UniversalisApp.zip
Powered by https://universalis.app"""
    return msg


def QQCommand_market(*args, **kwargs):
    try:
        QQ_BASE_URL = kwargs["global_config"]["QQ_BASE_URL"]
        action_list = []
        receive = kwargs["receive"]
        bot = kwargs["bot"]
        user = QQUser.objects.get(user_id=receive["user_id"])
        group = kwargs.get("group")
        msg = ""
        command_msg = receive["message"].replace("/market", "", 1).strip()
        command_seg = command_msg.split(" ")
        while "" in command_seg:
            command_seg.remove("")
        msg = handle_command(command_seg, user, group)
        msg = msg.strip()

        reply_action = reply_message_action(receive, msg)
        action_list.append(reply_action)
        return action_list
    except Exception as e:
        msg = "Error: {}".format(type(e))
        action_list.append(reply_message_action(receive, msg))
        logging.error(e)
        traceback.print_exc()
    return action_list
