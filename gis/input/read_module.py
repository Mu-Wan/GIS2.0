"""
读取文件 -> 调用解析文件 -> 调用转换数据 -> 返回模块所需数据
"""
import numpy as np

import input.utils as iu
from input import data_parse as dp, parse_file as pf
from namespace import file_path, constant as cn
import copy
import os
import re
import time
from typing import List, Iterable


def read_gas_file() -> Iterable[iu.SensorData]:
    """ 气体
    param
    return
        SensorData, ...
    """
    module = cn.Gas
    for file in __get_files(module):
        location = __get_loc_str(file, module)
        yield pf.parse_485(file, module, location)


def read_env_file() -> Iterable[iu.SensorData]:
    """ 环境
    param
    return
        SensorData, ...
    """
    module = cn.Env
    for file in __get_files(module):
        location = __get_loc_str(file, module)
        sData = pf.parse_485(file, module, location)
        sData.data = dp.to_env(sData.data)
        yield sData


def read_vib_file() -> Iterable[iu.SensorData]:
    """ 振动
    param
    return
        # 母线振动时.data = [[x],[y],[z]]
        # 断路器振动.data = []
        SensorData, ...
    """
    module = cn.Vib
    for file in __get_files(module):
        location = __get_loc_str(file, module)
        sData = pf.parse_485(file, module, location)
        if "母线" in location:
            axisLen = cn.bConfig['vib']['bus']['dotCount'] - 1
            sData.data = dp.to_bus_vib(sData.data)
            sData.data = [sData.data[axisLen * i: axisLen * (i + 1)]
                          for i in range(3)]
        else:
            sData.data = dp.to_mb_vib(sData.data)
        yield sData


def read_ms_file() -> Iterable[iu.SensorData]:
    """ 机械特性(隔离开关): 差分每相单独产出
    param
    return
        # [[cur], [switch]]
        SensorData, ...
    """
    module = cn.Ms
    for file in __get_files(module):
        location = __get_loc_str(file, module)
        sData = pf.parse_485(file, module, location)
        data = copy.deepcopy(sData.data)
        # 拆分3个位置
        msLen = dp.msLen
        for i in range(3):
            sData.location = location[i]
            cur = dp.to_ms_cur(data[i * msLen: (i + 1) * msLen], i)
            switch = np.array(data[(i + 3) * msLen:(i + 4) * msLen])
            sData.data = [cur, switch]
            yield sData


def read_mb_file() -> Iterable[dict[str:iu.SensorData]]:
    """ 机械特性(断路器)
    param
    return
        { 'cur': [SensorData x 3], 'trip': [SensorData x 3]}, , ...
    """
    module = cn.Mb
    location = cn.mbCode2Loc
    allowTime = cn.bConfig['mb']['base']['allowTime'] * (10 ** 6)
    waitTime = cn.bConfig['mb']['base']['waitTime']
    waitCount = int(waitTime / cn.readInterval)
    for fGroup in __divide_group(__get_files(module), 6, allowTime):
        if len(fGroup) == 6:
            yield __mb_parse(fGroup, module, location)
        elif len(fGroup) < 6:
            # 已标记
            if "wait" in fGroup[0]:
                # 已等完: 补全处理
                if __wait_judge(fGroup):
                    yield __mb_complement(fGroup, module, location)
                # 未等完: 跳过 继续等待
                else:
                    continue
            # 未标记: 标记
            else:
                __wait_mark(fGroup, waitCount)


def __mb_complement(fGroup, module, location) -> dict[str:iu.SensorData]:
    """ 补全数据
    param
        fGroup: 缺相的文件组[]
        module: 模块名
        location: 监测位置
    return
        { 'cur': [SensorData x 3], 'trip': [SensorData x 3]}
    """
    curPre, tripPre = ['0x' + _ for _ in cn.nameToSection[cn.Mb]]
    sDataList = {'cur': [], 'trip': []}
    # 模板数据
    timeList = fGroup[0].split('_')[1].split('-')[:8]
    num = 1
    # 补全
    prefixGroup = [__get_prefix(f) for f in fGroup]
    for i in range(3):
        cur = curPre + f'{i}'
        trip = tripPre + f'{i}'
        # 电流缺相
        if cur not in prefixGroup:
            fileName = cur + fGroup[0][4:]
            sData = iu.SensorData(fileName, module, location, num, timeList,
                                  [0 for _ in range(dp.mbCSLen)])
        # 电流正常
        else:
            f = fGroup[prefixGroup.index(cur)]
            sData = pf.parse_485(f, module, location)
            sData.data = dp.to_mb_cur(sData.data)
        sDataList['cur'].append(sData)
        # 行程缺相
        if trip not in prefixGroup:
            fileName = trip + fGroup[0][4:]
            sData = iu.SensorData(fileName, module, location, num, timeList,
                                  [0 for _ in range(dp.mbTripLen)])
        # 行程正常
        else:
            f = fGroup[prefixGroup.index(trip)]
            sData = pf.parse_485(f, module, location)
            sData.data = dp.to_mb_trip(sData.data, int(__get_loc(f)) % 3)
        sDataList['trip'].append(sData)
    return sDataList


