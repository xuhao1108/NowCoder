#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2021/7/22 16:43
# @Author : 闫旭浩
# @Email : 874591940@qq.com
# @desc : 牛客网自动顶帖
import base64
import re
import random
import time
import json
import requests
from io import BytesIO
# from threading import Thread, Lock

# from selenium.webdriver.common.keys import Keys
from MyUtils import ChromeDriver, ReadExcel, WriteExcel

user_info_list = []
url_info_list = []
reply_info = {}
config = {}


# base_url = 'https://www.nowcoder.com'


class NowCoder(ChromeDriver):
    def __init__(self, user_info):
        """
        初始化
        :param index: 第n个标签页
        """
        # super(NowCoder, self).__init__(chrome_data_dir=user_info['chrome_data_dir'])
        super(NowCoder, self).__init__(max_window=False)
        self.user_info = user_info
        # 登录
        self.login()
        # 获取用户名
        user_img_btn = self.get_element('/html/body/div[1]/div[1]/div/ul[2]/li[5]/a')
        self.click_element_by_js(user_img_btn)
        self.user_info['user_link'] = self.chrome.current_url
        self.last_url = ''

    def login(self):
        """
        登录牛客网
        :return:
        """
        try:
            # # 判断是否登录
            # self.chrome.get('https://www.nowcoder.com/')
            # self.chrome.find_element_by_xpath('//*[@id="nav-login"]')
            # 打开登录页面
            self.chrome.get('https://www.nowcoder.com/login')
            time.sleep(1)
            # 已经登录了
            if self.chrome.current_url == 'https://www.nowcoder.com/index':
                return True
            # 点击密码登录
            password_login_btn = self.get_element('/html/body/div[1]/div[2]/div/div[2]/div[2]/div[1]/ul/li[3]')
            self.click_element_by_js(password_login_btn)
            # 输入账号
            self.send_keys_to_element(self.user_info['username'], '/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[1]/div/div/input')
            # 输入密码
            self.send_keys_to_element(self.user_info['password'], '/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[2]/div/div/input')
            while True:
                try:
                    # 点击登录
                    login_btn = self.get_element('/html/body/div[1]/div[2]/div/div[2]/div[2]/form/button')
                    self.click_element_by_js(login_btn)
                    time.sleep(1)
                    self.chrome.find_element_by_xpath('//div[@class="el-form-item__error"]')
                except:
                    break
            return True
        except:
            return False

    def search_url_rank(self, url_info):
        """
        查询帖子的排名
        :param url_info: 查询的信息
        :return:
        """
        # 不获取排名，直接回复
        return True

        search_url = 'https://www.nowcoder.com/search?type=post&query={}'.format(url_info['keyword'])
        self.chrome.get(search_url)
        retry_number = 0
        while True:
            if retry_number > 3:
                return False
            if '很抱歉，没有找到与你搜索相关的内容' in self.chrome.page_source \
                    or '操作太快，请稍后再试。Too Many Requests!' in self.chrome.page_source:
                # or '你使用的网络运营商限制，导致静态文件加载出错，如果想' in self.chrome.page_source:
                self.chrome.refresh()
                time.sleep(1)
                retry_number += 1
            else:
                try:
                    error_text = c.chrome.find_element_by_xpath('/html/body/div/div').text
                    if '因你使用的网络运营商限制，导致静态文件加载出错，如果想要彻底解决问题，请联系你使用的网络运营商（如运营商不处理可以前往工信部投诉），也可以按照以下步骤修改电脑的DNS' in error_text:
                        self.chrome.refresh()
                        time.sleep(1)
                        retry_number += 1
                except:
                    break
        current_rank = 0
        # 依次获取帖子链接和排名
        last_page_url = ''
        retry_page_num = 0
        while self.chrome.current_url != last_page_url:
            if retry_page_num > 3:
                return True
            retry_page_num += 1
            last_page_url = self.chrome.current_url
            retry_num = 0
            # 获取页面链接列表
            while True:
                if retry_num > 3:
                    return True
                if retry_page_num > 3:
                    return True
                time.sleep(3)
                try:
                    a_btn_list = self.chrome.find_elements_by_xpath('/html/body/div[1]/div[2]/div[1]/div[3]/div[1]/ul/li/div/div[1]/a[1]')
                    a_list = [x.get_attribute('href') for x in a_btn_list]
                    if len(a_list) > 0:
                        break
                    else:
                        retry_page_num += 1
                except:
                    self.chrome.refresh()
                    retry_num += 1
            # 寻找目标链接
            for href in a_list:
                # 指定排名内，找不到
                if current_rank > url_info['rank']:
                    print('链接：{}，不在排名内。'.format(url_info['url']))
                    return True
                # 指定排名内，找到
                try:
                    # 删除?以及后面的参数部分
                    href = href.split('?')[0]
                    search_url = url_info['url'].split('?')[0]
                    if search_url.endswith(href):
                        print('链接：{}，在排名内。'.format(url_info['url']))
                        return False
                except:
                    pass
                current_rank += 1
            try:
                # 下一页
                next_page = self.get_element_attribute('/html/body/div[1]/div[2]/div[1]/div[3]/div[2]/ul/li[last()-1]/a', 'href')
                # self.click_element_by_js(next_page)
                # print('下一页帖子:{}'.format(next_page))
                # 末页
                if 'javascript:void(0)' in next_page:
                    return True
                self.chrome.get(next_page)
            except:
                return True

    def reply_post(self, url):
        """
        回复帖子
        :return:
        """
        self.last_url = ''
        global reply_info
        try:
            url = url.split('?')[0]
        except:
            url = url
        # 获取上一次发帖的信息
        if self.user_info['username'] not in reply_info:
            reply_info[self.user_info['username']] = {}
        last_reply_time = reply_info.get(self.user_info['username']).get(url, 0)
        # 在指定时间内已经回复过该帖子了，则跳过
        if time.time() - last_reply_time <= config['reply_time']:
            print('当前时间段内已经评论过，跳过该链接:{}'.format(url))
            return False
        # 打开帖子页面
        self.chrome.get(url)
        time.sleep(1)
        if '很抱歉，这篇文章因违反' in self.chrome.page_source:
            # 从列表中删除此帖子
            global url_info_list
            for url_info in url_info_list:
                if url == url_info['url']:
                    url_info['status'] = 'error'
                    break
            print('帖子被删除了！！！')
            return False
        delete_falg = self.delete_all_reply(url)
        if not delete_falg:
            return False
        # 判断有无“举报”的弹窗出现
        # self.close_error_alert()
        reply_message = get_reply_message()
        # print('回复内容：{}'.format(reply_message))
        try:
            # 回复帖子
            self.send_keys_to_element(reply_message, '/html/body/div[1]/div[2]/div[2]/div[6]/div/textarea')
        except:
            return self.reply_post(url)
        # 点击回帖
        try:
            post_btn = self.get_element('/html/body/div[1]/div[2]/div[2]/div[6]/div/div[3]/button')
            time.sleep(1)
            retry_num = 0
            while retry_num < 5:
                retry_num += 1
                try:
                    self.click_element_by_js(post_btn)
                    break
                except:
                    pass
        except:
            pass
        time.sleep(5)
        # 如果出现滑块，则处理
        self.slider()
        # 更新记录
        reply_info[self.user_info['username']][url] = int(time.time())
        print('{}回复内容：{}。'.format(self.user_info['username'], reply_message))
        # 写入本次运行的回复结果
        wirte_reply_data()
        return True

    def get_reply_number(self):
        try:
            if self.get_element_text('//div[@class="module-box js-comment-list"]//h1') == '0条回帖':
                return 0
        except:
            pass
        # 获取用户回复列表
        try:
            a_list = self.chrome.find_elements_by_xpath('//div[@class="answer-list-item clearfix js-copy-mark js-scroll-comments"]//div[@class="answer-detail"]/p/a')
            if not a_list:
                return -1
            a_list = self.get_elements_attribute('//div[@class="answer-list-item clearfix js-copy-mark js-scroll-comments"]//div[@class="answer-detail"]/p/a', 'href')
            # 删除特殊的广告数据
            while True:
                if 'https://www.nowcoder.com/user/authentication' in a_list:
                    a_list.remove('https://www.nowcoder.com/user/authentication')
                else:
                    break
            return a_list
        except:
            return -1

    def delete_all_reply(self, url):
        """
        删除上次回复的帖子
        :return:
        """
        # 循环删除回复，直到删除完毕
        retry_number = 0
        delete_retry_number = 0
        # 最多翻页20次
        while retry_number <= 20:
            retry_number += 1
            index = 0
            while index < 20:
                if delete_retry_number > 5:
                    return False
                result = self.get_reply_number()
                # 0回复
                if result == 0:
                    return True
                # 页面异常
                elif result == -1:
                    delete_retry_number += 1
                    self.chrome.get(url)
                    time.sleep(3)
                # 有回复
                else:
                    # 当前页面没有可删除的评论，则退出
                    if not self.delete_one_reply(result):
                        # print('删除完毕')
                        break
                    index += 1
                    time.sleep(2)
            # 获取末页
            # if self.last_url == '' or 'page=' not in self.last_url:
            try:
                self.last_url = self.chrome.find_element_by_xpath('//div[@class="pagination"]/ul/li[last()]/a').get_attribute('href')
            except:
                self.last_url = self.chrome.current_url
            # print(self.chrome.current_url, self.last_url)
            # 到末页了
            if self.chrome.current_url == self.last_url or self.last_url == 'javascript:void(0);':
                # print('到末页了')
                return True
            # 下一页
            if self.chrome.current_url != self.last_url:
                try:
                    # 下一页
                    next_btn = self.chrome.find_element_by_xpath('//div[@class="pagination"]/ul/li[last()-1]/a')
                    if next_btn.get_attribute('href') == 'javascript:void(0);':
                        return True
                    self.move_to_element_by_action(next_btn)
                    self.click_element_by_action(next_btn)
                    time.sleep(4)
                    # print('下一页')
                except:
                    # except Exception as e:
                    #     print('下一页失败:{}'.format(e))
                    #     input('ok?')
                    return True

    def delete_one_reply(self, a_list):
        # self.close_error_alert()
        # 获取要删除的下标
        if self.user_info['user_link'] not in a_list:
            return False
        index = a_list.index(self.user_info['user_link'])
        # print(a_list, len(a_list), self.user_info['user_link'], index)
        # 滑动到底部
        try:
            # 删除元素列表
            delete_btn_list = self.get_elements('//div[@class="answer-list-item clearfix js-copy-mark js-scroll-comments"]')
            self.scroll_to_element_by_js(delete_btn_list[-1])
            # 点击删除
            delete_btn = delete_btn_list[index].find_elements_by_xpath('.//a')[-1]
            self.click_element_by_js(delete_btn)
            try:
                # 点击错误，此时出现“举报”按钮
                pop_title = self.chrome.find_element_by_xpath('//div[@class="pop-title"]/h1').text
                if '举报' in pop_title:
                    # input('????:')
                    self.chrome.refresh()
                    time.sleep(3)
                    return True
            except:
                pass
            time.sleep(1)
            # 点击确认
            sure_btn = self.get_element('//a[@class="btn btn-primary confirm-btn"]')
            self.click_element_by_js(sure_btn)
            print('删除成功')
            time.sleep(1)
            return True
        # except:
        except Exception as e:
            # print('删除出错了:{}'.format(e))
            # input('ok?:')
            return False

    def close_error_alert(self):
        try:
            # 点击关闭按钮
            close_btn = self.chrome.find_element_by_xpath('//a[@class="pop-close"]')
            self.click_element_by_js(close_btn)
        except:
            pass
        try:
            # 点击关闭按钮
            close_btn = self.chrome.find_element_by_xpath('//a[@class="pop-close"]')
            self.click_element_by_js(close_btn)
        except:
            pass

    def slider(self):
        """
        处理滑块
        :return:
        """
        retry_num = 0
        while retry_num <= 3:
            retry_num += 1
            try:
                # 获取滑块
                slider_btn = self.chrome.find_element_by_xpath('//div[@class="yidun_slider"]')
                # 获取验证码图片
                image_url = self.chrome.find_element_by_xpath('//img[@class="yidun_bg-img"]').get_attribute('src')
                # print('出现滑块了：{}'.format(image_url))
                # time.sleep(1)
                # 获取缺口位置 总长度260，滑块大小40
                # distance = get_slide_x(image_url) - 40
                distance = int(get_slide_x(image_url) / 320 * 260 / 2)
                action = self.get_action()
                # 移动滑块
                action.click_and_hold(slider_btn).perform()
                action.move_by_offset(xoffset=distance, yoffset=0).perform()
                time.sleep(0.5)
                action.release(slider_btn).perform()
                #
                time.sleep(3)
            except:
                pass

    def run(self, url_info):
        try:
            # 不在排名内
            if self.search_url_rank(url_info):
                # 回复
                self.reply_post(url_info['url'])
                # reply_status = self.reply_post(url_info['url'])
                # 回复成功后，再次获取排名
                # 若不在指定范围内，则需要删除刚才的回复
                # if self.search_url_rank(url_info):
                #     # print('链接：{}，不在排名内。删除刚才的回复'.format(url_info['url']))
                #     self.chrome.get(url_info['url'])
                #     # 需要删除刚才的回复
                #     self.delete_all_reply()
            else:
                # 在排名内
                return True
        except:
            pass


