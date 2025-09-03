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

    def input_phone_number_and_click_get_code(self,phone_number:str):
        """输入手机号并点击获取验证码"""
        try:
            self.tab.ele('@@name=normal-input').input(phone_number)
            self.tab.ele('@text()=获取验证码').click()
        except Exception as e:
            print(f"输入手机号并点击获取验证码失败: {e}")
            return False

    def input_verify_code_and_click_login(self,code:str):
        """输入验证码并点击登录"""
        try:
            self.tab.ele('@@name=button-input').input(code) # 输出验证码
            self.tab.ele('@@style=width: 253px; height: 48px;').click() # 点击登录
        except Exception as e:
            print(f"输入验证码并点击登录失败: {e}")
            return False


if __name__ == '__main__':
    get_douyin_msg = GetDouyinMsg()
    get_douyin_msg.set_url('https://e.douyin.com/site/douyin-mp/login')
    get_douyin_msg.input_phone_number_and_click_get_code("19127619377")
    # print(get_douyin_msg.get_user_list())
