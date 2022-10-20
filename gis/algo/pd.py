"""
局放模块
"""
from input.read_module import read_pd_file
from algo.utils import *
from namespace import constant as cn
import time
import math
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cm

Tc = cn.bConfig['pd']['base']['tc'] * (10 ** 6)
Ts = 1 / (cn.bConfig['pd']['base']['tc'] * (10 ** 6))
minSet = cn.bConfig['pd']['base']['minSet']
maxSet = cn.bConfig['pd']['base']['maxSet']


# 这里需要结合读取修改 为读一个监测位置
def pd1time() -> OutData or None:
    """ 处理一次放电周期的文件
    param
    return
    """
    # 持续读, 直到不再上传
    isFir, hasFile = True, False
    firTimeStamp = 0
    templateData = None
    dataList = []  # 全局积累数据 eg.[data, ...]
    timeStampList = []  # 全局积累数据 eg.[time, ...]
    while True:
        needWait = False
        for sData in read_pd_file():
            needWait = True  # 仍有数据
            if isFir:  # 一次放电周期的起始时间
                isFir, hasFile = False, True
                firTimeStamp = sData.get_time_stamp()
                templateData = SensorData(sData.fileName, sData.module, sData.module, sData.num, sData.timeList, [])
            dataList.append(sData.data)
            timeStampList.append(sData.get_time_stamp())
        if not needWait:  # 不再生成数据
            break
        time.sleep(0.5)
    if hasFile:
        return __handle_statistics(dataList, timeStampList, templateData, firTimeStamp)
    else:
        return None