def get_excel_data():
    global user_info_list, url_info_list, config
    excel = ReadExcel('./config.xlsx')
    excedl_data = excel.read_all_data()
    # 默认关键词和排名
    default_keyword = None
    default_rank = None
    for data in excedl_data:
        # 设置默认值
        default_keyword = default_keyword if default_keyword else data.get('关键词')
        default_rank = default_rank if default_rank else data.get('排名')
        # 获取用户名信息
        if data.get('用户名') and data.get('密码'):
            user_info_list.append({
                'username': str(data.get('用户名')).replace('.0', ''),
                'password': data.get('密码'),
                # 'chrome_data_dir': data.get('浏览器路径'),
            })
        # 获取帖子信息
        if data.get('链接'):
            url_info_list.append({
                'url': data.get('链接'),
                'keyword': default_keyword if data.get('关键词', '') == '' else data.get('关键词'),
                'rank': int(default_rank if data.get('排名', '') == '' else data.get('排名')),
                'status': 'success'
            })
    excel = ReadExcel('./config.xlsx', sheet_index=1)
    excedl_data = excel.read_row(1)
    config = {
        # 单位：分钟
        'search_time': float(excedl_data[0]) * 60,
        'reply_time': float(excedl_data[1]) * 60,
        'user_time': float(excedl_data[2]) * 60,
        'name_path': excedl_data[3],
        'job_path': excedl_data[4],
        'username': excedl_data[5],
        'password': excedl_data[6],
    }
    try:
        config['stop_begin_time'] = int(excedl_data[7])
    except:
        config['stop_begin_time'] = 0
    try:
        config['stop_end_time'] = int(excedl_data[8])
    except:
        config['stop_end_time'] = 8


