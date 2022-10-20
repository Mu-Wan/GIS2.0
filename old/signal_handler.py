import numpy as np
import scipy.signal as signal
from PyEMD import EMD, Visualisation
from matplotlib import pyplot as plt
import name_place as cn


def rect_wave_edge(data):
    """
    :return: low_to_h: [矩形波升沿], high_to_l: [矩形波降沿]
    """
    y = np.array(data)
    x = np.arange(0, len(y))
    df = np.diff(y) / np.diff(x)
    # 判定斜率
    dh = np.max(y) - np.min(y)
    df_judge = dh / 10
    # 抖动区域
    shake_judge = 30
    high_to_l, low_to_h = [], []
    raw_lh = np.where(df > df_judge)[0].tolist()
    raw_hl = np.where(df < -df_judge)[0].tolist()
    # 去同升/降的相近点 + 抖动点
    for index, temp_raw in enumerate([raw_lh, raw_hl]):
        temp = 0
        for i in temp_raw:
            if (i - temp) > shake_judge:
                if index:
                    high_to_l.append(i)
                else:
                    low_to_h.append(i)
            temp = i
    # print('原始上升点: ', raw_lh, '去同上升点: ', low_to_h)
    # print('下降点: ', raw_hl, '去同下降点: ', high_to_l)
    # 去抖动点
    for hl in high_to_l:
        for lh in low_to_h:
            if abs(hl - lh) < shake_judge:  # 去掉后面的
                if hl > lh:
                    high_to_l.remove(hl)
                else:
                    low_to_h.remove(lh)
    return low_to_h, high_to_l


def find_turn_dot(data, space, cycle, ins_high, per_high):
    """
    :param space: 间隔点数
    :param cycle: 循环判断次数
    :param ins_high: 每次上升/下降高度
    :param per_high: 整体上升/下降高度
    :return: [开始上升,开始下降], [上升至平缓,下降至平缓]
    """
    to_change, to_steady = [[], []], [[], []]
    smooth_data = wave_smooth(data)
    to_ins, to_desc = find_change_dot(
        smooth_data, space, cycle, ins_high, per_high)
    ins_to, desc_to = find_steady_dot(
        smooth_data, space, cycle, ins_high, per_high)
    to_change = [to_ins, to_desc]
    to_steady = [ins_to, desc_to]
    return to_change, to_steady


def find_change_dot(smooth_data, space, cycle, ins_high, per_high, allow_per=20):
    """
    判断某点是否连续抬升/下降 => 从左到右 连续抬升/下降
    :param smooth_data: 滤波后的数据
    :param space: 间隔几个点进行比较
    :param cycle: 循环判断几次
    :param ins_high: 每次上升/下降高度
    :param allow_per: 允许偏差点数
    :return: 上升,下降
    """
    to_ins, to_desc = 0, 0
    i, ins_done, desc_done = 0, False, False
    allow_num = int(cycle/allow_per) + 1
    while i < len(smooth_data) - cycle*space:
        delta = smooth_data[i + 1:i + 1 + cycle*space: space] - \
            smooth_data[i:i + cycle*space: space]
        # 容错但不是第一个
        if not ins_done and (delta[delta > ins_high].size >= cycle - allow_num and delta[0] > ins_high) \
                and abs(smooth_data[i + cycle*space] - smooth_data[i]) > max(abs(smooth_data))*per_high:
            to_ins = i + 1
            ins_done = True
        if not desc_done and (delta[delta < -ins_high].size >= cycle - allow_num and delta[0] < -ins_high) \
                and abs(smooth_data[i + cycle*space] - smooth_data[i]) > max(abs(smooth_data))*per_high:
            to_desc = i
            desc_done = True
        if ins_done and desc_done:
            break
        i += 1
    return to_ins, to_desc


def find_steady_dot(smooth_data, space, cycle, ins_high, per_high, allow_per=20):
    """
    判断某点是否连续平缓 => 从右到左 连续抬升/下降
    :param smooth_data: 滤波后的数据
    :param space: 间隔几个点进行比较
    :param cycle: 循环判断几次
    :param ins_high: 每次上升/下降高度
    :param allow_per: 允许几个点偏差
    :return: 上升平缓,下降平缓
    """
    ins_to, desc_to = 0, 0
    i, ins_done, desc_done = len(smooth_data) - 1, False, False
    allow_num = int(cycle/allow_per) + 1
    while i > cycle*space:
        delta = smooth_data[i + 1 - cycle*space:i + 1: space] - \
            smooth_data[i - cycle*space:i: space]
        # 容错但不是最后一个
        if not ins_done and (delta[delta > ins_high].size >= cycle - allow_num and delta[-1] > ins_high):
            ins_to = i
            ins_done = True
        if not desc_done and (delta[delta < -ins_high].size >= cycle - allow_num and delta[-1] < -ins_high) \
                and abs(smooth_data[i - cycle*space] - smooth_data[i]) > max(abs(smooth_data)) * per_high:
            desc_to = i
            desc_done = True
        if ins_done and desc_done:
            break
        i -= 1
    return ins_to, desc_to


