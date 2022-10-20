"""
工具
"""
from input.utils import SensorData
from namespace.file_path import outputPath
import json


class OutData:
    """ 输出数据类型
    attr
    method
    """

    def __init__(self, sData: SensorData, outDict):
        self.outDict = outDict
        self.outDict['datetimes'] = sData.timeList
        self.outDict['location'] = sData.location

    def __str__(self):
        return f"data:{self.outDict}"


def get_value(data, num, valid=4) -> int:
    """ 获取数据
    param
        data: 数据
        num: 位数
        valid: 有效位数
    return
        int
    """
    return round(data[num], valid)


def set_state_exc(d, state, exception):
    """ 评分 及 报警
    param
        d: 需要修改的字典
        state: 评分
        exception: 报警
    return
    """
    d['state'] = state
    d['exception'] = exception


def save_curve(data, fileName):
    """ 存曲线文件
    param
        data: 曲线数据
        fileName: 文件名(不含后缀)
    return
    """
    with open(outputPath + fileName + '.dat', "a+") as f:
        json.dump(data, f, indent=2)