def __handle_statistics(dataList, timeStampList, sensorData, firTimeStamp) -> OutData:
    """ 处理统计量
    param
        dataList: 所有数据
        timeStampList: 所有时间戳差
        sensorData: 模板
        firTimeStamp: 初次时间
    return
        OutData
    """
    prpdName = 'prpd_' + sensorData.fileName + '.png'
    prpsName = 'prps_' + sensorData.fileName + '.png'
    # 转换量值
    detTSList, phaseList, pulseAmpList, pulsePhaseList = [], [], [], []
    for i in range(len(dataList)):
        __handle_one_pd(firTimeStamp, dataList[i], timeStampList[i], detTSList, phaseList, pulseAmpList, pulsePhaseList)
    # 算法处理
    outDict = {'partial_discharge_amplitude':
                   round(max(pulseAmpList), 2),
               'partial_discharge_power':
                   round(10 ** (max(pulseAmpList) / 10), 2),
               'partial_discharge_frequency':
                   abs(round(len(detTSList) / (detTSList[-1] / 10 ** 6), 1)),
               'number_of_pulses':
                   len(pulseAmpList),
               'phase': '',
               'discharge_type': '',
               'prpd_filename': prpdName,
               'prps_filename': prpsName,
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    __draw_prpd(prpdName, pulseAmpList, pulsePhaseList)
    __draw_prps(prpsName, dataList, detTSList, phaseList)
    return OutData(sensorData, outDict)


def __draw_prpd(prpdName, pulseAmpList, pulsePhaseList):
    """ 绘制PRPD
    param
        prpdName: 文件名
        pulseAmpList: 脉冲幅值
        pulsePhaseList: 脉冲相位
    return
    """
    plt.figure(figsize=(8, 6))
    plt.ylabel('amplitude / dBm')
    plt.ylim(0, 20)
    plt.yticks([0, 10, 20])
    plt.xlim(0, 360)
    plt.xticks([0, 90, 180, 270, 360])
    plt.xlabel('phase / °')
    x = np.arange(0, 361)
    sinY = np.sin((2 * math.pi / 360) * x) * 10 + 10
    horY = [10 for _ in range(361)]
    plt.plot(x, sinY, linewidth=1, alpha=0.3)
    plt.plot(x, horY, color='black', linewidth=0.1)
    plt.scatter(pulsePhaseList, pulseAmpList, s=3, c='red', alpha=0.2)
    plt.savefig(outputPath + prpdName)


def __draw_prps(prpsName, dataList, detTSList, phaseList):
    """ 绘制PRPS
    param
        prpsName: 文件名
        dataList: 全部数据
        detTSList: 时间戳差
        phaseList: 相对相位
    return
    """
    fig = plt.figure(figsize=(6, 6.2))
    fig.subplots_adjust(left=0.03, right=0.91, bottom=-0.05, top=1.1)
    ax = plt.axes(projection='3d')
    x = np.arange(0, 361)
    # 补线
    insertLen = 75
    detTSList = np.array(detTSList) / 10 ** 6
    moreTSList = insertLen / max(detTSList) * detTSList
    copyN = insertLen // len(detTSList)
    if copyN == 0:
        copyN = 1
    moreTSList = [moreTSList[i // copyN] +
                  (moreTSList[(i // copyN) + 1] -
                   moreTSList[i // copyN]) * (i % copyN) / copyN
                  for i in range((len(moreTSList) - 1) * copyN)]
    X, Y = np.meshgrid(x, moreTSList)
    Z = []
    minData = np.min(dataList)
    # 线补点
    for i in range(len(moreTSList) // copyN):
        beginDot = phaseList[i]
        needDot = 360 - beginDot
        if needDot >= len(dataList[i]):
            z = [minSet for _ in range(beginDot)] + \
                (dataList[i] - minData).tolist() + \
                [minSet for _ in range(361 - len(dataList[i]) - beginDot)]
        else:
            z = [minSet
                 if temp < beginDot
                 else dataList[i][temp - beginDot]
                 for temp in range(361)]
        z = np.array(z) - minSet
        for j in range(copyN):
            Z.append((z * (j + 1) / copyN))
    X, Y, Z = X.flatten(), Y.flatten(), np.array(Z).flatten()
    offset = Z + np.abs(Z.min())
    fracs = offset.astype(float) / offset.max()
    norm = colors.Normalize(fracs.min(), fracs.max())
    colorValues = cm.jet(norm(fracs.tolist()))
    ax.bar3d(X, Y, np.array([minSet for _ in range(len(X))]),
             dx=1, dy=insertLen / 360, dz=Z, color=colorValues)
    ax.set_xlabel('phase / °')
    ax.set_yticks([0, insertLen * 1 / 4, insertLen * 2 / 4, insertLen * 3 / 4, insertLen])
    yLabel = [round(i / 5 * detTSList[-1], 2) for i in range(5)]
    ax.set_yticklabels(yLabel)
    ax.set_ylabel('time / s')
    ax.set_zlabel('amplitude / dBm')
    plt.savefig(outputPath + prpsName)


def __handle_one_pd(firTimeStamp, data, timeStamp, detTSList, phaseList, pulseAmpList, pulsePhaseList):
    """ 处理单个局放文件的数据
    param
        firTimeStamp: 初次时间
        data: 数据
        timeStamp: 时间戳
        detTSList: 全局时间戳差
        phaseList: 全局相对时间戳
        pulseAmpList: 全局脉冲幅值
        pulsePhaseList: 全局脉冲相位
    return
    """
    detTimeStamp = timeStamp - firTimeStamp  # 文件时间戳差
    relativeStamp = __get_relative_stamp(detTimeStamp)
    detTSList.append(detTimeStamp)
    phaseList.append(int(relativeStamp / Tc * 360))  # 文件相位
    pulseAmpList.append(round(np.max(data), 2))  # 脉冲幅值
    pulsePhaseList.append(__get_pulse_phase(data, relativeStamp))  # 脉冲相位


def __get_relative_stamp(detTimeStamp) -> int:
    """ 获取该文件相对时间戳差
    param
        detT: 与初次文件的时差
    return
        int
    """
    TCount = math.floor(detTimeStamp / Tc)
    return detTimeStamp - TCount * Tc


def __get_pulse_phase(data, relativeStamp) -> int:
    """ 获取脉冲相位
    param
        data: 一次数据
        relativeStamp: 相对时间戳差
    return
        int
    """
    relativeStamp += np.argmax(data) * (Ts * 10 ** 6)
    return round(relativeStamp / Tc * 360, 2)
