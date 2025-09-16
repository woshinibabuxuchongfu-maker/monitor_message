from re import S
from time import sleep
import time
from DrissionPage import Chromium
from cachetools import Cache

class GetDouyinMsg:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GetDouyinMsg, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.browser = None
            self.tab = None
            self._initialized = True
            self.url = None
            self.user_list=Cache(maxsize=10000)

    def _initialize_browser(self, url: str):
        """初始化浏览器"""
        if self.browser is None:
            self.browser = Chromium()
            self.tab = self.browser.latest_tab
            if self.tab is None:
                self.tab = self.browser.latest_tab
        if self.tab is not None:
            if url is not None:
                self.tab.get(url)
            return self.tab

    def set_url(self, url: str):
        self.url = url
        self._initialize_browser(self.url)

    def get_url(self):
        return self.url

    def get_tab(self):
        return self.tab
    
    def is_connected(self):
        """检查浏览器连接状态"""
        try:
            if not self.browser or not self.tab:
                return False
            # 尝试获取当前URL来检查连接状态
            current_url = self.tab.url
            return current_url is not None
        except Exception as e:
            print(f"检查连接状态失败: {e}")
            return False
    
    def close_browser(self):
        if self.browser is not None:
            self.browser.close()
            self.browser = None
            self.tab = None
            self.url = None
            self._initialized = False
    
    def get_user_list(self) -> list:
        """提取抖音用户列表"""
        try:
            UserList = self.tab.ele('@@class=rc-virtual-list-holder-inner').children() # 获取用户列表元素[]
            list=[]
            for user in UserList:
                list.append(user.child().child(2).child().child().child().text)
            return list
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return False
    
    def _get_user_list(self) -> list:
        """获取左侧用户列表,返回用户列表中每个用户的元素"""
        try:
            if not self.tab:
                return []
            
            # 尝试多种选择器来获取用户列表
            selectors = [
                '@@class=flex-1 ml-2 overflow-x-hidden w-full',
                '@@class=rc-virtual-list-holder-inner',
                'xpath=//div[contains(@class, "flex-1") and contains(@class, "ml-2")]',
                'xpath=//div[contains(@class, "rc-virtual-list")]'
            ]
            
            for selector in selectors:
                try:
                    elements = self.tab.eles(selector)
                    if elements:
                        print(f"使用选择器 '{selector}' 找到 {len(elements)} 个用户元素")
                        return elements
                except Exception as e:
                    print(f"选择器 '{selector}' 失败: {e}")
                    continue
            
            print("所有选择器都失败了")
            return []
            
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    def _get_user_msgs(self):
        """获取用户的消息"""
        try:
            if not self.tab:
                return []
            msgs = self.tab.eles('@@class=leadsCsUI-NormalMessage leadsCsUI-NormalMessage_left')
            return msgs
        except Exception as e:
            print(f"获取用户消息失败: {e}")
            return []
    
    def refresh_page(self):
        """刷新当前页面；若刷新失败则回退到重新打开URL"""
        try:
            if self.tab is None:
                return
            self.tab.refresh()
        except Exception:
            if self.url and self.tab is not None:
                try:
                    self.tab.get(self.url)
                except Exception:
                    pass

    def wait_for_user_list(self, timeout: int = 10) -> bool:
        """等待用户列表元素出现并非空，返回是否成功。"""
        start_ts = time.time()
        while time.time() - start_ts < timeout:
            try:
                elements = self._get_user_list()
                if elements:
                    return True
            except Exception:
                pass
            sleep(0.5)
        return False

    def refresh_and_wait_user_list(self, timeout: int = 10) -> bool:
        """刷新页面并等待用户列表加载完成。"""
        self.refresh_page()
        sleep(2)
        return self.wait_for_user_list(timeout)
        

if __name__ == '__main__':
    get_douyin_msg = GetDouyinMsg()
    get_douyin_msg.set_url('https://leads.cluerich.com/pc/cs/chat/session?fullscreen=1')
    # get_douyin_msg.input_phone_number_and_click_get_code("19127619377")
    # print(get_douyin_msg.get_user_list())
    # print(get_douyin_msg.get_user_list())
    # 先获取到所有的用户列表，然后通过用户名和下面的消息判断是否是新消息，如果是则点击该用户然后获取用户的消息判断是否违规

    sleep(3)
    user_list=get_douyin_msg._get_user_list()
    print(len(user_list))
    sleep(1)
    user_list.reverse()
    for user in user_list:
        print(user.child().child().child().text) # 用户名
        # 判断是否是新消息 TODO:
        # 是：点击消息
        sleep(1)
        user.click()
        sleep(1)
        for item in get_douyin_msg.tab.eles('xpath=//*[@class=\'leadsCsUI-MessageItem\']//*[@class=\'leadsCsUI-Text\']'):
            print(item.text)
        sleep(1)