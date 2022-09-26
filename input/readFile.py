"""
二进制文件读取
"""
# 跨目录调用: 路径添加
import sys
import inspect

sys.path.append(inspect.getfile(inspect.currentframe()))
from namespace import filePath, funcParam
# ...
import struct
import os
import shutil
import platform
import threading
import time
from typing import List


def __get_files(*section) -> List[str]:
    """ 获取对应区间的文件
    param
        section: 可变位数 区间码
    return
        ["", "", ...]
    """
    return [f for f in os.listdir(filePath.binaryPath)
            if f.lower().find('done') == -1 and f[3] in section]


def read_one_file(moduleName):
    """ 气体、环境、振动、机械特性(隔离开关) - 单文件
    param
        moduleName 模块名
    return
    """
    __get_files(funcParam.modToSec[moduleName])

    pass


def read_mb_file():
    """ 机械特性(断路器) - 多文件匹配
    param
    return
    """
    pass


def read_pd_file():
    """ 局放 - 网口 + 累计
    param
    return
    """
    pass


def read_touch_file():
    """ 红外视频 - 网口
    param
    return
    """
    pass


def read_es_file():
    """ 储能 - 定时等待
    param
    return
    """
    pass
