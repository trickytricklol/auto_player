# -*- coding: utf-8 -*-
"""
青云志（Azure）自动挂机示例：根据当前场景自动切换任务策略。

流程：先探测当前处于哪个玩法（演习 / 北地活动），
再选择对应的关键字步骤循环点击；次数不足时自动结束。
"""

import time

from auto_ocr_player import OCR_Player


def main():
    player = OCR_Player(accuracy=0.6, adb_mode=True)

    tuiyi = ["键退", "确定", "点击继续", "没找到符合条件"]
    zhuxian = ["立刻前往", "再次前往", "s整理", "迎击"]
    huodong = ["刻前", "北地", "出击", "战斗胜利", "确定"]
    yanxi = ["次数不足", "关闭", "开始", "综合实力", "出击", "评价", "功勋", "确定"]

    yx, bd = player.exist(["演习", "北地"])
    if yx:
        steps = yanxi
    elif bd:
        steps = huodong
    else:
        steps = zhuxian
    print("当前策略:", steps)

    while True:
        re = player.find_touch(steps)
        if re == "次数不足":
            print("次数不足，结束挂机")
            break
        if re == "整理":
            while player.find_touch(tuiyi) != "没找到符合条件":
                time.sleep(1)
            player.find_touch(["取消", ])
        if re == "迎击":
            player.find_touch(["自律", ])
            time.sleep(3)
        time.sleep(1)


if __name__ == "__main__":
    main()
