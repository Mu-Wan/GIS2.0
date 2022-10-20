"""
机械特性-隔离开关模块
"""
from input.read_module import read_ms_file
from algo.utils import *
import algo.curve_utils as cu
from namespace import constant as cn
from namespace import algo_param as ap

import numpy as np
import socket
import time
from typing import Iterable

opKindName = ['分', '合', '异常']
maxCur = cn.eConfig['ms']['cur']['max']
msRate = cn.bConfig['ms']['cur']['rate']


def ms1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有机械特性-隔离开关文件
    param
    return
        OutData, ......
    """
    for sData in read_ms_file():
        out = __handle_one_ms(sData)
        if out:  # 动作时才产出
            yield __handle_one_ms(sData)


def __handle_one_ms(sensorData) -> OutData or None:
    """ 处理单个机械特性-隔离开关文件的数据
    param
        sensorData: 数据
    return
        OutData or None
    """
    cur, switch = sensorData.data
    # 算法处理
    outDict = {'action_type': '',
               'open_time': 0,
               'close_time': 0,
               'current_duration': 0,
               'maximum_operating_current': 0,
               'average_operating_current': 0,
               'filename': sensorData.fileName,
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    # 电流找点
    beginDots, _ = cu.find_turn_dot(cur, *ap.msFindBegin)
    _, stopDots = cu.find_turn_dot(cur, *ap.msFindEnd)
    curBegin = beginDots.up
    curStop = stopDots.down
    curTime = round((curStop - curBegin) * (1 / msRate), 2)
    # 动作
    switchL2H, switchH2L = cu.rect_wave_edge(switch[:-100])
    if switchL2H or switchH2L:
        opKind = 2
        if switchL2H:  # 上升沿 = 合
            opKind = 1
            outDict['close_time'] = curTime
            outDict['current_duration'] = outDict['close_time']
        elif switchH2L:  # 下降沿 = 分
            opKind = 0
            outDict['open_time'] = curTime
            outDict['current_duration'] = outDict['open_time']
        outDict['maximum_operating_current'] = round(np.max(cur), 2)
        outDict['average_operating_current'] = round(
            np.average(cur[curBegin:curStop]),
            2)
        outDict['action_type'] = opKindName[opKind]
        # 曲线存储
        save_curve({'cur': cur, 'switch': switch}, sensorData.fileName)
        # 通知主控
        __notify_shoot()
        # 异常处理
        if outDict['maximum_operating_current'] > maxCur:
            set_state_exc(outDict, 80, '电机电流异常')
        return OutData(sensorData, outDict)
    # 不动作
    else:
        return None


# 开线程, 不然卡进程
def __notify_shoot():
    """ 通知主控拍照
    param
    return
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('192.168.1.2', 6667))
            for _ in range(3):
                time.sleep(3)
                s.send(b'\xeb\x90\xeb\x90\x09\x00\x09\x00\x96')
            s.close()
    except Exception as e:
        print(e)


def __draw_test(cur, curBegin, curStop, switch, switchH2L, switchL2H):
    """ 绘制测试
    param
        cur: 电流数据
        curBegin: 电流抬升点
        curStop: 电流截止点
        switch: 辅助开关数据
        switchH2L: 下降沿
        switchL2H: 上升沿
    return
    """
    from matplotlib import pyplot as plt
    plt.subplot(211)
    plt.plot(range(len(cur)), cur)
    plt.scatter(curBegin, cur[curBegin])
    plt.scatter(curStop, cur[curStop])
    plt.subplot(212)
    plt.plot(range(len(switch)), switch)
    for dot in switchL2H:
        plt.scatter(dot, switch[dot])
    for dot in switchH2L:
        plt.scatter(dot, switch[dot])
    plt.show()
