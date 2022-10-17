"""
读取及处理 文件内容
"""
import copy
import re
# 跨目录调用: 路径添加
import sys
import inspect

sys.path.append(inspect.getfile(inspect.currentframe()))
from namespace import file_path, constant as cn
from input import parse_file, data_parse
# ...
import os
import time
from typing import List, Iterable


def read_gas_file() -> Iterable[parse_file.SensorData]:
    """ 气体
    param
    return
        SensorData, ...
    """
    module = cn.Gas
    for file in __get_files(module):
        location = cn.gasCode2Loc[file[3]]
        yield parse_file.parse_485(file, module, location)


def read_env_file() -> Iterable[parse_file.SensorData]:
    """ 环境
    param
    return
        SensorData, ...
    """
    module = cn.Env
    for file in __get_files(module):
        location = cn.envCode2Loc[file[3]]
        sData = parse_file.parse_485(file, module, location)
        sData.data = data_parse.to_env(sData.data)
        yield sData


def read_vib_file() -> Iterable[parse_file.SensorData]:
    """ 振动
    param
    return
        SensorData, ...
    """
    module = cn.Vib
    for file in __get_files(module):
        location = cn.vibCode2Loc[file[3]]
        sData = parse_file.parse_485(file, module, location)
        if "母线" in location:
            sData.data = data_parse.to_bus_vib(sData.data)
        else:
            sData.data = data_parse.to_mb_vib(sData.data)
        yield sData


def read_ms_file() -> Iterable[parse_file.SensorData]:
    """ 机械特性(隔离开关)
    param
    return
        SensorData, ...
    """
    module = cn.Ms
    for file in __get_files(module):
        location = cn.msCode2Loc[file[3]]
        sData = parse_file.parse_485(file, module, location)
        data = copy.deepcopy(sData.data)
        # 拆分3个位置
        msLen = data_parse.msLen
        for i in range(3):
            sData.location = location[i]
            sData.data = data_parse.to_ms_cur(
                data[i * msLen: (i + 1) * msLen], i)
            yield sData


def read_mb_file() -> Iterable[dict[str:parse_file.SensorData]]:
    """ 机械特性(断路器)
    param
    return
        { 'cur': [SensorData x 3], 'trip': [SensorData x 3]}, , ...
    """
    module = cn.Mb
    location = cn.mbCode2Loc
    allowTime = cn.config['mb']['base']['allowTime'] * (10 ** 6)
    waitTime = cn.config['mb']['base']['waitTime']
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


def __mb_divide_group(fileList) -> List[List]:
    """ 6文件分组
    param
        fileList: 文件组
    return
        [[一组] , [] ]
    """
    # 排序 [[time,''], ]
    fileList = [(__get_time_stamp(f), f) for f in fileList]
    fileList.sort(key=lambda x: x[0])
    # 允许时间内成组 [x6]
    groupList = []
    perTime = cn.config['mb']['base']['timeAllow'] * (10 ** 6)
    while len(fileList) > 0:
        tempGroup = [fileList[0][1]]
        endIndex = 6
        for i in range(1, 6):
            if i >= len(fileList):
                endIndex = i
                break
            elif fileList[i][0] - fileList[0][0] <= perTime:
                tempGroup.append(fileList[i][1])
            else:
                endIndex = i
                break
        tempGroup.sort()
        groupList.append(tempGroup)
        del fileList[: endIndex]
    return groupList


def __mb_complement(fGroup, module, location) -> dict[str:parse_file.SensorData]:
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
    prefixGroup = [f[:4] for f in fGroup]
    for i in range(3):
        cur = curPre + f'{i}'
        trip = tripPre + f'{i}'
        # 电流缺相
        if cur not in prefixGroup:
            sData = parse_file.SensorData(module, location, num, timeList,
                                          [0 for _ in range(data_parse.mbCSLen)])
        # 电流正常
        else:
            f = fGroup[prefixGroup.index(cur)]
            sData = parse_file.parse_485(f, module, location)
            sData.data = data_parse.to_mb_cur(sData.data)
        sDataList['cur'].append(sData)
        # 行程缺相
        if trip not in prefixGroup:
            sData = parse_file.SensorData(module, location, num, timeList,
                                          [0 for _ in range(data_parse.mbTripLen)])
        # 行程正常
        else:
            f = fGroup[prefixGroup.index(trip)]
            sData = parse_file.parse_485(f, module, location)
            sData.data = data_parse.to_mb_trip(sData.data, int(f[3]) % 3)
        sDataList['trip'].append(sData)
    return sDataList


def __mb_parse(fGroup, module, location) -> dict[str:parse_file.SensorData]:
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
        sData = parse_file.parse_485(fGroup[i], module, location)
        # 电流
        if i < 3:
            sData.data = data_parse.to_mb_cur(sData.data)
            sDataList['cur'].append(sData)
        # 行程
        else:
            sData.data = data_parse.to_mb_trip(sData.data, i % 3)
            sDataList['trip'].append(sData)
    return sDataList