def __mb_parse(fGroup, module, location) -> dict[str:iu.SensorData]:
    """ 解析三相文件
    param
        fGroup: [3 + 3]
        module: 模块名
        location: 监测位置
    return
        { 'cur': [SensorData x 3], 'trip': [SensorData x 3]}
    """
    sDataList = {'cur': [], 'trip': []}
    for i in range(0, 6):
        sData = pf.parse_485(fGroup[i], module, location)
        # 电流
        if i < 3:
            sData.data = dp.to_mb_cur(sData.data)
            sDataList['cur'].append(sData)
        # 行程
        else:
            sData.data = dp.to_mb_trip(sData.data, i % 3)
            sDataList['trip'].append(sData)
    return sDataList


def read_es_file() -> Iterable[tuple[iu.SensorData, iu.SensorData or None]]:
    """ 储能: 差分+合并每相单独产出
    param
    return
        # spring.data = [[分],[合]]
        # cur.data = []
        (spring, cur), ...
    """
    module = cn.Es
    allowTime = cn.bConfig['es']['base']['allowTime'] * (10 ** 6)
    waitTime = cn.bConfig['es']['base']['waitTime']
    waitCount = int(waitTime / cn.readInterval)
    for fGroup in __divide_group(__get_files(module), 4, allowTime):
        # 三相弹簧
        if len(fGroup) == 3:
            templateFile = fGroup[0]
            if os.path.getsize(file_path.binaryPath + templateFile) \
                    < dp.esNoActSize:  # 未动作、分闸: 直接处理
                for f in fGroup:
                    location = __get_loc_str(f, module)
                    sData = pf.parse_485(f, module, location)
                    sData.data = dp.to_es_spring(sData.data, False)
                    yield sData, None
            else:  # 合闸: 标记等待
                if 'wait' in templateFile:  # 已标记
                    # 已满足: 无此情况
                    if __wait_judge(fGroup):  # 仍缺文件 - 等完: 处理
                        for f in fGroup:
                            location = __get_loc_str(f, module)
                            sData = pf.parse_485(f, module, location)
                            sData.data = dp.to_es_spring(sData.data, True)
                            yield sData, None
                    else:  # 仍缺文件 - 未等完: 跳过
                        continue
                else:  # 未标记:
                    __wait_mark(fGroup, waitCount)
        # 三相弹簧 + 电流
        elif len(fGroup) == 4:
            for onePhase in __es_close_parse(fGroup, module):
                yield onePhase


def __es_close_parse(fGroup, module) -> List[tuple[iu.SensorData, iu.SensorData]]:
    """ 合闸解析
    param
        fGroup: 完整文件组[1+3]
        module: 模块
    return
        # spring.data = [[分],[合]]
        # cur.data = []
        [(spring, cur) x3 ]
    """
    curPre, springPre = ['0x' + _ for _ in cn.nameToSection[module]]
    curLen = dp.esCurLen
    sDataList, curList = [], []
    # 电流先处理
    curData = None
    for f in fGroup:
        if curPre in f:
            location = __get_loc_str(f, module)
            curData = pf.parse_485(f, module, location)
            # 拆分三相
            curList += [dp.to_es_cur(
                curData.data[curLen * i: curLen * (i + 1)], i)
                for i in range(3)]
    # 弹簧
    for f in fGroup:
        if springPre in f:
            phase = int(__get_loc(f)) % 3
            location = __get_loc_str(f, module)
            sData = pf.parse_485(f, module, location)
            sData.data = dp.to_es_spring(sData.data, True)
            curData.data = curList[phase]
            sDataList.append((sData, curData))
    return sDataList


