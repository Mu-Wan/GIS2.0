"""
数据解析: 长度 公式
"""
import sys
import inspect

sys.path.append(inspect.getfile(inspect.currentframe()))
from namespace import constant as cn
import numpy as np

# 1. 文件内需要拆分
infoLen = 14
# 振动
busVibLen = 3995
# 机械特性 - 隔离开关
msLen = 3000
# 机械特性 - 断路器
mbCurLen = 3000
mbSwitchLen = 3000
mbCSLen = mbCurLen * 3 + mbSwitchLen - infoLen
mbTripLen = 3000 - infoLen
# 储能
esNoLen = (100 - 14) / 2
esActLen = (12000 - 14) / 2
esCurLen = 6000
esNoActSize = 15 * (10 ** 3)
# 触头
eContactSplit = b'\x5A\x5A\x02\x06'

# 2. 公式
phaseLetter = ['A', 'B', 'C']


# 气体

# 温湿度
def to_env(data) -> np.ndarray:
    """ 转电流幅值
    param
        data: 数据
    return
        []
    """
    return (np.array(data) * 3.3 / 4095 - 1.25) * 10 * 6.25 - 25


# 振动 - 母线
def to_bus_vib(data) -> np.ndarray:
    """ 转振动幅值
    param
        data: 数据
    return
        []
    """
    return np.array(data) * 3.3 / (1.8 * 1024) - 2


# 振动 - 断路器
def to_mb_vib(data) -> np.ndarray:
    """ 转振动幅值
    param
        data: 数据
    return
        []
    """
    return np.array(data) * 100 / 4096 - 50


# 机械特性 - 隔离开关
def to_ms_cur(data, locNum: int) -> np.ndarray:
    """ 转电流幅值
    param
        data: 数据
        locNum: 监测位置
    return
        []
    """
    factor = cn.config['ms']['cur']['curC']
    return (np.array(data) * 3.3 / 4096 - 1.633) * 15 / 0.625 * factor[locNum]


# 机械特性 - 断路器
def to_mb_cur(data) -> np.ndarray:
    """ 转电流幅值
    param
        data: 数据
    return
        []
    """
    return np.array(data) * 3.3 * 8 / 4096 / (1 + 50 / 12)


def to_mb_trip(data, phase: int) -> np.ndarray:
    """ 转行程
    param
        data: 数据
        phase: 相数
    return
        []
    """
    pulse = cn.config['mb'][phaseLetter[phase]]['trip']['pulse']
    return (np.array(data) - pulse * 2) * 360 / pulse * 4


# 储能
def to_es_cur(data, phase: int) -> np.ndarray:
    """ 转电流幅值
    param
        data: 数据
        phase: 相数
    return
        []
    """
    factor = cn.config['es']['cur']['curC']
    return (np.array(data) * 3.3 / 4096 - 1.633) * 15 / 0.625 * factor[phase]


def to_es_spring(data) -> np.ndarray:
    """ 转弹簧压力值
    param
        data: 数据
    return
        []
    """
    return (np.array(data) / 4096 * 3.3) / 66 * 1000 * 1.9445


# 局放
def to_pd(data) -> np.ndarray:
    """ 转局放幅值
    param
        data: 数据
    return
        []
    """
    data = 5 - (5 * np.array(data)) / 2048
    return 10 * np.log10(data ** 2 / 50 * 1000 + 1e-7)

# 触头
