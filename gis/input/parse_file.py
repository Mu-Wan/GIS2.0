"""
解析 二进制数据
"""
from input import data_parse
from input.utils import SensorData
from namespace import file_path, constant as cn
import struct
import os
import shutil
import platform


def parse_485(fileName, module, location) -> SensorData:
    """ parse485
    param
        fileName: 文件名
        module: 模块
        location: 监测位置
    return
        SensorData
    """
    filePath = file_path.binaryPath + fileName
    donePath = filePath + 'Done'
    with open(filePath, 'rb') as file:
        # 头部
        dataHead = file.read(8)
        # 帧头
        biData = file.read(2 * 14)
        infoList = [struct.unpack("<h", biData[i:i + 2])[0]
                    for i in range(0, 28, 2)]
        # 余下 = 数据 + CRC(2) + 结尾(4)
        realData = file.read()[: -6]
        if module == cn.Gas:
            dataList = [struct.unpack("f", realData[i + 2:i + 4] + realData[i:i + 2])[0]
                        for i in range(0, len(realData), 4)]
        else:
            dataList = [struct.unpack("H", realData[i:i + 2])[0]
                        for i in range(0, len(realData), 2)]
    # 标记 与 移走
    os.rename(filePath, donePath)
    __remove_file(donePath)
    num = 1
    return SensorData(fileName, module, location, num, infoList[-8:], dataList)


def parse_touch(fileName, module, location, num) -> SensorData:
    """ 解析网口 - 红外视频
    param
        fileName: 文件名
        module: 模块
        location: 监测位置
        num: 相数
    return
        SensorData
    """
    filePath = file_path.binaryPath + fileName
    donePath = filePath + 'Done'
    with open(filePath, 'rb') as file:
        picData, readData = file.read().split(data_parse.eContactSplit)
    # 标记 与 移走
    os.rename(filePath, donePath)
    __remove_file(donePath)
    infoList = fileName.split('_')[1].split('-')[:8]
    return SensorData(fileName, module, location, num, infoList, [picData, readData])


def parse_pd(fileName, module, location) -> SensorData:
    """ 解析网口 - 局放
    param
        fileName: 文件名
        module: 模块
        location: 监测位置
    return
        SensorData
    """
    filePath = file_path.binaryPath + fileName
    donePath = filePath + 'Done'
    with open(filePath, 'rb') as file:
        data = file.read()
        dataList = [struct.unpack("<H", data[i:i + 2])[0]
                    for i in range(0, len(data) - 6, 2)]
    # 标记 与 移走
    os.rename(filePath, donePath)
    __remove_file(donePath)
    infoList = fileName.split('_')[1].split('-')[:8]
    num = 1
    return SensorData(fileName, module, location, num, infoList, dataList)


def __remove_file(filePath):
    """ 移走文件
    param
        fileName: 文件路径
    return
    """
    if platform.system().lower() == 'linux':
        try:
            shutil.move(filePath, file_path.removePath)
        except Exception as e:
            print(e)