def read_pd_file() -> Iterable[iu.SensorData]:
    """ 局放
    param
    return
        SensorData, ...
    """
    module = cn.Pd
    for f in __get_files(module):
        location = __get_loc_str(f, module)
        sData = pf.parse_pd(f, module, location)
        sData.data = dp.to_pd(sData.data)
        yield sData


def read_econtact_file() -> Iterable[iu.SensorData]:
    """ 红外视频
    param
    return
        # data = [[pic], [red]]
        SensorData, ...
    """
    module = cn.eContact
    for file in __get_files(module):
        locNum = int(__get_loc(file), 16)
        location = cn.nameToLocDict[module][str(int(locNum / 3))]  # 特殊
        num = locNum % 3
        sData = pf.parse_touch(file, module, location, num)
        picData, redData = sData.data
        sData.data = [dp.to_econtact_light(picData),
                      dp.to_econtact_infrared(redData)]
        yield sData


def __get_files(moduleName) -> List[str]:
    """ 获取模块的文件
    param
        moduleName: 模块名
    return
        ["0x00_-----", ...]
    """
    section = cn.nameToSection[moduleName]
    return [f
            for f in os.listdir(file_path.binaryPath)
            if __get_section(f) in section and f.lower().find('done') == -1]


def __get_section(file) -> str:
    """ 返回文件名里的区间码
    param
        file: 文件名
    return
        str
    """
    return file[2].lower()


def __get_loc(file) -> str:
    """ 返回文件名里的监测位置码
    param
        file: 文件名
    return
        str
    """
    return file[3]


def __get_prefix(file) -> str:
    """ 返回文件名里的前缀
    param
        file: 文件名
    return
        str
    """
    return file[:4]


def __get_loc_str(file, module) -> str:
    """ 返回location
    param
        file: 文件名
        module: 模块名
    return
        str
    """
    return cn.nameToLocDict[module][__get_loc(file)]


def __get_time_stamp(timeStr) -> int:
    """ 转换为时间戳
    param
        timeStr: 时间字符串
    return
        int
    """
    strList = timeStr.split('_')[1].split('-')
    timeStr = '-'.join(strList[:6])
    timeStr = int(time.mktime(time.strptime(timeStr, "%Y-%m-%d-%H-%M-%S"))) * 10 ** 6
    return timeStr + int(strList[6]) * (10 ** 3) + int(strList[7])


def __divide_group(fileList, count, perTime) -> List[List]:
    """ 同一次动作文件分组 (时间相近)
    param
        fileList: 文件组
        count: 文件数量
        perTime: 允许时间
    return
        [[一组] , [] ]
    """
    # 排序 [[time,''], ]
    fileList = [(__get_time_stamp(f), f) for f in fileList]
    fileList.sort(key=lambda x: x[0])
    # 允许时间内成组 [x count]
    groupList = []
    while len(fileList) > 0:
        tempGroup = [fileList[0][1]]
        endIndex = count
        for i in range(1, count):
            # 文件耗尽: 结束
            if i >= len(fileList):
                endIndex = i
                break
            # 时间相近: 添加
            elif fileList[i][0] - fileList[0][0] <= perTime:
                tempGroup.append(fileList[i][1])
            # 无关文件: 结束
            else:
                endIndex = i
                break
        tempGroup.sort()
        groupList.append(tempGroup)
        del fileList[: endIndex]
    return groupList


def __wait_mark(fGroup, count):
    """ 标记等待
    param
        fGroup: 缺相的文件组
        count: 等待次数
    return
    """
    for f in fGroup:
        fPath = file_path.binaryPath + f
        os.rename(fPath, fPath + f'-{count}wait')


def __wait_judge(fGroup) -> bool:
    """ 判断及继续等待
    param
        fGroup: 缺相的文件组
    return
        bool
    """
    reStr = re.compile(r"-\dwait", re.I)
    templateFile = fGroup[0]
    matchStr = re.search(reStr, templateFile).group()
    count = int(matchStr[1])
    # 已经等待结束
    if count == 0:
        return True
    # 继续等待 并更名
    else:
        newStr = f"-{count - 1}" + matchStr[2:]
        for f in fGroup:
            fPath = file_path.binaryPath + f
            newFPath = file_path.binaryPath + re.sub(reStr, newStr, f)
            os.rename(fPath, newFPath)
        return False
