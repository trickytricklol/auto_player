# -*- coding: utf-8 -*-
"""
阴阳师（Onmyoji）自动挂机示例。

两种模式任选其一：
    python demo_yys.py ocr    # OCR 文字识别模式（识别并点击文字按钮）
    python demo_yys.py cv     # CV 模板匹配模式（匹配 wanted 目录下的模板图）
"""

import sys
import time

from auto_ocr_player import OCR_Player
from auto_player import Player


def run_ocr_mode():
    """OCR 模式：识别并点击「挑战」「点击屏幕继续」。"""
    player = OCR_Player(accuracy=0.6, adb_mode=True)
    while True:
        player.find_touch(["s挑战", "点击屏幕继续"])
        time.sleep(1)


def run_cv_mode():
    """CV 模板匹配模式：匹配 wanted 目录下的 yys_tiaozhan / yys_jixu 模板图。"""
    player = Player(accuracy=0.8, adb_mode=True)
    while True:
        player.find_touch(["yys_tiaozhan", "yys_jixu"])
        time.sleep(1)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "ocr"
    if mode == "cv":
        run_cv_mode()
    else:
        run_ocr_mode()
