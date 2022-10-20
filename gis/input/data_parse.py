"""
数据解析: 长度 公式
"""
from namespace import constant as cn
import numpy as np
import binascii

# 1. 文件内需要拆分
infoLen = 14
# 振动
busVibLen = cn.bConfig['vib']['bus']['dotCount'] - 1
# 机械特性 - 隔离开关
msLen = cn.bConfig['ms']['cur']['dotCount']
msRate = cn.bConfig['ms']['cur']['rate']
msT = cn.bConfig['ms']['cur']['T']
msFactor = cn.bConfig['ms']['cur']['curC']
# 机械特性 - 断路器
mbCurLen = 3000
mbSwitchLen = 3000
mbCSLen = mbCurLen * 3 + mbSwitchLen - infoLen
mbTripLen = 3000 - infoLen
# 储能
esNoLen = int((cn.bConfig['es']['spring']['normCount'] * 2 - 14) / 2)
esActLen = int((cn.bConfig['es']['spring']['actCount'] * 2 - 14) / 2)
esCurLen = cn.bConfig['es']['cur']['dotCount']
esT = cn.bConfig['es']['base']['T']
esRate = cn.bConfig['es']['base']['rate']
esFactor = cn.bConfig['es']['cur']['curC']
esNoActSize = 15 * (10 ** 3)
# 局放
minSet = cn.bConfig['pd']['base']['minSet']
maxSet = cn.bConfig['pd']['base']['maxSet']
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
    """ 转直流电流幅值
    param
        data: 数据
        locNum: 监测位置
    return
        []
    """
    data = (np.array(data) * 3.3 / 4096 - 1.633) * 15 / 0.625 * esFactor[locNum]
    return __ac2dc(data, msT, msRate)


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
    pulse = cn.bConfig['mb'][phaseLetter[phase]]['trip']['pulse']
    return (np.array(data) - pulse * 2) * 360 / pulse * 4


# 储能
def to_es_cur(data, phase: int) -> np.ndarray:
    """ 转直流电流幅值
    param
        data: 数据
        phase: 相数
    return
        []
    """
    data = (np.array(data) * 3.3 / 4096 - 1.633) * 15 / 0.625 * esFactor[phase]
    return __ac2dc(data, esT, esRate)


def to_es_spring(data, isAct) -> tuple[np.ndarray, np.ndarray]:
    """ 转弹簧压力值
    param
        data: 数据
        isAct: 是否动作
    return
        ([分], [合])
    """
    data = (np.array(data) / 4096 * 3.3) / 66 * 1000 * 1.9445
    if isAct:
        esLen = esActLen
    else:
        esLen = esNoLen
    return data[0: esLen], data[esLen: esLen * 2]


# 局放
def to_pd(data) -> np.ndarray:
    """ 转局放幅值
    param
        data: 数据
    return
        []
    """
    # 范围限制
    data = 5 - (5 * np.array(data)) / 2048
    data = 10 * np.log10(data ** 2 / 50 * 1000 + 1e-7)
    data = np.where(data < minSet, minSet, data)
    data = np.where(data > maxSet, maxSet, data)
    return data


# 触头 - 视频
def to_econtact_light(data) -> list:
    """ 转正确视频数组
    param
        data: 数据
    return
        []
    """
    # 下位机bug
    return data[:4] + data[7:]


# 触头 - 红外
def to_econtact_infrared(data) -> list:
    """ 转红外数据
    param
        data: 数据
    return
        []
    """
    # 帧尾去除 + 字符串二进制->真实二进制->实际数据
    data = binascii.b2a_hex(data)[:-16]
    return [int(data[i + 2:i + 4] + data[i:i + 2], 16) / 100
            for i in range(0, len(data), 4)]


def __ac2dc(data, T, rate) -> np.ndarray:
    """ 交流转直流
    param
        data: 数据
        T: 周期
        rate: 采样率
    """
    dotNum = int(T * rate * 10 ** 3)
    return np.array(
        [np.sqrt(
            np.sum(
                np.power(data[i:i + dotNum], 2) / dotNum
            )
        )
            for i in range(len(data) - dotNum)])
