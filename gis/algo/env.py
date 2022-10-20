"""
环境模块
"""
from input.read_module import read_env_file
from algo.utils import *
from namespace import constant as cn
from typing import Iterable

tempMax = cn.eConfig['env']['tempMax']
tempMin = cn.eConfig['env']['tempMin']
hum = cn.eConfig['env']['hum']


def env1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有环境文件
    param
    return
        OutData, ......
    """
    for sData in read_env_file():
        yield __handle_one_env(sData)


def __handle_one_env(sensorData) -> OutData:
    """ 处理单个环境文件的数据
    param
        sensorData: 数据
    return
        OutData
    """
    data = sensorData.data
    # 算法处理
    outDict = {'temperature': get_value(data, 0),
               'humidity': get_value(data, 1),
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    # 异常处理
    if outDict['temperature'] > tempMax:
        set_state_exc(outDict, 80, '温度过高')
    elif outDict['temperature'] < tempMin:
        set_state_exc(outDict, 80, '温度过低')
    if outDict['humidity'] > hum:
        set_state_exc(outDict, 80, '湿度过高')
    return OutData(sensorData, outDict)
