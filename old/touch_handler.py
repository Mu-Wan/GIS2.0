import os
import numpy as np
import cv2


def breaking_identify(img_path, threshold=85):
    """Identify the breaking of the contact.

    Args:
        img_path (str): Path of image. eg: "D:/gis/image_process/fenzha.png".
        threshold (int): Threshold value for judging closing and opening. Default:85.

    Returns:
        str: "分闸" or "合闸" or "中间状态".
    """
    img = cv2.imread(img_path, 0)
    rows, cols = img.shape
    mean_list = []
    for x in range(160, 405, 12):
        mean_list.append(img[0:330, x].mean())

    i = len(mean_list) - 1
    while i > 0:
        if max(mean_list) < threshold:
            return 0
            # print("分闸")
            # break
        else:
            if mean_list[i] < threshold:
                i -= 1
            else:
                if i == len(mean_list) - 1:
                    return 1
                    # print("合闸完毕")
                    # break
                else:
                    return 2
                    # print(f"中间状态")
                    # break
