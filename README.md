# auto_player

很早以前写的一个自动点击小工具，主要拿来给模拟器里的游戏做些重复操作。

思路比较简单：截屏后用 OpenCV 找模板图，找到就点一下。后来又加了 OCR，可以直接按文字找按钮。既可以用 `pyautogui` 操作桌面，也可以通过 ADB 操作 Android 设备。

仓库里的 `demo_yys.py` 和 `demo_azure.py` 是当时自己用的两个例子，可以从这里看基本用法。

## 安装

```bash
pip install -r requirements.txt
```

如果只用图片匹配，不需要装 PaddlePaddle 和 PaddleHub。最小依赖如下：

```bash
pip install opencv-python numpy pillow pyautogui
```

OCR 相关依赖：

```bash
pip install paddlepaddle paddlehub
```

## 图片匹配

先把按钮截图放进 `wanted` 目录，文件名就是之后要查找的名字。例如：

```text
wanted/
├── yys_tiaozhan.jpg
└── yys_jixu.jpg
```

然后创建一个 `Player`：

```python
import time

from auto_player import Player


player = Player(accuracy=0.8, adb_mode=True)

while True:
    player.find_touch(["yys_tiaozhan", "yys_jixu"])
    time.sleep(1)
```

`find_touch` 会按列表顺序查找，点到第一个匹配项后返回它的名字，全部没找到时返回 `False`。

不用 ADB 的话，把 `adb_mode` 改成 `False`，程序会直接控制当前电脑的鼠标。

## OCR

有些按钮不方便截模板，可以用 OCR 版本：

```python
import time

from auto_ocr_player import OCR_Player


player = OCR_Player(accuracy=0.6, adb_mode=True)

while True:
    player.find_touch(["s挑战", "点击屏幕继续"])
    time.sleep(1)
```

普通字符串是包含匹配，前面加 `s` 表示完全匹配。比如 `s挑战` 只会匹配“挑战”，不会匹配“挑战成功”。

## 配置

常用配置在 `auto_player.py` 开头，也可以通过环境变量覆盖：

| 环境变量 | 用途 |
| --- | --- |
| `AUTO_PLAYER_WANTED` | 模板图片目录 |
| `AUTO_PLAYER_SCREEN` | 截图保存目录 |
| `AUTO_PLAYER_ADB` | ADB 命令或完整路径 |
| `AUTO_PLAYER_NOX_SHARE` | 模拟器共享目录，可不填 |

连接多台设备时，可以用 `adb_num` 选择 `adb devices` 列表中的设备，下标从 0 开始。

匹配不到时一般先检查模板图和当前画面的分辨率是否一致，再适当调低 `accuracy`。如果只需要识别画面的某一块，可以给 `find_touch` 或 `exist` 传 `area=[h1, h2, w1, w2]`，这里用的是百分比坐标。

## 其他

这套代码主要是自用，接口不多，具体可以直接看 `auto_player.py`：

- `exist`：只检查目标是否存在
- `find_touch`：查找并点击
- `touch`：点击指定坐标
- `drag`：拖动或长按
- `screen_shot`：截取当前画面
- `cut`：按百分比裁剪画面

请只在自己有权限操作的设备和应用中使用。
