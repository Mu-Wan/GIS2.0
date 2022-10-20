"""
气体模块
"""
from input.read_module import read_gas_file
from algo.utils import *
from namespace import constant as cn
from typing import Iterable

lowWarn = cn.eConfig['gas']['other']['lowWarn']
bLowWarn = cn.eConfig['gas']['breaker']['lowWarn']
bLowLock = cn.eConfig['gas']['breaker']['lowLock']


def gas1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有气体文件
    param
    return
        OutData, ......
    """
    for sData in read_gas_file():
        yield __handle_one_gas(sData)


def __handle_one_gas(sensorData) -> OutData:
    """ 处理单个气体文件的数据
    param
        sensorData: 数据
    return
        OutData
    """
    data = sensorData.data
    # 算法处理
    outDict = {'press': get_value(data, 16),
               'temperature': get_value(data, 26),
               'microwater': get_value(data, 54),
               'density': get_value(data, 76),
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    # 异常处理
    if sensorData.location.find('断路器') == -1:
        if outDict['density'] < lowWarn:
            set_state_exc(outDict, 80, '低气压报警')
    else:
        if bLowLock < outDict['density'] < bLowWarn:
            set_state_exc(outDict, 80, '低气压报警')
        elif outDict['density'] < bLowLock:
            set_state_exc(outDict, 60, '低气压闭锁')
    return OutData(sensorData, outDict)

