import time
import pyperclip
from pynput import mouse

has_clicked = False

def on_click(x, y, button, pressed):
    global has_clicked
    if button == mouse.Button.left and pressed and not has_clicked:
        has_clicked = True
        return False

# 启动监听器
listener = mouse.Listener(on_click=on_click)
listener.start()

# 等待点击
while not has_clicked:
    time.sleep(0.1)

# 等待系统完成复制（0.5秒足够）
time.sleep(0.5)

# 获取剪贴板内容
captcha = pyperclip.paste()

print(captcha)


listener.stop()