# -*- coding: utf-8 -*-
"""
auto_player —— 基于 OpenCV 模板匹配的自动点击框架（桌面 / ADB 双模式）。

- 桌面模式：用 pyautogui 直接控制电脑鼠标，适合操作模拟器窗口或 PC 应用；
- ADB 模式：通过 ADB 命令控制 Android 设备 / 模拟器，无需遮挡窗口。

核心 API
    Player(accuracy, adb_mode, adb_num)   初始化
    screen_shot()                         截屏并返回 cv2 图片
    locate(target_name)                   在大图上定位模板，返回命中点中心列表
    exist([name...])                      判断目标是否存在（不点击）
    find_touch([name...])                 按优先级查找并点击第一个命中的目标
    touch(pos) / drag(p1, p2)             点击 / 拖动（自带随机偏移）
    cut(img, area)                        按百分比裁剪图片，加速匹配
"""

import os
import random
import subprocess
import time

import cv2
import numpy
import pyautogui
from PIL import ImageGrab

# ---------------------------------------------------------------------------
# 配置区（按需修改，也可用同名环境变量覆盖，优先级：环境变量 > 此处默认值）
# ---------------------------------------------------------------------------
# 模板目录：目录下每张图片（不含扩展名的文件名）即一个可匹配的目标名
WANTED_PATH = os.environ.get(
    "AUTO_PLAYER_WANTED",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "wanted"),
)
# 截图保存目录
SCREEN_PATH = os.environ.get(
    "AUTO_PLAYER_SCREEN",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen"),
)
# ADB 命令：已加入系统 PATH 直接写 "adb"；否则写完整命令前缀，
# 如 r"D:\Nox\bin\nox_adb.exe" 或原版的 "d: && cd \\mysys\\Nox\\bin\\ && nox_adb.exe"
ADB_CMD = os.environ.get("AUTO_PLAYER_ADB", "adb")
# 模拟器共享目录：部分模拟器截图会自动同步到此目录（ADB 模式可选）
NOX_SHARE = os.environ.get("AUTO_PLAYER_NOX_SHARE", "")

# 桌面模式下鼠标操作的全局延迟，程序已内置随机延迟，一般无需修改
pyautogui.PAUSE = 0.001

os.makedirs(SCREEN_PATH, exist_ok=True)


