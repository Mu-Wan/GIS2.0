"""
解析二进制文件内容
"""


class SensorData:
    """ sensor one file data
    attr
        time: 动作时间
        module: 模块(1级)
        location: 监测位置(2级)
        num: 同监测位置的机位(3级)
        data: 数据内容
    method
    """

    def __init__(self):
        self.time = ""
        self.module = ""
        self.location = ""
        self.num = ""
        self.data = []


def parse_485():
    """ 解析485
    param:
    return:
    """
    pass


def parse_touch():
    """ 解析网口 - 红外视频
    param:
    return:
    """
    pass


def parse_pd():
    """ 解析网口 - 局放
    param:
    return:
    """
    pass
