"""
振动模块
"""
from input.read_module import read_vib_file
from algo.utils import *
from namespace import constant as cn
import numpy as np
from PyEMD import EMD
from typing import Iterable

# 大部分耗时在于emd
breakerRate = cn.bConfig['vib']['breaker']['rate'] * 1000
busRate = cn.bConfig['vib']['bus']['rate'] * 1000


def vib1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有振动文件
    param
    return
        OutData, ......
    """
    for sData in read_vib_file():
        yield __handle_one_vib(sData)


def __handle_one_vib(sensorData) -> OutData:
    """ 处理单个振动文件的数据
    param
        sensorData: 数据
    return
        OutData
    """
    # 断路器: data = []
    # 母线: data = [[x],[y],[z]]
    data = sensorData.data
    # 算法处理
    outDict = {'acceleration': [],  # 单轴被修改为int
               'frequency': [],
               'IMF1_word': [],
               'IMF2_word': [],
               'IMF3_word': [],
               'filename': sensorData.fileName,
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    if len(data) == 3:
        # 1.母线
        __handle_bus_vib(data, outDict, sensorData.fileName)
    else:
        # 2.断路器
        __handle_breaker_vib(data, outDict, sensorData.fileName)
    # 异常处理
    return OutData(sensorData, outDict)


def __handle_breaker_vib(data, outDict, fileName):
    """ 断路器单轴振动
    param
        data: 数据
        outDict: 数据库记录
        fileName: 曲线存储
    return
    """
    data = np.array(data)
    # 数据库
    outDict['acceleration'] = round(max(np.abs(data)), 4)
    outDict['frequency'] = breakerRate
    imfsED = __get_imfs(data, False)
    outDict['IMF1_word'] = imfsED[0]
    outDict['IMF2_word'] = imfsED[1]
    outDict['IMF3_word'] = imfsED[2]
    # 曲线
    fftAbs, fftAngle = __fft(data)
    curvaData = {'x': {'data': list(np.around(data, 4)),
                       'abs': list(np.around(fftAbs, 4)),
                       'angle': list(np.around(fftAngle, 4))},
                 'y': {},
                 'z': {}}
    save_curve(curvaData, fileName)


def __handle_bus_vib(dataList, outDict, fileName):
    """ 母线三轴振动
    param
        dataList: 数据组
        outDict: 数据库记录
        fileName: 曲线存储
    return
    """
    curvaData = {'x': {}, 'y': {}, 'z': {}}
    i2Letter = ['x', 'y', 'z']
    for i, data in enumerate(dataList):
        data = np.array(data)
        # 数据库
        outDict['acceleration'].append(round(max(np.abs(data)), 4))
        outDict['frequency'].append(busRate)
        imfsED = __get_imfs(data, False)
        outDict['IMF1_word'].append(imfsED[0])
        outDict['IMF2_word'].append(imfsED[1])
        outDict['IMF3_word'].append(imfsED[2])
        # 曲线
        fftAbs, fftAngle = __fft(data)
        curvaData[i2Letter[i]] = {'data': list(np.around(data, 4)),
                                  'abs': list(np.around(fftAbs, 4)),
                                  'angle': list(np.around(fftAngle, 4))}
    save_curve(curvaData, fileName)


def __fft(data) -> tuple:
    """ fft变换
    param
        data:
    return
        [abs], [angle]
    """
    dataFft = np.fft.fft(data)
    fftAbs = np.abs(dataFft) / len(data)
    fftAngle = np.angle(dataFft) / np.pi * 180
    halfLen = int(len(data) / 2)
    return fftAbs[1: halfLen], fftAngle[1: halfLen]


def __get_imfs(data, isBus):
    """ EMD分解
    param
        data: 数据
        isBus: 是否母线振动
    return
        [imf的能量距]
    """
    # 采样周期
    if isBus:
        rate = busRate
    else:
        rate = breakerRate
    T = 1 / rate
    # emd分解
    emd = EMD()
    emd.emd(data)
    imfs, res = emd.get_imfs_and_residue()
    # 能量距计算
    imfsED = []
    for imf in imfs[:3]:
        imfED = 0
        for j, dot in enumerate(imf):
            imfED += j * T * ((dot * j * T) ** 2)
        imfsED.append(round(imfED, 3))
    return imfsED