def read_es_file() -> Iterable[dict[str:parse_file.SensorData]]:
    """ 储能
    param
    return
        {'cur': ,'spring': }, ...
    """
    module = cn.Es
    allowTime = cn.config['es']['base']['allowTime'] * (10 ** 6)
    waitTime = cn.config['es']['base']['waitTime']
    waitCount = int(waitTime / cn.readInterval)
    for fGroup in __divide_group(__get_files(module), 4, allowTime):
        # 三相弹簧
        if len(fGroup) == 3:
            templateFile = fGroup[0]
            # 未动作、分闸: 直接处理
            if os.path.getsize(file_path.binaryPath + templateFile) \
                    < data_parse.esNoActSize:
                for f in fGroup:
                    location = cn.esSpringCode2Loc[f[3]]
                    yield {'cur': [],
                           'spring': parse_file.parse_485(f, module, location)}
            # 合闸: 标记等待
            else:
                # 已标记
                if 'wait' in templateFile:
                    # 已满足: 无此情况
                    # 仍缺文件 - 等完: 处理
                    if __wait_judge(fGroup):
                        for f in fGroup:
                            location = cn.esSpringCode2Loc[f[3]]
                            yield {'cur': [],
                                   'spring': parse_file.parse_485(f, module, location)}
                    # 仍缺文件 - 未等完: 跳过
                    else:
                        continue
                # 未标记:
                else:
                    __wait_mark(fGroup, waitCount)
        # 三相弹簧 + 电流
        elif len(fGroup) == 4:
            for onePhase in __es_parse(fGroup, module):
                yield onePhase


def __es_parse(fGroup, module) -> List[dict[str:parse_file.SensorData]]:
    """ 合闸解析
    param
        fGroup: 完整文件组[1+3]
        module: 模块
    return
        [{'cur': , 'spring': } x3 ]
    """
    curPre, springPre = ['0x' + _ for _ in cn.nameToSection[module]]
    curLen = data_parse.esCurLen
    sDataList, curList = [], []
    # 电流先处理
    curData = None
    for f in fGroup:
        if curPre in f:
            location = cn.esSpringCode2Loc[f[3]]
            curData = parse_file.parse_485(f, module, location)
            # 拆分三相
            curList += [data_parse.to_es_cur(
                curData.data[curLen * i: curLen * (i + 1)], i)
                for i in range(3)]
    # 弹簧
    for f in fGroup:
        if springPre in f:
            phase = int(f[3]) % 3
            location = cn.esSpringCode2Loc[f[3]]
            sData = parse_file.parse_485(f, module, location)
            sData.data = data_parse.to_es_spring(sData.data)
            curData.data = curList[phase]
            sDataList.append({'cur': curData, 'spring': sData})
    return sDataList


def read_pd_file() -> Iterable[parse_file.SensorData]:
    """ 局放
    param
    return
        SensorData, ...
    """
    module = cn.Pd
    for f in __get_files(module):
        location = cn.pdCode2Loc[f[3]]
        yield parse_file.parse_pd(f, module, location)


def read_econtact_file() -> Iterable[parse_file.SensorData]:
    """ 红外视频
    param
    return
        SensorData, ...
    """
    module = cn.eContact
    for file in __get_files(module):
        location = int(file[3], 16) / 3
        num = int(file[3], 16) % 3
        yield parse_file.parse_touch(file, module, location, num)


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
            if f[2].lower() in section and f.lower().find('done') == -1]


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
    reStr = re.compile(r"\dwait", re.I)
    templateFile = fGroup[0]
    matchStr = re.search(reStr, templateFile).group()
    count = int(matchStr[0])
    # 已经等待结束
    if count == 0:
        return True
    # 继续等待 并更名
    else:
        newStr = f"{count - 1}" + matchStr[1:]
        for f in fGroup:
            fPath = file_path.binaryPath + f
            newFPath = file_path.binaryPath + re.sub(reStr, newStr, f)
            os.rename(fPath, newFPath)
        return False


if __name__ == '__main__':
    pass
    # for _ in read_gas_file():

    # for _ in read_env_file():

    # for _ in read_vib_file():

    # for _ in read_ms_file():

    # while True:
    #     for _ in read_mb_file():
    #         print(_)
    #         print(len(_['cur']))
    #         print(len(_['trip']))
    #     time.sleep(cn.readInterval)

    # while True:
    #     for _ in read_es_file():
    #         print(_)
    #     time.sleep(cn.readInterval)

    # for _ in read_pd_file():
    #     print(_)

    # for _ in read_econtact_file():
    #     print(_)
    #     print(len(_.data['pic']))
    #     print(len(_.data['red']))
