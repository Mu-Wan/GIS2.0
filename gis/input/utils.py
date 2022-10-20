"""
工具
"""
import time


class SensorData:
    """ 传感器单文件的数据内容
    attr
        fileName: 文件名
        module: 模块(1级)
        location: 监测位置(2级)
        num: 同监测位置的机位(3级)
        timeList: 动作时间数组
        data: 数据内容
    method
    """

    def __init__(self, fileName, module, location, num, timeList, data):
        self.fileName = fileName
        self.module = module
        self.location = location
        self.num = num
        self.timeList = timeList
        self.data = data

    def get_time_stamp(self) -> int:
        """ 时间数组转时间戳
        param
        return
        """
        timeStr = '-'.join([str(_) for _ in self.timeList[:-2]])
        tempStamp = time.mktime(time.strptime(timeStr, "%Y-%m-%d-%H-%M-%S"))
        tempStamp *= 10 ** 6
        return tempStamp + int(self.timeList[-2]) * 10 ** 3 + int(self.timeList[-1])

    def __str__(self):
        return f"module:{self.module} | location:{self.location} | " \
               f"num:{self.num} | timeList:{self.timeList}\n" \
               f"data-len:{len(self.data)}\n"
