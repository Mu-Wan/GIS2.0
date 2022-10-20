"""
储能模块
"""
from input.read_module import read_es_file
from input.data_parse import esNoLen
from algo.utils import *
import algo.curve_utils as cu
from namespace import constant as cn
from namespace import algo_param as ap

import numpy as np
from typing import Iterable

springCloseMax = cn.eConfig['es']['spring']['closeMax']
curMax = cn.eConfig['es']['cur']['max']
sampleT = 1 / cn.bConfig['es']['base']['rate']


def es1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有储能文件
    param
        data: 数据
    return
        OutData, ......
    """
    # (spring, cur)
    # spring.data = [[分],[合]]
    for sData, cData in read_es_file():
        # 动作
        if len(sData.data[0]) > esNoLen:
            yield __handle_one_act(sData, cData)
        # 实时
        else:
            yield __handle_one_norm(sData)


def __handle_one_norm(springData) -> OutData:
    """ 处理非动作储能文件的数据
    param
        springData: 弹簧数据
    return
        OutData
    """
    splitData, closeData = springData.data
    # 算法处理
    outDict = {'split_spring_pressure': round(np.average(splitData), 2),
               'closing_spring_pressure': round(np.average(closeData), 2),
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    return OutData(springData, outDict)


def __handle_one_act(springData, curData) -> OutData:
    """ 处理动作储能文件的数据
    param
        springData: 弹簧数据
        curData: 电流数据
    return
        OutData
    """
    splitData, closeData = springData.data
    # 算法处理
    outDict = {'current_energy_storage_motor': 0,
               'starting_current': 0,
               'start_time': 0,
               'energy_storage_time': 0,
               'number_energy_storage': 0,
               'split_spring_pressure_max': round(np.max(splitData), 2),
               'closing_spring_pressure_max': round(np.max(closeData), 2),
               'filename': springData.fileName,
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    # 储能次数: 等数据库做完返回来补充
    curveData = {'spring': {'split': splitData, 'close': closeData},
                 'cur': []}
    # 合闸
    if curData:
        __handle_close(curData.data, outDict)
        curveData['cur'] = curData
    # 曲线存储
    save_curve(curveData, springData.fileName)
    # 异常判断
    if outDict['starting_current'] > curMax:
        set_state_exc(outDict, 80, '电机电流异常')
    if outDict['closing_spring_pressure_max'] < springCloseMax:
        set_state_exc(outDict, 80, '储能异常')
    return OutData(springData, outDict)


def __handle_close(curData, outDict):
    """ 处理合闸
    param
        curData: 电流数据
        outDict: 数据库字典
    return
    """
    curBeginDots, _ = cu.find_turn_dot(curData, *ap.esFindBegin)
    _, curStopDots = cu.find_turn_dot(curData, *ap.esFindEnd)
    curBegin = curBeginDots.up
    curStop = curStopDots.down
    curMidLen = curStop - curBegin
    defineBegin = int(curBegin + curMidLen * 0.2)
    defineEnd = int(curBegin + curMidLen * 0.9)
    outDict['current_energy_storage_motor'] = round(
        np.average(curData[defineBegin:defineEnd]), 2)
    outDict['starting_current'] = round(np.max(curData), 2)
    outDict['start_time'] = round(curBegin * sampleT, 2)
    outDict['energy_storage_time'] = round(curStop - curBegin, 2)
    # __draw_test(curData, curBegin, curStop)


def __draw_test(curData, curBegin, curStop):
    """ 绘制测试
    param
        curData: 电流数据
        curBegin: 电流抬升点
        curStop: 电流截止点
    return
    """
    from matplotlib import pyplot as plt
    plt.figure(figsize=(15, 4.8))
    plt.plot(range(len(curData)), curData)
    plt.scatter(curBegin, curData[curBegin], c='red')
    plt.scatter(curStop, curData[curStop], c='blue')
    plt.show()