def read_reply_data():
    """
    获取各用户的回复信息
    :return:
    """
    global reply_info
    excel = ReadExcel('./config.xlsx', sheet_index=2)
    row_number = excel.get_row_number()
    excedl_data = excel.read_all_data()
    for data in excedl_data:
        username = data.get('用户名', '')
        url = data.get('链接', '').split('?')[0]
        reply_time = int(data.get('回复时间'))
        if username not in reply_info:
            reply_info[username] = {}
        reply_info[username][url] = reply_time
    excel = WriteExcel('./config.xlsx', sheet_index=2)
    excel.sheet.delete_rows(2, row_number)
    excel.save_to_excel()


def wirte_reply_data():
    """
    将各用户的回复信息写入excel
    :return:
    """
    excel = WriteExcel('./config.xlsx', sheet_index=2)
    row = 1
    for username in reply_info:
        for url in reply_info[username]:
            excel.write_row([username, url, reply_info[username][url]], row)
            row += 1


def get_reply_message():
    """
    获取回复话术
    :return:
    """
    first_name, job_name = '', ''
    with open(config['name_path'], 'r') as f:
        first_name_list = f.read().split('\n')
    with open(config['job_path'], 'r') as f:
        job_name_list = f.read().split('\n')
    while first_name == '':
        first_name = random.choice(first_name_list)
    last_name = random.choice('abcdefghijklmnopqrstuvwxyz')
    last_name += random.choice('abcdefghijklmnopqrstuvwxyz')
    while job_name == '':
        job_name = random.choice(job_name_list)
    message = '感谢内推，{}{}+{}'.format(first_name, last_name, job_name)
    return message


