"""
曲线处理的数学方法
"""
from namespace import algo_param as ap

from collections import namedtuple
import numpy as np
import scipy.signal as signal

s2Change = namedtuple("s2Change", ["up", "down"])
c2Steady = namedtuple("c2Steady", ["up", "down"])


def wave_smooth(data, winCount=ap.winCount) -> np.ndarray:
    """ 滤波
    param
        data: 数据
        winCount: 滑动窗口数目
    return
        []
    """
    # 中值
    medData = signal.medfilt(data, 11)
    # 滑动平均值
    winLen = int(len(data) / winCount) + 1
    window = np.ones(winLen) / float(winLen)
    return np.array(np.convolve(medData, window, 'same'))


def trip_wave_smooth(data) -> np.ndarray:
    """ 行程滤波
    param
        data: 数据
    return
        []
    """
    # sg滤波
    winLen = int(len(data) / 20)
    if winLen % 2 == 0:
        winLen += 1
    smoothData = signal.savgol_filter(data, winLen, 5)
    # 中值滤波
    return np.array(signal.medfilt(smoothData, winLen))


def find_base_value(data, curKind) -> int:
    """ 找基准值
    param
        data: 原始数据
        curKind: 曲线类型
    return
        水平偏移
    """
    smoothData = wave_smooth(data)
    toChangeDot, toSteadyDot = [], []
    if curKind == "close":
        toChangeDot, toSteadyDot = find_turn_dot(smoothData, *ap.closeCurFind)
    elif curKind == "sep":
        toChangeDot, toSteadyDot = find_turn_dot(smoothData, *ap.sepCurFind)
    if toChangeDot[0] != 0 and toSteadyDot[-1] != 0:
        begin, end = toChangeDot[0], toSteadyDot[-1]
    else:
        begin, end = 0, 0
    baseData = np.hstack((smoothData[:begin], smoothData[end:]))
    baseData = (np.round(baseData, 4) * 10000).astype('int64')
    return np.argmax(np.bincount(baseData)) / 10000


def rect_wave_edge(data) -> tuple[list, list]:
    """ 矩形波找沿
    param
        data: 数据
    return
        ([矩形波升沿], [矩形波降沿])
    """
    high2Low, low2High = [], []
    y = np.array(data)
    x = np.arange(0, len(y))
    # 判定斜率
    df = np.diff(y) / np.diff(x)
    detH = np.max(y) - np.min(y)
    okH = detH / 10
    # 去除同升/同降抖动点
    shakeLen = 30
    nearDot = 0
    allH2L = np.where(df < -okH)[0].tolist()
    for dot in allH2L:
        if (dot - nearDot) > shakeLen:
            high2Low.append(dot)
        nearDot = dot
    allL2H = np.where(df > okH)[0].tolist()
    for dot in allL2H:
        if (dot - nearDot) > shakeLen:
            low2High.append(dot)
        nearDot = dot
    # 去除附近区域内的抖动
    for h2l in high2Low:
        for l2h in low2High:
            if abs(h2l - l2h) < shakeLen:  # 去掉后面的
                if h2l > l2h:
                    high2Low.remove(h2l)
                else:
                    low2High.remove(l2h)
    return low2High, high2Low


def find_turn_dot(data, space, cycle, oneDet, totalDet) -> tuple[s2Change, c2Steady]:
    """ 曲线找抬升点 / 下降点
    param
        data: 数据
        space: 间隔点数
        cycle: 循环判断次数
        oneDet: 每次上升/下降高度
        totalDet: 整体上升/下降高度
    return
        ( (开始上升,开始下降) , (上升至平缓,下降至平缓) )
    """
    smoothData = wave_smooth(data)
    s2Up, s2Down = __find_change_dot(
        smoothData, space, cycle, oneDet, totalDet)
    up2S, down2S = __find_steady_dot(
        smoothData, space, cycle, oneDet, totalDet)
    return s2Change(s2Up, s2Down), c2Steady(up2S, down2S)


def __find_change_dot(smoothData, space, cycle, oneDet, totalDet, allowNum=20) -> tuple[int, int]:
    """ 获取第一个连续抬升 / 下降的点
    param
        smoothData: 滤波后的数据
        space: 间隔几个点进行比较
        cycle: 循环判断几次
        oneDet: 每次上升/下降高度
        totalDet: 整体上升/下降高度
        allowNum: 允许偏差点数
    return
        (上升,下降)
    """
    s2Up, s2Down = 0, 0
    i, upDone, downDone = 0, False, False
    allowNum = int(cycle / allowNum) + 1
    while i < len(smoothData) - cycle * space:
        delta = smoothData[i + 1:i + 1 + cycle * space: space] - \
                smoothData[i:i + cycle * space: space]
        # 容错但不是第一个
        if not upDone and (delta[delta > oneDet].size >= cycle - allowNum and delta[0] > oneDet) \
                and abs(smoothData[i + cycle * space] - smoothData[i]) > max(abs(smoothData)) * totalDet:
            s2Up = i + 1
            upDone = True
        if not downDone and (delta[delta < -oneDet].size >= cycle - allowNum and delta[0] < -oneDet) \
                and abs(smoothData[i + cycle * space] - smoothData[i]) > max(abs(smoothData)) * totalDet:
            s2Down = i
            downDone = True
        if upDone and downDone:
            break
        i += 1
    return s2Up, s2Down


def __find_steady_dot(smoothData, space, cycle, oneDet, totalDet, allowNum=20) -> tuple[int, int]:
    """ 获取第一个平缓的点
    param
        smoothData: 滤波后的数据
        space: 间隔几个点进行比较
        cycle: 循环判断几次
        oneDet: 每次上升/下降高度
        totalDet: 整体上升/下降高度
        allowNum: 允许几个点偏差
    return
        (上升平缓,下降平缓)
    """
    up2S, down2S = 0, 0
    i, upDone, downDone = len(smoothData) - 1, False, False
    allowNum = int(cycle / allowNum) + 1
    while i > cycle * space:
        delta = smoothData[i + 1 - cycle * space:i + 1: space] - \
                smoothData[i - cycle * space:i: space]
        # 容错但不是最后一个
        if not upDone and (delta[delta > oneDet].size >= cycle - allowNum and delta[-1] > oneDet):
            up2S = i
            upDone = True
        if not downDone and (delta[delta < -oneDet].size >= cycle - allowNum and delta[-1] < -oneDet) \
                and abs(smoothData[i - cycle * space] - smoothData[i]) > max(abs(smoothData)) * totalDet:
            down2S = i
            downDone = True
        if upDone and downDone:
            break
        i -= 1
    return up2S, down2S