def run_cmd(cmd):
    """执行系统命令并返回标准输出。

    兼容 "adb" 与 "d: && cd ... && nox_adb.exe" 两种写法（Windows shell）。
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout or ""
    except Exception as exc:  # 环境相关的底层异常，直接暴露便于排查
        print(f"[run_cmd] 命令执行失败: {cmd!r} -> {exc}")
        return ""


class Player(object):
    """基于模板匹配的自动点击器。

    参数:
        accuracy: 匹配精准度阈值，0~1，越大越严格（默认 0.8）
        adb_mode: True 走 ADB 模式，False 走桌面鼠标模式
        adb_num:  连接多台 ADB 设备时选择第几台（从 0 开始）
    """

    def __init__(self, accuracy=0.8, adb_mode=False, adb_num=0):
        super(Player, self).__init__()
        self.accuracy = accuracy
        self.adb_mode = adb_mode
        self.screen = None
        self.target_map = {}
        self.device = None
        self.load_target()
        if self.adb_mode:
            self._init_adb(adb_num)
        else:
            w, h = pyautogui.size()
            print(f"桌面模式，屏幕尺寸: {w}x{h}")

    # ------------------------------------------------------------------ ADB
    def _init_adb(self, adb_num):
        """初始化 ADB 连接，选择第 adb_num 台设备。"""
        output = run_cmd(f"{ADB_CMD} devices")
        print(output)
        device_list = [line.split("\t")[0] for line in output.split("\n") if "\tdevice" in line]
        if not device_list:
            raise RuntimeError("未检测到 ADB 连接设备，请检查 ADB 配置与设备连接")
        if adb_num >= len(device_list):
            raise RuntimeError(f"adb_num={adb_num} 超出设备数量 {len(device_list)}")
        self.device = device_list[adb_num]
        print(run_cmd(f"{ADB_CMD} -s {self.device} shell wm size"))

    # ---------------------------------------------------------------- 模板
    def load_target(self):
        """读取模板目录下所有图片作为匹配目标，返回 {目标名: [cv2图片, 目标名]}。"""
        if not os.path.isdir(WANTED_PATH):
            raise FileNotFoundError(f"模板目录不存在: {WANTED_PATH}")
        target_map = {}
        for file in sorted(os.listdir(WANTED_PATH)):
            if not file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                continue
            name = os.path.splitext(file)[0]
            img = cv2.imread(os.path.join(WANTED_PATH, file))
            if img is None:
                print(f"警告: 无法读取模板图片 {file}")
                continue
            target_map[name] = [img, name]
        print("已加载模板:", list(target_map.keys()))
        self.target_map = target_map
        return target_map

    # ---------------------------------------------------------------- 截屏
    def screen_shot(self, name="screen", save=True):
        """截取当前屏幕并返回 cv2 图片。

        save=True 时保存到 screen 目录（桌面模式 name='screen' 时也默认不落盘）。
        """
        if self.adb_mode:
            remote = f"sdcard/Pictures/{name}.jpg"
            run_cmd(f"{ADB_CMD} -s {self.device} shell screencap -p {remote}")
            run_cmd(f"{ADB_CMD} -s {self.device} pull {remote} {SCREEN_PATH}\\{name}.jpg")
            screen = cv2.imread(os.path.join(SCREEN_PATH, f"{name}.jpg"))
            if screen is None and NOX_SHARE:  # 部分模拟器截图自动同步到共享目录
                screen = cv2.imread(os.path.join(NOX_SHARE, f"{name}.jpg"))
        else:
            grab = ImageGrab.grab()
            if save and name != "screen":  # 默认截图只读内存，不落盘
                grab.save(os.path.join(SCREEN_PATH, f"{name}.jpg"))
            screen = cv2.cvtColor(numpy.array(grab), cv2.COLOR_RGB2BGR)
        print("截图已完成 ", time.ctime())
        self.screen = screen
        return screen

    # ---------------------------------------------------------------- 操作
    def random_offset(self, position, range=5):
        """在目标坐标附近随机偏移，模拟人手点击，降低被脚本检测的概率。"""
        x, y = position
        return x + random.randint(-range, range), y + random.randint(-range, range)

    def touch(self, position):
        """点击目标坐标（自带随机偏移）：ADB 模式模拟触摸，桌面模式用鼠标。"""
        x, y = self.random_offset(position)
        if self.adb_mode:
            run_cmd(f"{ADB_CMD} -s {self.device} shell input touchscreen tap {x} {y}")
        else:
            origin = pyautogui.position()
            dt = random.uniform(0.01, 0.02)
            pyautogui.moveTo(x, y, duration=dt)
            pyautogui.mouseDown(button="left")
            time.sleep(dt)  # 部分游戏只认"按下+抬起"，不认 click
            pyautogui.mouseUp(button="left")
            pyautogui.moveTo(*origin, duration=dt)

    def drag(self, position_start, end, second=0.2):
        """从起点拖动到终点（或长按），自带随机偏移；ADB 模式用 swipe 实现。"""
        sx, sy = self.random_offset(position_start)
        ex, ey = self.random_offset(end)
        if self.adb_mode:
            run_cmd(
                f"{ADB_CMD} -s {self.device} shell input touchscreen swipe "
                f"{sx} {sy} {ex} {ey} {int(second * 1000)}"
            )
        else:
            origin = pyautogui.position()  # 记录原位，操作完返回
            dt = random.uniform(0.01, 0.02)
            pyautogui.moveTo(sx, sy, duration=dt)
            pyautogui.dragTo(ex, ey, duration=second + dt)
            pyautogui.moveTo(*origin, duration=dt)

    # ---------------------------------------------------------------- 定位
    @staticmethod
    def mark(background, p1, p2):
        """在图上用红色矩形标出匹配区域（调试用）。p1 左上，p2 右下。"""
        cv2.rectangle(background, p1, p2, (0, 0, 255), 3)

    @staticmethod
    def _distance(p1, p2):
        """计算两点欧氏距离，用于合并邻近的重复命中点。"""
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def locate(self, background, target_name, debug=0):
        """在大图 background 上定位模板 target_name，返回所有命中位置的中心点列表。

        debug=1 时用窗口显示匹配结果（按任意键关闭）。模板不存在时抛出明确异常。
        """
        if target_name not in self.target_map:
            raise KeyError(
                f"未找到模板 '{target_name}'，请确认模板目录下存在 {target_name}.jpg"
            )
        target, c_name = self.target_map[target_name]
        h, w, _ = target.shape
        result = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
        ys, xs = numpy.where(result >= self.accuracy)
        # 按相关性从高到低排序，去重后每个簇保留的都是该簇最优的匹配
        candidates = sorted(
            ((float(result[y, x]), x, y) for y, x in zip(ys, xs)),
            reverse=True,
        )
        loc_pos = []
        for _, x, y in candidates:
            center = (x + int(w / 2), y + int(h / 2))
            if loc_pos and self._distance(loc_pos[-1], center) < 20:
                continue  # 忽略邻近的重复命中点，保留相关性更高的那个
            loc_pos.append(center)
            self.mark(background, (x, y), (x + w, y + h))

        if debug:  # 在图上显示查找结果，调试时开启
            cv2.imshow(f"result for {c_name}:", background)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        print(f"查找结果：{c_name} 匹配到 {len(loc_pos)} 个位置")
        return loc_pos

    def cut(self, img, area=(0, 50, 0, 50)):
        """按百分比裁剪图片以加速匹配。

        area = [h1, h2, w1, w2]，分别表示高、宽的起止百分比。
        返回 (裁剪后的图片, 左上角在原图中的坐标)。
        """
        h1, h2, w1, w2 = [e / 100 for e in area]
        h, w, _ = img.shape
        # 用 round 而非 int，避免浮点精度导致裁剪边界少 1 像素（如 int(700*0.7)=489）
        h1, h2 = round(h * h1), round(h * h2)
        w1, w2 = round(w * w1), round(w * w2)
        return img[h1:h2, w1:w2, :], [w1, h1]

    def exist(self, name_list, area=None):
        """判断目标是否存在（不点击）。

        传入列表返回等长的真假列表；传入单个名字返回布尔值。
        """
        background = self.screen_shot()
        start = (0, 0)
        if area:
            background, start = self.cut(background, area)
        name_list = name_list if type(name_list) == list else [name_list, ]
        re = []
        for name in name_list:
            try:
                loc_pos = self.locate(background, name)
            except KeyError as exc:  # 模板缺失时按未命中处理，避免挂机循环中断
                print(f"警告: {exc}，按未命中处理")
                loc_pos = []
            cur = len(loc_pos) > 0
            re.append(cur)
        re = re[0] if len(re) == 1 else re
        return re

    def find_touch(self, name_list, area=None):
        """按优先级查找目标，点击第一个命中的目标后立即返回其名字；全部未命中返回 False。

        注意有优先级顺序，找到前面的就不会再找后面的。
        area 不为空时，自动把裁剪坐标还原为原图坐标。
        """
        background = self.screen_shot()
        start = (0, 0)
        if area:
            background, start = self.cut(background, area)
        name_list = name_list if type(name_list) == list else [name_list, ]
        for name in name_list:
            try:
                loc_pos = self.locate(background, name)
            except KeyError as exc:  # 模板缺失时跳过继续找下一个，避免挂机循环中断
                print(f"警告: {exc}，跳过")
                continue
            if not loc_pos:
                continue
            x, y = loc_pos[0]  # 同一目标命中多处时只点第一个
            self.touch((x + start[0], y + start[1]))
            return name
        return False
