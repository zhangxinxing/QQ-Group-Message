#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
这个模块，主要根据网页版的qq，模拟其相应的url请求（get/post），
获得服务器返回的结果

功能： 获取账号群消息 

基本流程： 登陆（获取权限） ---》 更新群目录（有条件的）---》 跟新群成员列表及信息（有条件的）
                         ---》 消息轮询与处理  ---》 错误退出（正常的轮询周期在24-48h之间）

缺点： 受制于webqq，相关信息获取过程，容易出错

      发送的相关加密数据，计算方法会常常更新

      不能长时间的qq在线，24-48h便会被迫下线

      webqq不支持接收离线的消息，文件，图片，和自己在其他客户端发送的消息

      因为获取的群信息（初始时），获取不到真实的群id，所以以群的名称作为 唯一标识 （在创建相关文件目录时用到）?重复

      webqq 不接收离线消息 不接收自己在别的客户端发送的消息

作者：zhang

日期：2015年8月 
      
       
'''

import re
import random
import json
import os
import sys
import datetime
import time
import threading
import logging
import getHash
from HttpClient import HttpClient

stdout = sys.stdout
stderr = sys.stderr

reload(sys)
sys.setdefaultencoding("utf-8")

sys.stderr = stderr
sys.stdout = stdout

HttpClient_Ist = HttpClient()



Referer = 'http://d.web2.qq.com/proxy.html?v=20130916001&callback=1&id=2'
SmartQQUrl = 'http://w.qq.com/login.html'
RefererGroupList = 'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1'
RefererFind = 'http://find.qq.com/index.html?version=1&im_version=5385&width=910&height=610&search_target=0'
initTime = time.time()


UpdateGroupInfo = False
UpdateMemInfo = False

#总的log文件，用来记录总程序的运行过程
#
logging.basicConfig(filename='log.log', level=logging.DEBUG, format='%(asctime)s  %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')

# -----------------
# 方法声明
# -----------------




def pass_time():
    """
        计算 时间间隔
    """
    global initTime
    rs = (time.time() - initTime)
    initTime = time.time()
    return str(round(rs, 3))


def getReValue(html, rex, er, ex):
    """
        在返回的页面中（html code） 查找相应的数据(模式)
    """
    v = re.search(rex, html)

    if v is None:
        logging.error(er)

        if ex:
            raise Exception, er
        return ''

    return v.group(1)


def date_to_millis(d):
    """
        将日期转换为 毫秒
    """
    return int(time.mktime(d.timetuple())) * 1000


def loginSucess():
    """
     登陆成功，则改变相应的状态字段 待用
    """
    pass


def stopError(info):
    """
       当程序出现致命错误时，改变相应的状态字段 并退出
    """
    logging.critical("程序发生致命错误，调用stopError()")
    logging.critical(info)
    logging.critical("异常退出！")
    sys.exit()

    
class UserGetMessage(HttpClient):
    """
       every user has a private getting message process

       this is the implementation of procedure mentioned above
    """
    def __init__(self):
        
        self.ClientID = int(random.uniform(111111, 888888))
        self.PTWebQQ = ''

        self.PSessionID = ''
       
        self.VFWebQQ = ''
        self.AdminQQ = '0'
        self.FriendList = {}
        
        self.GroupList = {}
        self.initUrl = ''
        self.VPath = './v.jpg' # QRCode保存路径

        self.qqnum = ''
        self.dirname = ''


    def uin_to_account(self,tuin):
    # 如果消息的发送者的真实QQ号码不在FriendList中,则自动去取得真实的QQ号码并保存到缓存中
    
        if tuin not in self.FriendList.keys():
            try:
                time.sleep(5)
                info = json.loads(self.Get('http://s.web2.qq.com/api/get_friend_uin2?tuin={0}&type=1&vfwebqq={1}'.format(tuin, self.VFWebQQ), Referer))
                #logging.info("Get uin to account info:" + str(info))
            
                if info['retcode'] == 0:
                    re = info['result']['account']
                    self.FriendList.setdefault(tuin,re)
                    return re 
                else:
                    return 0  #获取失败
            except Exception as e:
                logging.error(e)
                return 0
        else:
            return self.FriendList[tuin]

    
    def login(self):
        """
           登录函数
           登录失败，程序退出
        """
        
        #global APPID,  PTWebQQ, VFWebQQ, PSessionID
	#,msgId
        MaxTryTime = 5
        
        logging.critical("正在获取登陆页面")
        self.initUrl = getReValue(self.Get(SmartQQUrl), r'\.src = "(.+?)"', 'Get Login Url Error.', 1)
        logging.critical(self.initUrl)
        html = self.Get(self.initUrl + '0')
        #logging.critical(html)

        logging.critical("正在获取appid")
        APPID = getReValue(html, r'var g_appid =encodeURIComponent\("(\d+)"\);', 'Get AppId Error', 1)
        logging.critical("正在获取login_sig")
        sign = getReValue(html, r'var g_login_sig=encodeURIComponent\("(.+?)"\);', 'Get Login Sign Error', 0)
        logging.info('get sign : %s', sign)
        logging.critical("正在获取pt_version")
        JsVer = getReValue(html, r'var g_pt_version=encodeURIComponent\("(\d+)"\);', 'Get g_pt_version Error', 1)
        logging.info('get g_pt_version : %s', JsVer)
        logging.critical("正在获取mibao_css")
        MiBaoCss = getReValue(html, r'var g_mibao_css=encodeURIComponent\("(.+?)"\);', 'Get g_mibao_css Error', 1)
        logging.info('get g_mibao_css : %s', sign)
        StarTime = date_to_millis(datetime.datetime.utcnow())

        T = 0
        while True:
            T = T + 1
            self.Download('https://ssl.ptlogin2.qq.com/ptqrshow?appid={0}&e=0&l=L&s=8&d=72&v=4'.format(APPID), self.VPath)
            
            logging.info('[{0}] Get QRCode Picture Success.'.format(T))
            

            while True:
                html = self.Get('https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1&login2qq=1&aid={0}&u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1%26webqq_type%3D10&ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=0-0-{1}&mibao_css={2}&t=undefined&g=1&js_type=0&js_ver={3}&login_sig={4}'.format(APPID, date_to_millis(datetime.datetime.utcnow()) - StarTime, MiBaoCss, JsVer, sign), self.initUrl)
                # logging.info(html)
                ret = html.split("'")
                if ret[1] == '65' or ret[1] == '0':  # 65: QRCode 失效, 0: 验证成功, 66: 未失效, 67: 验证中
                    break
                time.sleep(3)
            if ret[1] == '0' or T > self.MaxTryTime:
                break

        #logging.info(ret)
        if ret[1] != '0':
            logging.info("获取二维码失败")
            return 0
        logging.critical("二维码已扫描，正在登陆")
        pass_time()
        # 删除QRCode文件
        if os.path.exists(self.VPath):
            os.remove(self.VPath)

        # 记录登陆账号的昵称
        tmpUserName = ret[11]

        html = self.Get(ret[5])
        #logging.critical("测试点1："+html)
        url = getReValue(html, r' src="(.+?)"', 'Get mibao_res Url Error.', 0)
        #logging.critical("测试点2："+url)
        if url != '':
            html = self.Get(url.replace('&amp;', '&'))
            url = getReValue(html, r'location\.href="(.+?)"', 'Get Redirect Url Error', 1)
            html = self.Get(url)
            #logging.critical("测试点3："+html)

        self.PTWebQQ = self.getCookie('ptwebqq')

        #logging.info('get PTWebQQ success: {0}'.format(self.PTWebQQ))

        LoginError = 1
        while LoginError > 0:
            try:
                html = self.Post('http://d.web2.qq.com/channel/login2', {
                    'r': '{{"ptwebqq":"{0}","clientid":{1},"psessionid":"{2}","status":"online"}}'.format(self.PTWebQQ, self.ClientID, self.PSessionID)
                }, Referer)
                ret = json.loads(html)
                LoginError = 0
            except:
                LoginError += 1
                logging.critical("登录失败，正在重试")
                
        if ret['retcode'] != 0:
            logging.critical("登录失败")
            return 0
        
        self.VFWebQQ = ret['result']['vfwebqq']
        self.PSessionID = ret['result']['psessionid']

        logging.critical("QQ号：{0} 登陆成功, 用户名：{1}".format(ret['result']['uin'], tmpUserName))
        logging.info('Login success')
        logging.critical("登陆二维码用时" + pass_time() + "秒")
        loginSucess()

        return ret['result']['uin']
       # msgId = int(random.uniform(20000, 50000))


    def updateGroupInfo(self,gname,gcode):
        """
          这部分获取群和及其成员的对应关系
       
        dirname = self.dirname + gname
        if os.path.exists(dirname) == False:
            #首次获取群info
            try:
                os.mkdir(dirname)
                filename = dirname+'/gruopInfo.txt'
                fobj = open(filename,'w')
                fobj.close()
            except:
                 info = '首次登入，创建目录或群列表失败！ 位置：函数updateGroupInfo(); qqnum: ' + self.dirname
                 stopError(info)
        """
        try:
            ts = time.time()
            while ts < 1000000000000:
                ts = ts * 10
            ts = int(ts)
            time.sleep(5)
            re = json.loads(self.Get('http://s.web2.qq.com/api/get_group_info_ext2?gcode={0}&vfwebqq={1}&t={2}'.format(gcode, self.VFWebQQ,ts), RefererGroupList))
            #logging.info("Get uin to account info:" + str(info))

        except:
            logging.info("获取group info失败！")
            return 0

        if re['retcode'] == 0:
            result = re['result']
            
            meminfo = result['minfo']
            ginfo = result['ginfo']

            #写入文件
            #第一行 群的基本信息
            #第二行 更新时间
            #第三行 人数  
            #第四行开始 每个成员 真实qq（获取失败 为0 ） + 相关信息  split(' ')

            ISOTIMEFORMAT = '%Y-%m-%d-%X'
            
            global UpdateMemInfo
            
            with open(self.GroupList[gname][4],'a+') as f:
                
                f.write(str(ginfo) + '\n')
                f.write(str(time.strftime(ISOTIMEFORMAT, time.localtime())) + '\n')
                f.write(str(len(meminfo)) + '\n')
                for mem in meminfo:
                    f.write( str(self.uin_to_account(mem['uin'])) + ' ' + str(mem) +'\n')
                    if UpdateMemInfo:
                        self.updateMemberList(self.uin_to_account(mem['uin']),self.GroupList[gname][5])
                        
                    
            return 1
        else:
            return 0 #获取失败

        

    def updateGroupList(self):
        """

          每次登陆时，都要获取最新的群列表，因为相关的中间值gid，gcode会更改
          groupList 关系到后面的相关各种操作
          群列表的基本对应信息
          
        Args:
            dirname : user's QQnum  ‘./qqnum’
            
        """
        #dirname = './' + dirname
        dirname = self.dirname
        #print 'updateGroupList\n'
        if os.path.exists(dirname) == False:
        #首次登陆
            try:
                os.mkdir(dirname)
                filename = dirname+'/GroupList.txt'
                fobj = open(filename,'w')
                fobj.close()

                global UpdateMemInfo,UpdateGroupInfo
                
                UpdateGroupInfo = True
                UpdateMemInfo = True
            except:
                 info = '首次登入，创建目录或群列表失败！ 位置：函数updateGroupList(); dirname: ' + dirname
                 stopError(info)

        """
         GroupList 的结构：
         groupName gid gcode realNum mCount memListPath memInfoPath messageLogPath memListUpdateTime

         groupName : 群的名字，作为key，真实的群号在开始时并不能获取到
         gid,gcode : 中间值，是相关的群标识
         realnum : 群的真实群号，如果可以获得（通过接收到的消息），初始为0
         memListPath : 群及成员关系存储路径
         memInfoPath : 成员详细信息路径 （如果可以获得）
         messageLogPath : 消息存储路径 
         memListUpdateTime : 成员列表跟新时间 暂时不用 2015-8-3
        """
        #读取groupList文件中已存的信息相关信息
        filename = dirname + '/GroupList.txt'
        with open(filename,'r') as fr:
            for line in fr.readlines():
                ginfo = []
                lineArr = line.strip().split(' ')
                # 独立添加，易于更改
                #groupName gid gcode realNum mCount memListPath memInfoPath messageLogPath memListUpdateTime
                ginfo.append( lineArr[1])
                ginfo.append( lineArr[2])
                ginfo.append( lineArr[3])
                ginfo.append( int(lineArr[4]))
                ginfo.append( unicode(lineArr[5].decode('utf-8')))
                ginfo.append( unicode(lineArr[6].decode('utf-8')))
                ginfo.append( unicode(lineArr[7].decode('utf-8')))

                self.GroupList.setdefault(unicode(lineArr[0].decode('utf-8')),ginfo)
                
                
        #print self.GroupList
        #获得最新的群列表
        try:
            HASH = getHash.getHashCode(self.qqnum,self.PTWebQQ)
            reqURL = "http://s.web2.qq.com/api/get_group_name_list_mask2"
            data = (
            ('vfwebqq',self.VFWebQQ),
            ('hash', HASH))
            html = self.Post(reqURL, data, RefererFind)
            ret = json.loads(html)
            #logging.info(ret)
        except:
            #当群列表失败时，下面的的消息处理会出现问题，故直接程序退出
            logging.critical("get group list failed!")
            info = "获得最新的群列表 failed!"
            stopError(info)
        
        if ret['retcode'] == 0:
            
            for re in ret['result']['gnamelist']:
                if re['name'] not in self.GroupList.keys(): #当这个群首次出现时，填充相关字段
                    
                    #创建群组的目录
                    try:
                        dirname = self.dirname+'/'+re['name']
                        os.mkdir(dirname)
                        
                        filename = dirname+'/GroupInfo.txt'
                        fobj = open(filename,'w')
                        fobj.close()
                        
                        filename = dirname+'/Message.txt'
                        fobj = open(filename,'w')
                        fobj.close()

                        filename = dirname+'/MemberInfo.txt'
                        fobj = open(filename,'w')
                        fobj.close()
                    except:
                        info = "首次获取新群，创建目录或群列表失败！" + str(self.qqnum)
                        stopError(info)

                    #填充数据
                    #groupName gid gcode realNum mCount memListPath memInfoPath messageLogPath
                    groupInfo = []
                    
                    groupInfo.append(re['gid'])
                    groupInfo.append(re['code'])
                    groupInfo.append(0)
                    groupInfo.append(0)
                    groupInfo.append(self.dirname+'/'+re['name']+'/GroupInfo.txt')
                    groupInfo.append(self.dirname+'/'+re['name']+'/MemberInfo.txt')
                    groupInfo.append(self.dirname+'/'+re['name']+'/Message.txt')
                    
                    
                    
                    self.GroupList.setdefault(re['name'],groupInfo)
                    
                else:
                    #print re['name']
                    self.GroupList[re['name']][0] = re['gid']
                    self.GroupList[re['name']][1] = re['code']
                    #update group info
                    
                if UpdateGroupInfo:
                    self.updateGroupInfo(re['name'],re['code'])

            self.closeGroupList()
                        
            
        else:
            #当群列表失败时，下面的的消息处理会出现问题，故直接程序退出
            info = '获取群列表失败！ QQnum: ' + dirname
            stopError(info)

        
            

    def updateMemberList(self,findnum,filename):
        """
           根据qq号，获取详细信息
        """
        
       
        skey = self.getCookie('skey')
        

        #logging.info('skey: {0}'.format(skey))

        #compute the ldw value
        
        n = int(5381)
        keystr = skey
        for i in keystr:
           n += (n<<5) + ord(i)
        ldwkey = n&2147483647
        #logging.info("ldw: {0}".format(ldwkey))
        
        try:
            reqURL = "http://cgi.find.qq.com/qqfind/buddy/search_v3"
            data = (
            ('keyword',findnum),
            ('ldw', ldwkey))
            html = self.Post(reqURL, data, RefererFind)
            #html = self.Post('http://cgi.find.qq.com/qqfind/buddy/search_v3', {
              #  'r': '{{"keyword":"{0}", "ldw":{1}}}'.format(self.findQQnum, ldwkey)
            #}, RefererFind)
            ret = json.loads(html)
            #logging.info(ret)
        except:
            logging.critical("find QQ num info failed!")
            return

        #写入文件中
        if ret['retcode'] == 0:
            ISOTIMEFORMAT = '%Y-%m-%d-%X'
            info = str(findnum) + ' ' + str(time.strftime(ISOTIMEFORMAT, time.localtime())) + ' ' + str(ret['result'] )  
            with open(filename,'a+') as f:
                f.write(info+'\n')
        

    def handleMessage(self,msgObj):

        for msg in msgObj['result']:
            msgType = msg['poll_type']

            # 群消息
            if msgType == 'group_message':
                #txt = combine_msg(msg['value']['content'])
                guin = msg['value']['from_uin'] #对应 gid
                grid = msg['value']['info_seq'] #对应真实的id
                tuin = msg['value']['send_uin']
                #seq = msg['value']['seq']
                #logging.info(msg)
                #print tuin
                send_qq = self.uin_to_account(tuin)

                info = str(msg) + ' ' + str(send_qq) #send_qq获取失败时，为0

                #查找信息属于的群，并存储
                GroupName = ''
                for groupName in self.GroupList.keys():
                   if guin == self.GroupList[groupName][0]:
                        GroupName = groupName

                with open(self.GroupList[GroupName][6],'a+') as f:
                    f.write(info + '\n')
                    
                self.GroupList[groupName][3] += 1
                    
            
            # QQ号在另一个地方登陆, 被挤下线
            if msgType == 'kick_message':
                logging.error(msg['value']['reason'])
                raise Exception, msg['value']['reason']  # 抛出异常, 重新启动WebQQ, 需重新扫描QRCode来完成登陆

    def closeGroupList(self):
        """
          程序运行完毕，将GroupList相关信息存入文件，下次使用
        """
        with open(self.dirname+'/GroupList.txt','w') as f:
            for (key,arr) in self.GroupList.items():
                info = str(key) + ' ' + str(arr[0])+ ' ' + str(arr[1]) + ' ' + str(arr[2]) + ' ' + str(arr[3]) + ' ' + str(arr[4]) + ' ' + str(arr[5]) + ' ' + str(arr[6])
                #print info
                f.write(info+'\n')

                
    def getMessage(self):
        """
           总体控制流程 （是否跟新群信息列表，由用户决定）
        """
        
        self.qqnum = self.login()
        if self.qqnum == 0:
            #登陆失败
            info = "登陆失败"
            stopError(info)
            
        else:
            self.dirname = './' + str(self.qqnum)
            self.updateGroupList()

            #self.closeGroupList()
        """
            try:
                t_check = check_msg(self.PTWebQQ,self.PSessionID,self.ClientID,self.handleMessage)
                t_check.setDaemon(True)
                t_check.start()
                logging.info("消息轮询开始 "+ self.qqnum)
                t_check.join()
                logging.info("程序退出 "+ self.qqnum)
            except KeyBoardError:
                logging.error("程序被强制退出")
                self.closeGroupList()
                sys.exit()
        """
        
        


class check_msg(threading.Thread):
 

    def __init__(self,PTWebQQ,PSessionID,ClientID,msgHandler):
        
        self.PTWebQQ = PTWebQQ
        self.PSessionID = PSessionID
        self.ClientID = ClientID
        self.msgHandler = msgHandler
        
        threading.Thread.__init__(self)
        

    def run(self):
        E = 0
        # 心跳包轮询
        while 1:
            if E >= 5:
                break
            try:
                time.sleep(60)
                ret = self.check()
            except:
                E += 1
                continue
            # logging.info(ret)
			
            # 返回数据有误
            if ret == "":
                E += 1
                continue

            # POST数据有误
            if ret['retcode'] == 100006:
                break

            # 无消息
            if ret['retcode'] == 102:
                E = 0
                continue

            # 更新PTWebQQ值
            if ret['retcode'] == 116:
                self.PTWebQQ = ret['p']
                E = 0
                continue

            if ret['retcode'] == 0:
                # 信息分发
                try:
                    self.msgHandler(ret)
                    E = 0
                    continue
                except Exception as e:
                    logging.error(str(e))
                    logging.error("信息分发出错！")
                    E = 5
        logging.critical("轮询错误超过五次或发生致命错误！")

    # 向服务器查询新消息
    def check(self):

        html = HttpClient_Ist.Post('http://d.web2.qq.com/channel/poll2', {
            'r': '{{"ptwebqq":"{1}","clientid":{2},"psessionid":"{0}","key":""}}'.format(self.PSessionID, self.PTWebQQ, self.ClientID)
        }, Referer)
        #logging.info("Check html: " + str(html))
        try:
            ret = json.loads(html)
        except Exception as e:
            logging.error(str(e))
            logging.critical("get json Check error occured, retrying.")
            return self.check()

        return ret


# -----------------
# 主程序
# -----------------

if __name__ == "__main__":
    
    UpdateGroupInfo = False
    UpdateMemInfo = False
    
    
    if len(sys.argv) == 2:

        if sys.argv[1] == 1:
            UpdateGroupInfo = True
        if sys.argv[1] == 2:
            UpdateGroupInfo = True
            UpdateMemInfo = True
            
    QQGroupMe = UserGetMessage()
    QQGroupMe.getMessage()
    
    try:
        t_check = check_msg(QQGroupMe.PTWebQQ,QQGroupMe.PSessionID,QQGroupMe.ClientID,QQGroupMe.handleMessage)
        #t_check.setDaemon(True)
        t_check.start()
        logging.info("消息轮询开始 " + str(QQGroupMe.qqnum) )
        t_check.join()
       
    except :
        logging.error("程序被强制退出 checkmsg error" + str(QQGroupMe.qqnum) )
        
        
    logging.info("程序退出 " + str(QQGroupMe.qqnum) )
    QQGroupMe.closeGroupList()
    sys.exit()
    
