"""
触头模块
"""
from input.read_module import read_econtact_file
from algo.utils import *
from namespace.file_path import outputPath
import numpy as np
from matplotlib import pyplot as plt
import cv2
from typing import Iterable

lightPre = 'l'
InfraredPre = 'r'


def econtact1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有触头文件
    param
    return
        OutData, ......
    """
    for sData in read_econtact_file():
        yield __handle_one_econtact(sData)


def __handle_one_econtact(sensorData) -> OutData:
    """ 处理单个触头文件的数据
    param
        sensorData: 数据
    return
        OutData
    """
    # data = [[pic], [red]]
    picData, redData = sensorData.data
    lightName = __generate_name(lightPre, sensorData.fileName)
    InfraredName = __generate_name(InfraredPre, sensorData.fileName)
    # 算法处理
    outDict = {'phase': sensorData.num,
               'position': 0,
               'temperature_max': 0,
               'visible_light_filename': lightName,
               'infrared_filename': InfraredName,
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    # 视频图片
    with open(outputPath + lightName, "wb+") as f:
        f.write(picData)
    # 红外图片
    redData = redData[:-1]  # 冗余一位
    redData = np.array(redData).reshape(24, 32)
    redData[0, 0] = redData[0, -1]  # 下位机bug
    for _ in range(4):  # 横向扩征
        redData = np.repeat(redData, 2, axis=1)[:, :-1]
        redData[:, 1::2] = (redData[:, 2::2] + redData[:, 1::2]) / 2
    for _ in range(4):  # 纵向扩征
        redData = np.repeat(redData, 2, axis=0)[:-1, :]
        redData[1::2, :] = (redData[2::2, :] + redData[1::2, :]) / 2
    redData = np.flip(redData, axis=1)
    fig = plt.figure(figsize=(6, 4.8))
    fig.subplots_adjust(left=0.07, right=1.05, bottom=0.08, top=0.95)
    plt.imshow(redData, cmap="jet", aspect='auto')
    plt.colorbar()
    maxIndex = np.unravel_index(  # 最大值
        np.argmax(redData, axis=None),
        redData.shape)
    for i in range(100, 150):  # 最大值标记
        plt.scatter(maxIndex[1], maxIndex[0],
                    marker='o', c='none', edgecolors='k', s=i)
    plt.savefig(outputPath + InfraredName)
    # 数据库
    outDict['temperature_max'] = np.max(redData)
    outDict['position'] = __breaking_identify(outputPath + lightName)
    # 异常处理
    return OutData(sensorData, outDict)


def __generate_name(prefix, fileName) -> str:
    """ 分别生成红外、视频文件名
    param
        prefix: 前缀
        filaName: 二进制文件名
    return
        str
    """
    return prefix + '_' + fileName + '.png'


def __breaking_identify(imgPath, threshold=85):
    """ 分合位置识别
    param
        img_path (str):
        threshold (int):
    return
        str: "分闸" or "合闸" or "中间状态".
    """
    img = cv2.imread(imgPath, 0)
    rows, cols = img.shape
    mean_list = []
    for x in range(160, 405, 12):
        mean_list.append(img[0:330, x].mean())
    i = len(mean_list) - 1
    while i > 0:
        if max(mean_list) < threshold:
            return 0
        else:
            if mean_list[i] < threshold:
                i -= 1
            else:
                if i == len(mean_list) - 1:
                    return 1
                else:
                    return 2