def judge_hor_both(data, index: int, half_judge: int, is_change_per: int):
    """
    判断某点附近是否近似水平
    :param judge_len:
    :param index:
    :param data:
    :return: [左边(是否,超出点数),右边(是否,超出点数)]
    """
    # 左右与中点的允许误差: 相对判断(以高度百分比) => 越大,越易视为水平,越难视为非水平(升降点出现频率降低)
    hor_range = np.max(np.abs(data)) / 150
    judge_left, judge_right = True, True
    left_out, right_out = 0, 0
    judge_dot = data[index]
    left_dot_list = data[index - half_judge + 1:index + 1]
    right_dot_list = data[index:index + half_judge]
    dy = np.abs(
        np.min(data[index - half_judge + 1:index + half_judge]) -
        np.max(data[index - half_judge + 1:index + half_judge]))
    # 整体增量判断: 绝对 + 相对
    if dy > 0.1 and dy > np.max(np.abs(data)) / is_change_per:
        # 左/右与中点差值: 边点误差 + 然后整体误差 => 半数超出视为非水平
        left_out = left_dot_list[(np.abs(left_dot_list - judge_dot) >
                                  hor_range)].size
        if left_out > int(half_judge / 2):
            judge_left = False
        right_out = right_dot_list[(np.abs(right_dot_list - judge_dot) >
                                    hor_range)].size
        if right_out > int(half_judge / 2):
            judge_right = False
    return [(judge_left, left_out), (judge_right, right_out)]


def peak_trough(data, pro_range):
    """
    :param data:
    :param pro_range: 相对突起程度(很重要,需要调试才能取得能获得峰谷值) 短波(0.1-0.4) 长波0.1
    :return:[[波峰],[波谷]]
    """
    smooth_data = wave_smooth(data)
    peaks, properties = signal.find_peaks(smooth_data, prominence=pro_range)
    troughs, properties = signal.find_peaks(-smooth_data, prominence=pro_range)
    return peaks, troughs


def find_base_value(data, cur_kind):
    """
    滤波(去尖峰) -> 找到抬升点 和 趋缓点(不稳定因素) -> 取除此之外的平均值 / 众数 x / 渐近线 x
    :param data: 原始数据
    :param cur_kind: 曲线类型
    :return: 水平偏移
    """
    smooth_data = wave_smooth(data)
    if cur_kind == "close":
        to_change_dot, to_steady_dot = find_turn_dot(
            smooth_data, *cn.close_cur_find)
    elif cur_kind == "sep":
        to_change_dot, to_steady_dot = find_turn_dot(
            smooth_data, *cn.sep_cur_find)
    if to_change_dot[0] != 0 and to_steady_dot[-1] != 0:
        begin, end = to_change_dot[0], to_steady_dot[-1]
    else:
        begin, end = 0, 0
    base_data = np.hstack((smooth_data[:begin], smooth_data[end:]))
    # base_value = np.average(base_data)
    base_data = (np.round(base_data, 4) * 10000).astype('int64')
    # base_data = np.abs(base_data)
    base_value = np.argmax(np.bincount(base_data)) / 10000
    return base_value


def wave_smooth(data, percent: int = cn.smooth_default):
    """
    滤波并转np
    :param data:
    :return: (np)[滤波后]
    """
    # win_len = int(len(data) / 800)
    # if win_len == 0:
    #     win_len = int(len(data) / 100)
    # 中值滤波: 去除尖锐
    med_data = signal.medfilt(data, 11)
    # return med_data
    # window = np.ones(win_len) / float(win_len)
    # smooth_data = np.convolve(med_data, window, 'same')
    win_len = int(len(data) / percent) + 1
    window = np.ones(win_len) / float(win_len)
    smooth_data = np.convolve(med_data, window, 'same')
    return np.array(smooth_data)


def trip_wave_smooth(data):
    # 拟合滤波 => 拟合曲线 => (窗口太短会只是减弱,窗口太大变形/阶数越高抖得越厉害,越低变形越大)
    win_len = int(len(data) / 20)
    if win_len % 2 == 0:
        win_len += 1
    # plt.figure()
    smooth_data = signal.savgol_filter(data, win_len, 5)
    smooth_data = signal.medfilt(smooth_data, win_len)
    trip_sec_tc, trip_sec_ts = find_turn_dot(smooth_data, *cn.trip_sep_find)
    # plt.plot(range(len(data)), smooth_data)
    # print(trip_sec_tc[1], smooth_data[trip_sec_tc[1]-10:trip_sec_tc[1]+10])
    # plt.scatter(trip_sec_tc[0], smooth_data[trip_sec_tc[0]])
    # plt.scatter(trip_sec_tc[1], smooth_data[trip_sec_tc[1]])
    # plt.scatter(trip_sec_ts[0], smooth_data[trip_sec_ts[0]])
    # plt.scatter(trip_sec_ts[1], smooth_data[trip_sec_ts[1]])
    # plt.plot(range(len(data)), data - 1)
    # plt.show()
    return np.array(smooth_data)


def wave_diff(data):
    """
    :param data:
    :return: np[滤波后的导数]
    """
    smooth_data = wave_smooth(data)
    y_diff = np.diff(smooth_data) / np.diff(range(0, len(data)))
    return wave_smooth(np.append(y_diff, 0))


def wave_fft(data):
    """
    :param data:
    :return: 幅频/相频
    """
    data_fft = np.fft.fft(data)
    fft_abs = np.abs(data_fft) / len(data)
    fft_angle = np.angle(data_fft) / np.pi * 180
    half_len = int(len(data) / 2)
    return fft_abs[1:half_len], fft_angle[1:half_len]


def getE_Imfs(data):
    """
    :param data:
    :return: IMFs的能量距
    """
    emd = EMD()
    emd.emd(data)
    imfs, res = emd.get_imfs_and_residue()
    E_imfs, delta_T = [], 1 / (cn.vb_frequency*1000)
    for i in range(len(imfs)):
        E_imf = 0
        for j in range(len(imfs[i])):
            E_imf += j*delta_T * ((imfs[i][j]*j*delta_T)**2)
        E_imfs.append(round(E_imf, 3))
    return imfs, res, E_imfs
