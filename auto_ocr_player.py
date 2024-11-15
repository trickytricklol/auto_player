# -*- coding: utf-8 -*-
"""
auto_ocr_player —— 基于 OCR 文字识别的自动点击器（auto_player 的 OCR 扩展）。

原理：先截屏，用 PaddleHub 的中文 OCR 模型识别出所有文字及其坐标，
再按关键字匹配并点击目标文字。适合按钮样式不固定、只能用文字定位的场景。

关键字规则：
    普通关键字 -> 子串匹配（text 包含该关键字即命中）
    以 's' 开头 -> 精确匹配（如 's挑战' 只匹配完全等于"挑战"的文字）
"""

from auto_player import Player


class OCR_Player(Player):
    """OCR 版 Player。用法与 Player 一致，另提供 read() 获取识别结果。"""

    OCR_MODULE = "chinese_ocr_db_crnn_mobile"  # PaddleHub 中文 OCR 模型名

    def __init__(self, accuracy=0.6, adb_mode=False, adb_num=0):
        super(OCR_Player, self).__init__(accuracy, adb_mode, adb_num)
        self._ocr = None
        self.accuracy = accuracy

    def _get_ocr(self):
        """懒加载 OCR 模型：不使用 OCR 时无需安装 paddle 系依赖。"""
        if self._ocr is None:
            try:
                import paddlehub as hub
            except ImportError:
                raise RuntimeError("未安装 paddlehub，请先执行: pip install paddlepaddle paddlehub")
            self._ocr = hub.Module(name=self.OCR_MODULE, enable_mkldnn=True)
        return self._ocr

    def read(self, debug=False, output_dir="ocr_result"):
        """截屏并识别图中所有文字。

        debug=True 时将识别结果可视化保存到 output_dir。
        返回识别数据列表，每项含 text 与 text_box_position 等字段。
        """
        screen = self.screen_shot()
        ocr = self._get_ocr()
        results = ocr.recognize_text(
            images=[screen],               # 图片数据，ndarray，BGR 格式
            use_gpu=False,                 # 使用 GPU 前需设置 CUDA_VISIBLE_DEVICES
            output_dir=output_dir,         # 可视化结果的保存路径
            visualization=debug,           # 是否将识别结果保存为图片文件
            box_thresh=self.accuracy,      # 检测文本框置信度阈值
            text_thresh=self.accuracy,     # 识别中文文本置信度阈值
        )
        return results[0]["data"] if results else []

    def _match(self, key, data):
        """按关键字规则从识别结果中过滤命中项，返回 [(text, 文字中心坐标), ...]。"""
        exact = key[0] == "s"  # 's' 开头表示精确匹配
        target = key[1:] if exact else key
        found = []
        for item in data:
            text = item.get("text", "")
            hit = (text == target) if exact else (target in text)
            if not hit:
                continue
            p1, _, p2, _ = item["text_box_position"]
            (x1, y1), (x2, y2) = p1, p2
            center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
            found.append((text, center))
        return found

    def find_touch(self, key_list, debug=False):
        """按优先级匹配 OCR 文字并点击第一个命中项；全部未命中返回 False。"""
        data = self.read(debug)
        key_list = [key_list, ] if type(key_list) == str else key_list
        for key in key_list:
            found = self._match(key, data)
            print(f"目标：{key},  找到数量：{len(found)}")
            if found:
                self.touch(found[0][1])
                return key
        return False

    def exist(self, key_list, debug=False):
        """判断 OCR 文字是否存在。

        返回命中数量：单个关键字返回 int，列表返回等长 int 列表。
        """
        data = self.read(debug)
        key_list = [key_list, ] if type(key_list) == str else key_list
        re = []
        for key in key_list:
            found = self._match(key, data)
            print(f"目标：{key},  找到数量：{len(found)}")
            re.append(len(found))
        re = re[0] if len(re) == 1 else re
        return re