def get_slide_x(image_url):
    """
    获取滑块验证码缺口位置
    :param image_url:
    :return:
    """
    try:
        response = requests.get(image_url)
        base64_data = base64.b64encode(BytesIO(response.content).read())
        b64 = base64_data.decode()
        data = {'username': config['username'], 'password': config['password'], 'typeid': 33, "image": b64, 'softid': 'cce56384732d4aada9121d9cb1bb9dee'}
        # data = {'username': config['username'], 'password': config['password'], 'typeid': 33, "image": b64}
        result = json.loads(requests.post('http://api.ttshitu.com/predict', json=data).text)
        if result['success']:
            return int(result['data']['result'])
        else:
            return 0
    except:
        return 0


def start_now_coder():
    """
    定时启动
    :return:
    """
    # 创建所有浏览器对象
    now_coder_list = []
    for user_info in user_info_list:
        try:
            now_coder = NowCoder(user_info)
            now_coder_list.append(now_coder)
        except:
            pass
    # 依次搜索每个帖子，然后用每个账号进行回复
    last_user = None
    while True:
        # 2~6点不运行
        if config['stop_begin_time'] < time.localtime().tm_hour < config['stop_end_time']:
            print('休息....')
            return True
        # 搜索每个帖子
        for url_index, url_info in enumerate(url_info_list):
            print('正在搜索第{}个帖子:{}'.format(url_index + 1, url_info['url']))
            if url_info['status'] != 'success':
                continue
            # 随机获取一个账号进行回复
            if len(now_coder_list) > 1:
                current_user = last_user
                while current_user == last_user:
                    current_user = random.choice(now_coder_list)
                last_user = current_user
            else:
                current_user = now_coder_list[0]
            print('正在使用账号{}:{}进行回复...'.format(now_coder_list.index(current_user) + 1, current_user.user_info['username']))
            current_user.run(url_info)
            # 等待若干秒
            time.sleep(config['user_time'])
            ##########################################################################
            # print('正在搜索第{}个帖子:{}'.format(url_index + 1, url_info['url']))
            # 用每个账号 进行搜索和回复
            # for user_index, now_coder in enumerate(now_coder_list):
            #     if url_info['status'] != 'success':
            #         continue
            #     try:
            #         # 若在排名内，则直接进行下一个帖子
            #         if now_coder.run(url_info):
            #             break
            #     except:
            #         pass
            #     # 等待若干秒，切换账号
            #     if user_index < len(now_coder_list) - 1:
            #         print('等待切换账号{}中...'.format(user_index + 2))
            #     else:
            #         print('等待切换账号1中...')
            #     time.sleep(config['user_time'])
        # 等待若干秒继续搜索
        # print('等待继续搜索中...')
        time.sleep(config['search_time'])
        ##########################################################################


def my_t():
    while True:
        # 2~6点不运行
        if config['stop_begin_time'] < time.localtime().tm_hour < config['stop_end_time']:
            print('休息......')
            return True
        print(time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_sec)
        time.sleep(30)


def run():
    # 获取配置参数
    get_excel_data()
    # 获取回复信息
    read_reply_data()
    while True:
        if config['stop_begin_time'] < time.localtime().tm_hour < config['stop_end_time']:
            print('等待......')
            time.sleep(60)
        else:
            # my_t()
            start_now_coder()


if __name__ == '__main__':
    run()
