from flask import Blueprint, render_template, session, jsonify, request, redirect
from bs4 import BeautifulSoup
import requests
import time
import re
import json

vx_demo = Blueprint('vx_demo', __name__)


# 将XML转化为字典
def xml(text):
    data = {}
    obj = BeautifulSoup(text, 'html.parser')
    tag_list = obj.find(name='error').find_all()
    for tag in tag_list:
        data[tag.name] = tag.text
    print(data)
    return data


@vx_demo.route('/login')
def login():
    # 利用web微信接口获取动态验证码
    ctime = int(time.time() * 1000)
    url = 'https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_={0}'.format(
        ctime)
    response = requests.get(url=url)
    dynamic_code = re.findall('uuid = "(.*)";', response.text)[0]
    session['dynamic_code'] = dynamic_code
    return render_template("vx_home.html", **{"dynamic_code": dynamic_code})


# 用于多轮询验证是否扫码
@vx_demo.route('/head_code')
def head_code():
    ctime = int(time.time() * 1000)
    dynamic_code = session.get('dynamic_code')
    url = 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip=0&r=1754220961&_={1}'.format(
        dynamic_code, ctime)
    response = requests.get(url=url)
    data = {}
    if 'window.code=408' in response.text:
        data['code'] = 408  # 未扫描登录
    elif 'window.code=201' in response.text:
        data['code'] = 201  # 第一次扫码 获取头像
        img = re.findall("window.userAvatar = '(.*)';", response.text)[0]
        data['img'] = img
    elif 'window.code=200' in response.text:
        data['code'] = 200  # 扫码后确认登录
        redirect_url = re.findall('window.redirect_uri="(.*)";', response.text)[0] + '&fun=new&version=v2'
        # 请求该url 获取凭证
        voucher = requests.get(redirect_url)
        cookies = voucher.cookies.get_dict()
        session['cookies'] = cookies
        voucher_list = xml(voucher.text)  # 获取凭证字典
        data['redirect_url'] = redirect_url
        session['voucher_list'] = voucher_list  # 将凭证信息存储至session中
    return jsonify(data)


# 用户信息初始化
@vx_demo.route('/home')
def home():
    voucher_list = session.get('voucher_list')
    mes_init_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?lang=zh_CN&r=1703906020&pass_ticket={0}".format(
        voucher_list['pass_ticket'])
    post_json = {
        'BaseRequest': {'Uin': voucher_list['wxuin'], 'Sid': voucher_list['wxsid'], 'DeviceID': "e616236045909270",
                        'Skey': voucher_list['skey']}}
    init_wx = requests.post(url=mes_init_url, json=post_json)
    init_wx.encoding = 'utf-8'
    json_data = init_wx.json()
    return render_template('home.html', **{'json_data': json_data})


# 获取所有好友列表
@vx_demo.route('/all_friend')
def all_friend():
    ctime = int(time.time() * 1000)
    voucher_list = session.get('voucher_list')
    cookies = session.get('cookies')
    all_friend_url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={0}&r={1}&seq=0&skey={2}'.format(
        voucher_list['pass_ticket'], ctime, voucher_list['skey'])

    frinds = requests.get(url=all_friend_url, cookies=cookies)
    frinds.encoding = 'utf-8'
    json_data = frinds.json()
    return render_template('friend_all.html', **{'json_data': json_data})


# 发送指定消息
@vx_demo.route('/send')
def send():
    ctime = int(time.time() * 1000)
    FromUserName = request.args.get('FromUserName')
    ToUserName = request.args.get('ToUserName')
    voucher_list = session.get('voucher_list')
    Content = '联系测试'
    send_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket={0}".format(
        voucher_list['pass_ticket'])
    post_json = {
        'BaseRequest': {'Uin': voucher_list['wxuin'], 'Sid': voucher_list['wxsid'], 'DeviceID': "e616236045909270",
                        'Skey': voucher_list['skey']},
        'Msg': {'ClientMsgId': ctime, 'Content': Content, 'LocalID': ctime, 'FromUserName': FromUserName,
                'ToUserName': ToUserName, 'Type': 1},
        'Scene': 0
    }
    response = requests.post(url=send_url, data=bytes(json.dumps(post_json, ensure_ascii=False),encoding='utf-8'))
    return redirect('/home')
