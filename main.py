import touch_handler as th
from logger import mylogger
import signal_handler as sh
from db_handler import DBHandler
import read_handler as rh
import name_place as cn
import json
import math
import time
import binascii
import copy
import os
import socket
import traceback

import numpy as np
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cm
# import mpl_toolkits.axisartist as axisartist
# from matplotlib.ticker import MultipleLocator, AutoLocator, FixedLocator
from matplotlib import rcParams
config = {
    "font.family": 'serif',
    "font.size": 20,
    "mathtext.fontset": 'stix',
    "font.serif": ['SimSun'],
}
rcParams.update(config)

dbh = DBHandler()
isShow = False


def _get_mb_cur_switch(datalist: list, phase):
    """
    拆分三路电流(分 合 副分) + 三路辅助开关(只用1个)
    输入: [3000*3 + 3000-14]
    :return: cur:[np,np,np],switch:[np,np,np]
    """
    cur, switch = [], []
    for i in range(3):
        temp_cur = np.array(
            datalist[i * cn.mb_config[phase]['cs_dot']:(i + 1) * cn.mb_config[phase]['cs_dot']]) * 3.3 * 8 / 4096 / (1 + 50/12)
        cur.append(temp_cur + 0.2)
        if i == 0:
            # 点数不足100,缺少14点
            temp_switch = np.array(datalist[(
                i + 3) * cn.mb_config[phase]['cs_dot']:(i + 4) * cn.mb_config[phase]['cs_dot']] + [datalist[-1] for j in range(14)])
        else:
            temp_switch = np.array([0 for i in range(3000)])
        switch.append(temp_switch)
    return cur, switch


def _get_trip(datalist: list, phase):
    """
    对行程进行数值转换
    :return: np
    """
    datalist[-1] = datalist[-2]
    return (np.array(datalist) - cn.mb_config[phase]['ppr']*2) * 360 / (cn.mb_config[phase]['ppr']*4)


def _get_timestamp(info_list: list):
    """
    从帧头中获取时间戳
    """
    time_list = [str(x) for x in info_list[-8:-2]]
    ms, us = info_list[-2:]
    time_str = '-'.join(time_list)
    timestamp = time.mktime(time.strptime(time_str, "%Y-%m-%d-%H-%M-%S"))
    timestamp *= 10**6
    return timestamp + ms * 10**3 + us


def _get_name(timestamp: int, dois: list, description: str = ""):
    """
    获取文件名
    """
    get_time = time.localtime(int(timestamp / (10**6)))
    get_time = time.strftime("%Y-%m-%d_%H-%M-%S", get_time)
    name = hex(dois[0])[-1] + hex(dois[1])[-1] + "_" + \
        description + "_" + get_time + ".png"
    return name


def gas():
    """
    气体模块: 依照modbus协议取出相应数据
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 4行量值)
    curve表: n x (1 x {'名1':值, '名2':值, ...})
    """
    # region 论文
    # dot = 12
    # yl = [0.4 + random.uniform(-0.01, 0.01) for i in range(dot)]
    # t_yl = yl - np.min(yl) * 4 / 5
    # r_yl = t_yl / np.max(t_yl)
    # wd = [20 + random.uniform(-1, 1) for i in range(dot)]
    # t_wd = wd - np.min(wd) * 4 / 5
    # r_wd = t_wd / np.max(t_wd)
    # ws = [200 + random.uniform(-10, 10) for i in range(dot)]
    # t_ws = ws - np.min(ws) * 4 / 5
    # r_ws = t_ws / np.max(t_ws)
    # md = [24 + random.uniform(-0.6, 0.6) for i in range(dot)]
    # t_md = md - np.min(md) * 4 / 5
    # r_md = t_md / np.max(t_md)
    # x, x_name = [i for i in range(dot)], [f"{i}" for i in range(dot-1, -1, -1)]
    # plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    # plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    # fig = plt.figure(figsize=(10, 5), dpi=150)
    # fig.subplots_adjust(left=0.05, right=0.9,
    #                     bottom=0.1, top=0.9)
    # ax = axisartist.Subplot(fig, 111)
    # fig.add_axes(ax)
    # ax.axis["top"].set_visible(False)
    # ax.axis["left"].set_visible(False)
    # ax.axis["right"].set_visible(False)
    # ax.axis["bottom"].set_axisline_style("->", size=1.0)
    # ax.set_xticks(x)
    # ax.set_xticklabels(x_name)
    # ax.set_xlabel('t/h')
    # plt.plot(x, np.array(r_yl) + 3, label="压力/Mpa")
    # plt.plot(x, np.array(r_wd) + 2, label="温度/℃")
    # plt.plot(x, np.array(r_ws) + 1, label="微水/ppm")
    # plt.plot(x, np.array(r_md), label="密度/")
    # for index, value in enumerate(yl):
    #     plt.annotate(f"{round(value,3)}", (index, r_yl[index] + 3), xycoords='data',
    #                  xytext=(index-0.3, r_yl[index] + 0.05 + 3), fontsize=7)
    # for index, value in enumerate(wd):
    #     plt.annotate(f"{round(value,1)}", (index, r_wd[index] + 2), xycoords='data',
    #                  xytext=(index-0.3, r_wd[index] + 0.05 + 2), fontsize=7)
    # for index, value in enumerate(ws):
    #     plt.annotate(f"{round(value,1)}", (index, r_ws[index] + 1), xycoords='data',
    #                  xytext=(index-0.3, r_ws[index] + 0.05 + 1), fontsize=7)
    # for index, value in enumerate(md):
    #     plt.annotate(f"{round(value,1)}", (index, r_md[index]), xycoords='data',
    #                  xytext=(index-0.3, r_md[index] + 0.05), fontsize=7)
    # plt.legend(loc='upper right', bbox_to_anchor=(1.1, 1), fontsize=8)
    # plt.show()
    # endregion
    for module, location, num, doi, phase, infolist, datalist in rh.read_files(
            cn.func_gas):
        if infolist:
            gas_data = copy.deepcopy(cn.gas_data)
            # 数据解析: 气体传感器协议取值
            gas_data['相对压力'][2] = round(
                (datalist[int((16 - 14) / 2)]) - 0.1, 2)
            gas_data['温度'][2] = round(datalist[int((26 - 14) / 2)], 1)
            gas_data['微水'][2] = round(datalist[int((54 - 14) / 2)], 1)
            gas_data['密度'][2] = round(datalist[int((76 - 14) / 2)], 2)
            # 异常处理
            real_time, status_flag, status, act_name = 0, 0, '正常', ''
            if location.find('断路器') == -1:
                if gas_data['密度'][2] < cn.gas_other_high:
                    status_flag, status = 1, '低气压报警'
            else:
                if cn.gas_break_low < gas_data['密度'][2] < cn.gas_break_high:
                    status_flag, status = 1, '低气压报警'
                elif gas_data['密度'][2] < cn.gas_break_low:
                    status_flag, status = 1, '低气压闭锁'
            dbh.add_update(module, location, num, 1, real_time, infolist, act_name, status_flag,
                           status, gas_data, None, _get_timestamp(infolist))


def pd():
    """
    局放模块: 注意虽然两文件,但单独工作,相互不影响
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 4行量值)
    curve表: n x (1 x {'名1':值, '名2':值, ...})
    curve表: 1行 => {'PRPD':[], 'PRPS':[]}
    """
    for pd_num in range(5):
        is_done, index = False, 0
        prpd_t, prpd_h = [], []
        fri_infolist, fri_timestamp, Tc = [], 0, (0.02*(10**6))
        pd_data = copy.deepcopy(cn.pd_data)
        timestamp_list, alldata_list, beginPhase_list, time_list = [
            0], [], [0], []
        module, location, phase = '', '', 0
        min_set, insert_len = -30, 75
        for module, location, num, doi, phase, infolist, datalist in rh.read_files(cn.func_pd, pd_num):
            if infolist:
                is_done = True
                index += 1
                datalist = 5 - (5 * np.array(datalist)) / 2048
                datalist = 10 * np.log10(datalist**2 / 50 * 1000 + 1e-7)
                if np.max(datalist) > 25:
                    datalist[np.argmax(datalist)] = 25
                datalist = np.where(datalist < min_set, min_set, datalist)
                # 原始图像
                # plt.figure(figsize=(8, 6))
                # plt.plot(range(len(datalist)), datalist)
                # plt.show()
                # plt.savefig(fname=cn.data_path +
                #             _get_name(_get_timestamp(infolist), doi, f"raw"))
                alldata_list.append(datalist)
                time_list.append(_get_timestamp(infolist))
                # 工频周期Tc + 采样周期Tp
                if index == 1:
                    fri_infolist = infolist
                    fri_timestamp = _get_timestamp(fri_infolist)
                else:
                    now_timestamp = _get_timestamp(infolist)
                    det_t = now_timestamp - fri_timestamp
                    timestamp_list.append(det_t)
                    T_count = math.floor(det_t / Tc)
                    max_index = np.argmax(datalist)
                    det_stamp = det_t - T_count * Tc
                    beginPhase_list.append(int(det_stamp / Tc * 360))
                    det_stamp += max_index * (cn.pd_T*10**6)
                    # 脉冲幅值
                    prpd_h.append(round(np.max(datalist), 2))
                    # 脉冲相位 = (现文件 + 脉冲索引*采样周期Tp - (起始文件 + n*Tc)) / Tc
                    prpd_t.append(round(det_stamp / Tc * 360, 2))
        if is_done:
            # 数据分析: PRPD
            try:
                get_time = _get_timestamp(fri_infolist)
                plt.figure(figsize=(8, 6))
                plt.ylabel('amplitude / dBm')
                # plt.ylim(0, ((max(prpd_h)/10) % 10 + 1) * 10)
                plt.ylim(0, 20)
                plt.yticks([0, 10, 20])
                plt.xlim(0, 360)
                plt.xticks([0, 90, 180, 270, 360])
                plt.xlabel('phase / °')
                x = np.arange(0, 361)
                sin_y = np.sin((2*math.pi/360) * x) * 10 + 10
                hor_y = [10 for j in range(361)]
                plt.plot(x, sin_y, linewidth=1, alpha=0.3)
                plt.plot(x, hor_y, color='black', linewidth=0.1)
                plt.scatter(prpd_t, prpd_h, s=3, c='red', alpha=0.2)
                prps_name = _get_name(get_time, doi, f"PRPD")
                plt.savefig(fname=cn.data_path + prps_name)
                pd_data['局部放电幅值'][2] = round(
                    max(prpd_h), 2)
                pd_data['局部放电功率'][2] = round(
                    10**(max(prpd_h)/10), 2)
                pd_data['局部放电频次'][2] = abs(
                    round(len(timestamp_list) / (timestamp_list[-1] / 10**6), 1))
                # pd_data['局部放电频次'][2] = abs(round(timestamp_list[-1] // Tc, 1))
                pd_data['脉冲个数'][2] = len(prpd_t)
                # 数据分析: PRPS
                fig = plt.figure(figsize=(6, 6.2))
                fig.subplots_adjust(left=0.03, right=0.91,
                                    bottom=-0.05, top=1.1)
                ax = plt.axes(projection='3d')
                # x:0-360; y:detT; z: 按detT从[[文件],[文件]]里取
                # => [文件]应该只有360里的极小一部分 => 要嘛把360细分更多点,摆上去
                # => 目前算出文件的相位,按一个点一° + 补点补成360
                timestamp_list = np.array(timestamp_list) / 10**6
                timestamp_temp = insert_len / \
                    max(timestamp_list) * timestamp_list
                # copyN = 1
                copyN = insert_len // len(timestamp_list)
                if copyN == 0:
                    copyN = 1
                timestamp_temp = [timestamp_temp[temp//copyN] +
                                  (timestamp_temp[(temp//copyN) + 1] - timestamp_temp[temp //
                                                                                      copyN]) * ((temp % copyN)) / copyN
                                  for temp in range((len(timestamp_temp)-1)*copyN)]
                # timestamp_temp.append(timestamp_list[-1])
                X, Y = np.meshgrid(x, timestamp_temp)
                Z = []
                # dy = len(timestamp_list) / 360
                dy = insert_len / 360
                min_data = np.min(alldata_list)
                for k in range(len(timestamp_temp)//copyN):
                    beginDot = beginPhase_list[k]
                    needDot = 360 - beginDot
                    if needDot >= len(alldata_list[k]):
                        z = [min_set for temp in range(beginDot)] + \
                            (alldata_list[k] - min_data).tolist() + \
                            [min_set for temp in range(
                                361 - len(alldata_list[k]) - beginDot)]
                    else:
                        z = [min_set if temp < beginDot
                             else alldata_list[k][temp - beginDot] for temp in range(361)]
                    z = np.array(z) - min_set
                    for j in range(copyN):
                        Z.append((z * (j + 1) / copyN))
                # ax.plot_surface(X, Y, np.array(Z), cmap='jet')
                X, Y, Z = X.flatten(), Y.flatten(), np.array(Z).flatten()
                offset = Z + np.abs(Z.min())
                fracs = offset.astype(float)/offset.max()
                norm = colors.Normalize(fracs.min(), fracs.max())
                norm = colors.Normalize(fracs.min(), fracs.max())
                color_values = cm.jet(norm(fracs.tolist()))
                ax.bar3d(X, Y, np.array([min_set for l in range(
                    len(X))]), dx=1, dy=dy, dz=Z, color=color_values)
                ylabel = [round(l/5*timestamp_list[-1], 2) for l in range(5)]
                ax.set_yticks([0, insert_len * 1 / 4, insert_len *
                               2 / 4, insert_len * 3 / 4, insert_len])
                ax.set_yticklabels(ylabel)
                ax.set_xlabel('phase / °')
                ax.set_ylabel('time / s')
                ax.set_zlabel('amplitude / dBm')
                # ax.w_xaxis.set_pane_color((1.0, 1.0, 1.0, 0))
                # ax.w_yaxis.set_pane_color((1.0, 1.0, 1.0, 0))
                # ax.w_zaxis.set_pane_color((1.0, 1.0, 1.0, 0))
                prpd_name = _get_name(get_time, doi, f"PRPS")
                # plt.show()
                plt.savefig(fname=cn.data_path + prpd_name)
                # 数据分析: 趋势图
                # plt.figure(figsize=(8, 6))
                # plt.ylabel('amplitude / V')
                # plt.xlabel('time / s')
                # # 获取上次一的 初始时间 / xy数据 (初次bug)
                # get_curve = dbh.select_curve(module, location)
                # if get_curve and get_curve.get('trend_data'):
                #     trend_data = get_curve['trend_data']
                #     init_time = trend_data['time']
                #     timestamp_list = trend_data['x'] + \
                #         ((np.array(timestamp_list[1:]) * 10**6 +
                #           (fri_timestamp - init_time)) / 10**6).tolist()
                #     prpd_h = trend_data['y'] + prpd_h
                # # 初次
                # else:
                #     init_time = fri_timestamp
                #     timestamp_list = timestamp_list[1:]
                # plt.plot(timestamp_list, prpd_h)
                # trend_name = hex(doi[0])[-1] + hex(doi[1])[-1] + "_trend.png"
                # plt.savefig(fname=cn.data_path + trend_name)
                # curve_data = {
                #     'prpd': prpd_name, 'prps': prps_name,
                #     'trend_pic': trend_name,
                #     'trend_data': {
                #         'time': init_time,
                #         'x': timestamp_list,
                #         'y': prpd_h
                #     }
                # }
                h_max = np.max(prpd_h)
                h_max_index = np.argmax(prpd_h)
                max_time = time_list[h_max_index+1]
                curve_data = {
                    'prpd': prpd_name,
                    'prps': prps_name,
                    'amp': h_max,
                    'freq': pd_data['局部放电频次'][2]
                }
                # 异常分析
                real_time, status_flag, status, act_name = 0, 0, '正常', '放电类型'
                dbh.add_update(module, location, num, 1, real_time, fri_infolist, act_name, status_flag,
                               status, pd_data, curve_data, max_time)
            except Exception as e:
                mylogger.error(f"{traceback.format_exc()}")
                # traceback.print_exc()


def _get_ms_cur_switch(datalist: list):
    """
    拆分三路电流(QSF1 QSF2 QS3) + 三路辅助开关(QSF1 QSF2 QS3)
    :return: cur:[np,np,np],switch:[np,np,np]
    """
    cur, switch = [], []
    for i in range(3):
        temp_cur = (np.array(
            (datalist[i * cn.ms_dot:(i + 1) * cn.ms_dot])) * 3.3 / 4096 - 1.633) \
            * 15 / 0.625 * cn.ms_cur_factor_list[i]
        cur.append(temp_cur)
        temp_switch = np.array(
            datalist[(i + 3) * cn.ms_dot:(i + 4) * cn.ms_dot])
        switch.append(temp_switch)
    return cur, switch


def ms():
    """
    机械特性-隔离开关模块
        - 数据收入: list
        - 数据情况:
            - 电流、开关: 3+3
        - 数据输出: 子界面x3 <= 分三次存储
    Record表: n x (3 x ...)
    ResultCal表: n x (3 x 7行量值)
    curve表: n x (3 x {'cur':[] , 'switch':[]})
    """
    ms_data = copy.deepcopy(cn.ms_data)
    op_kind_name = ['分', '合', '异常']
    for module, location, num, doi_high, phase, infolist, datalist in rh.read_files(
            cn.func_ms):
        if infolist:
            cur, switch = _get_ms_cur_switch(datalist)
            # plt.figure(figsize=(10, 4))
            # 交流电转有效值
            for i in range(3):
                real_time, status_flag, status, act_name = 0, 0, '正常', ''
                ms_data = copy.deepcopy(cn.ms_data)
                # cur[i] = cur[i] - np.average(cur[i][0:10])
                cur_dot = int(20 / (1 / cn.ms_frequency))
                cur[i] = np.array([np.sqrt(np.sum(np.power(cur[i][j:j+cur_dot], 2) / cur_dot))
                                   for j in range(len(cur[i])-cur_dot)])
                # 电流找点
                begin_dots, _ = sh.find_turn_dot(
                    cur[i], *cn.ms_find_begin)
                _, stop_dots = sh.find_turn_dot(
                    cur[i], *cn.ms_find_end)
                # 辅助开关判断
                switch_lh, switch_hl = sh.rect_wave_edge(switch[i][:-100])
                if switch_lh or switch_hl:
                    if switch_lh:   # 上升沿 = 合
                        op_kind = 1
                        ms_data['合闸时间'][2] = \
                            round((stop_dots[1] - begin_dots[0])
                                  * (1 / cn.ms_frequency), 2)
                        ms_data['电流持续时间'][2] = ms_data['合闸时间'][2]
                    elif switch_hl:   # 下降沿 = 分
                        op_kind = 0
                        ms_data['分闸时间'][2] = \
                            round((stop_dots[1] - begin_dots[0])
                                  * (1 / cn.ms_frequency), 2)
                        ms_data['电流持续时间'][2] = ms_data['分闸时间'][2]
                    # 三个位置同一个文件 => location需变化
                    location = cn.mod_loc_data[module][0][i][0]
                    ms_data['最大工作电流'][2] = round(np.max(cur[i]), 2)
                    ms_data['平均工作电流'][2] = round(np.average(
                        cur[i][begin_dots[0]:stop_dots[1]]), 2)
                    curve = {'cur': cur[i].tolist(),
                             'switch': switch[i].tolist()}
                    # 通知主控
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect(('192.168.1.2', 6667))
                            for i in range(3):
                                time.sleep(3)
                                s.send(b'\xeb\x90\xeb\x90\x09\x00\x09\x00\x96')
                            s.close()
                        mylogger.error('连接成功 且 发送成功')
                    except Exception as e:
                        mylogger.error(f'连接失败: {e.args}')
                    # 异常处理
                    if ms_data['最大工作电流'][2] > cn.ms_cur_max:
                        status_flag = 1
                        status = '电机电流异常'
                    act_name = op_kind_name[op_kind]
                    dbh.add_update(module, location, num, 3, real_time, infolist, act_name,
                                   status_flag, status, ms_data, curve)
                # else:
                #     op_kind = 2
                #     status_flag, status = 1, '辅助开关异常 '
            # region 绘制曲线
            #     plt.subplot(211)
            #     plt.plot(range(len(cur[i])), cur[i] + i)
            #     plt.legend(f'[{i}]')
            #     plt.scatter(begin_dots[0], cur[i][begin_dots[0]]+i)
            #     plt.scatter(stop_dots[1], cur[i][stop_dots[1]]+i)
            #     plt.subplot(212)
            #     plt.plot(range(len(switch[i])), switch[i] + i)
            #     plt.legend(f'[{i}]')
            #     for switch_dot in switch_lh:
            #         plt.scatter(switch_dot, switch[i][switch_dot])
            #     for switch_dot in switch_hl:
            #         plt.scatter(switch_dot, switch[i][switch_dot])
            # plt.show()
            # endregion


def mb():
    """
    机械特性-断路器模块
        传感器: 行程(1) + 电流/辅开(3+3)
        使用: 行程x3(每个:一相) + 电开x3(每个:一相的分/合/副分电流 + 3同开关)
        实际: 3+3文件 1个位置(1界面)
        处理思路: 1.拆分cur[3p] switch[1] trip[3]  2.三相结合计算
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 24行量值)
    curve表: n x (1 x {'cur': [ [[A相分],[合],[副分]], [[B相分],[合],[副分]], [[C相分],[合],[副分]] ],
                      'switch': [ [[A相],[],[]] , [[B相],[],[]], [[C相],[],[]] ],
                      'trip': [ [A相],[B相],[C相] ]
                      'vir': [ [A相],[B相],[C相] ]})
    """
    # 一次数据: [[]x6]
    for one_time_data in rh.read_files(cn.func_mb):
        mb_data = copy.deepcopy(cn.mb_data)
        module, location, num, infolist = '', '', 0, []
        cur, switch, trip, vir = {}, {}, {}, {}
        cs_stamp, trip_stamp = {}, {}
        # has_data = False
        has_data = True
        cs_phase = {0: False, 1: False, 2: False}
        trip_phase = {0: False, 1: False, 2: False}
        # 一个文件数据: [, , , , , ]
        for module, location, num, doi, phase, infolist, datalist in one_time_data:
            # if infolist:
            # has_data = True
            if doi[0] == cn.mod_doi[cn.func_mb][0]:  # 电流文件:属于电流区间段
                if phase in cs_phase.keys():
                    cs_phase[phase] = True
                cur[phase], switch[phase] = _get_mb_cur_switch(
                    datalist, phase)
                cs_stamp[phase] = _get_timestamp(infolist)
            else:  # 行程文件
                if phase in trip_phase.keys():
                    trip_phase[phase] = True
                trip[phase] = _get_trip(datalist, phase)
                trip_stamp[phase] = _get_timestamp(infolist)
            # else:
            #     break
        #
        if has_data:
            get_time = time.localtime(int(max(cs_stamp.values()) / (10**6)))
            get_time = time.strftime("%Y-%m-%d %H'%M'%S", get_time) + '.png'
            act_name, status, phase_name = "", "", ['A', 'B', 'C']
            phase_has_data = [True, True, True]

            # # 原始曲线绘制
            # _mb_draw_raw(cur, switch, trip, get_time)

            # 缺相置0
            _mb_single_complete(cur, switch, trip, cs_stamp, trip_stamp,
                                cs_phase, trip_phase, phase_has_data)

            # 校准曲线(以电流为基准)
            _mb_correct(cur, switch, trip, cs_stamp, trip_stamp)

            # 电流索引: 合闸索引,副分索引,分闸索引; 辅助开关
            close_i, subsep_i, sep_i, s_index = cn.close_order, cn.subsep_order, cn.sep_order, 0
            vir_dots, temp_vir = {'sep': 0, 'close': 0,
                                  'sec': 0}, {0: [], 1: [], 2: []}
            for phase in range(3):
                # region 1.操作判断: 辅助开关波形 (目前是01分闸 10合闸)
                # 变化沿: 合 一分 二分 [升(启),降(3)] [升缓(2),降缓(停)]
                # 行程: [升,降] [升缓,降缓] ; [升(启/0),降(0/启),升(合),降(二分)] [升缓(停/0),降缓(0/停),升缓(合),降缓(二分)]
                switch_lh, switch_hl = sh.rect_wave_edge(
                    switch[phase][s_index])  # 开关变化沿
                len_lh, len_hl = len(switch_lh), len(switch_hl)
                # 电流别名
                cur_close, cur_standby, cur_sep = cur[phase][close_i], cur[
                    phase][subsep_i], cur[phase][sep_i]

                cur_close_tc, cur_close_ts = sh.find_turn_dot(
                    cur_close, *cn.close_cur_find)  # 电流 合闸
                cur_sep_tc, cur_sep_ts = [0, 0], [0, 0]
                cur_sec_tc, cur_sec_ts = [0, 0], [0, 0]
                trip_tc, trip_ts = [0, 0], [0, 0]
                if cur_close_tc[0] != 0 and cur_close_ts[-1] != 0:
                    cur_sep_tc, cur_sep_ts = sh.find_turn_dot(
                        cur_sep[:int(len(cur_sep)/2)], *cn.sep_cur_find)  # 电流 一分
                    if cur_sep_tc[0] != 0 and cur_sep_ts[-1] != 0:
                        trip_tc, trip_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][:int(cur_close_tc[0])]), *cn.trip_sep_find)  # 行程 重合闸的一分
                    else:
                        trip_tc, trip_ts = sh.find_turn_dot(
                            trip[phase], *cn.trip_close_find)  # 行程 仅合闸
                    cur_sec_tc, cur_sec_ts = sh.find_turn_dot(
                        cur_sep[cur_close_tc[0]:], *cn.sep_cur_find)    # 电流 二分
                    if cur_sep_tc[0] != 0 and cur_sep_ts[-1] != 0:
                        cur_sec_tc = [temp + cur_close_tc[0]
                                      for temp in cur_sec_tc]
                        cur_sec_ts = [temp + cur_close_tc[0]
                                      for temp in cur_sec_ts]
                        trip_close_tc, trip_close_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][cur_close_tc[0]:cur_sec_ts[1]]), *cn.trip_close_find)  # 行程 重合闸的合闸
                        trip_sec_tc, trip_sec_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][cur_sec_tc[0]:]), *cn.trip_sec_find)  # 行程 重合闸的二分
                        trip_tc += [trip_close_tc[0] + cur_close_tc[0],
                                    trip_sec_tc[1] + cur_sec_tc[0]]
                        trip_ts += [trip_close_ts[0] + cur_close_tc[0],
                                    trip_sec_ts[1]+cur_sec_tc[0]]
                        # trip_tc += [temp + cur_close_tc[0]
                        # for temp in trip_sec_tc]
                        # trip_ts += [temp + cur_close_tc[0]
                        # for temp in trip_sec_ts]

                else:
                    trip_tc, trip_ts = sh.find_turn_dot(
                        sh.trip_wave_smooth(trip[phase]), *cn.trip_sep_find)  # 行程 仅分闸
                    cur_sep_tc, cur_sep_ts = sh.find_turn_dot(
                        cur_sep, *cn.sep_cur_find)  # 电流 仅分闸
                # # 原始图像绘制
                # temp_test = []
                # for i in range(3):
                #     temp_test.append([0 for p in range(len(trip[0]))])
                # _mb_draw_dot(cur, switch, trip, temp_test, phase, get_time, close_i,
                #              sep_i, cur_close, cur_sep, trip_tc, trip_ts,
                #              cur_close_tc, cur_close_ts, cur_sep_tc,
                #              cur_sep_ts, cur_sec_tc, cur_sec_ts)
                op_kind = 5  # 默认异常
                # 辅助开关判断
                if len_lh == 1 and len_hl == 0:  # 分:只有1个下降沿
                    op_kind = 0
                    act_name = "分闸"
                elif len_lh == 0 and len_hl == 1:  # 合:只有1个上升沿
                    op_kind = 1
                    act_name = "合闸"
                elif len_lh == 1 and len_hl == 1:
                    if switch_hl[0] < switch_lh[0]:
                        op_kind = 2  # 合分:上下各1个,且先上后下
                        act_name = "合分"
                    else:
                        op_kind = 3  # 分合:上下各1个,且先下后上
                        act_name = "分合"
                elif len_lh == 2 and len_hl == 1 and switch_lh[0] < switch_hl[0] < switch_lh[1]:
                    op_kind = 4  # 重合闸:分合分
                    act_name = "重合闸"
                # 行程判断
                if len(trip_tc) == 4 and len(trip_ts) == 4:
                    if trip_tc[1] == 0:
                        op_kind = 2  # 合分:上下各1个,且先上后下
                        act_name = "合分"
                    else:
                        op_kind = 4
                        act_name = '重合闸'
                elif trip_tc[1] != 0:  # 下降点
                    op_kind = 0
                    act_name = '分闸'
                elif trip_tc[0] != 0:  # 上升点
                    op_kind = 1
                    act_name = '合闸'
                if not phase_has_data[phase]:
                    op_kind = 6
                mb_data['操作类型'][2 + phase] = op_kind
                # count = dbh.select_data(module, location, phase,
                #                         '机械操作次数')[0][0]
                # add_count = 0
                # if op_kind in [0, 1]:
                #     add_count = 1
                # elif op_kind == 2:
                #     add_count = 2
                # elif op_kind == 4:
                #     add_count = 3
                # mb_data['机械操作次数'][2 + phase] = count + add_count
                # endregion

                # # region 2.量值计算
                # sep_dot, close_dot, sec_dot = 0, 1, 2  # 第n个变化沿对应意义
                # if op_kind in [1, 2]:  # 合/合分时意义有变
                #     sep_dot, close_dot = 1, 0

                # 在tc和ts的索引 [升,降]
                sep_begin_index, sep_stop_index = cur_sep_tc[0], cur_sep_ts[1]
                close_begin_index, close_stop_index = cur_close_tc[0], cur_close_ts[1]
                sec_begin_index, sec_stop_index = cur_sec_tc[0], cur_sec_ts[1]
                t_sep_begin_index, t_sep_stop_index = trip_tc[1], trip_ts[1]
                t_close_begin_index, t_close_stop_index = trip_tc[0], trip_ts[0]
                if op_kind == 2:
                    t_sep_begin_index, t_sep_stop_index = trip_tc[3], trip_ts[3]
                    t_close_begin_index, t_close_stop_index = trip_tc[2], trip_ts[2]
                if op_kind == 4:  # 重合闸 在第二段的0
                    t_close_begin_index, t_close_stop_index = trip_tc[2], trip_ts[2]
                    t_sec_begin_index, t_sec_stop_index = trip_tc[3], trip_ts[3]

                # region 量值计算思路
                #  电流分三条,合闸只会有1个波,分闸可能2个; 行程一条曲线,可能有3个
                #  点情况: 分闸3个(2变,1平) 合闸4个(2变,2平) 行程2个
                #  行程量 = 行程平稳点(值) - 行程变化点(值)
                #  虚拟断口位置 = 行程区间的0.65/0.7 + 开始点
                #  动作时间 = (虚拟断口 - 电流开始点(0)) * 采样时间
                #  动作速度 = (虚拟端口处(行程值) - 虚拟端口后10ms(行程值)) / 10
                #  电流 = 平均值( 变化点(值) 到 平稳点(值) )
                #  带电时间 = 变化点 - 平稳点
                # endregion
                if op_kind == 5:  # 异常直接不操作
                    mylogger.info(f'{phase}相: 异常类型')
                elif op_kind == 6:    # 无数据不操作
                    mylogger.info(f'{phase}相: 无数据')
                else:
                    try:
                        if op_kind != 1:  # 除合闸外均有分闸过程
                            try:
                                mb_data['一分行程量'][2 + phase] = round(
                                    abs(trip[phase][t_sep_stop_index] - trip[phase][t_sep_begin_index]) * cn.mb_config[phase]['trip_sep_factor'], 2)
                                virtual_high = (trip[phase][t_sep_stop_index] - trip[phase][t_sep_begin_index]) * cn.mb_config[phase]['sep_vir_per'] + \
                                    trip[phase][t_sep_begin_index]
                                virtual_sep = np.argmin(
                                    abs(trip[phase][t_sep_begin_index:t_sep_stop_index] - virtual_high)) + t_sep_begin_index
                                vir_dots['sep'] = virtual_sep
                                # (断口-分闸电流第一沿)*采样时间
                                mb_data['一分时间'][2 + phase] = round(
                                    (virtual_sep - sep_begin_index) * cn.mb_time_inter, 2)
                                mb_data['一分速度'][2 + phase] = cn.mb_config[phase]['sep_speed_factor'] * round(
                                    abs(trip[phase][virtual_sep] -
                                        trip[phase][virtual_sep +
                                                    int(10 / cn.mb_time_inter)]) / 10, 2)
                                mb_data['一分电流'][2 + phase] = round(
                                    max(cur_sep[sep_begin_index: sep_stop_index]), 2)
                                mb_data['一分带电时间'][2 + phase] = round(
                                    (sep_stop_index - sep_begin_index) * cn.mb_time_inter, 2)
                                if mb_data['一分行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['一分行程量'][2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['一分时间'][2 + phase] < cn.mb_diag['sep_time_min'] or mb_data['一分时间'][2 + phase] > cn.mb_diag['sep_time_max']:
                                    status += f"{phase_name[phase]}相分闸时间异常;"
                                if mb_data['一分速度'][2 + phase] < cn.mb_diag['sep_v_min'] or mb_data['一分速度'][2 + phase] > cn.mb_diag['sep_v_max']:
                                    status += f"{phase_name[phase]}相分闸速度异常;"
                                if mb_data['一分带电时间'][2 + phase] > cn.mb_diag['sep_cur_time_max']:
                                    status += f"{phase_name[phase]}相分线圈带电异常;"
                                if mb_data['一分电流'][2 + phase] > cn.mb_diag['sep_cur_max']:
                                    status += f"{phase_name[phase]}相分线圈电流异常;"
                                mylogger.info(f'{phase}相: 一分找点完毕')
                            except IndexError:
                                mylogger.warning(f'{phase}相: 一分找点错误!')
                        if op_kind != 0:  # 不是分的情况均有
                            try:
                                mb_data['合行程量'][2 + phase] = round(
                                    abs(trip[phase][t_close_stop_index] - trip[phase][t_close_begin_index]) * cn.mb_config[phase]['trip_close_factor'], 2)
                                virtual_high = (trip[phase][t_close_stop_index] - trip[phase][t_close_begin_index]) * cn.mb_config[phase]['close_vir_per'] + \
                                    trip[phase][t_close_begin_index]
                                virtual_close = np.argmin(
                                    abs(trip[phase][t_close_begin_index:t_close_stop_index] - virtual_high)) + t_close_begin_index
                                vir_dots['close'] = virtual_close
                                mb_data['合时间'][2 + phase] = round(
                                    (virtual_close - close_begin_index) * cn.mb_time_inter, 2)
                                mb_data['合速度'][2 + phase] = cn.mb_config[phase]['close_speed_factor'] * round(
                                    abs(trip[phase][virtual_close] -
                                        trip[phase][virtual_close -
                                                    int(10 / cn.mb_time_inter)]) / 10, 2)
                                mb_data['合电流'][2 + phase] = round(
                                    max(cur_close[close_begin_index:close_stop_index]), 2)
                                mb_data['合带电时间'][2 + phase] = round(
                                    (close_stop_index - close_begin_index) *
                                    cn.mb_time_inter, 2)
                                if mb_data['合行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['合行程量'][2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['合时间'][2 + phase] < cn.mb_diag['close_time_min'] or mb_data['合时间'][2 + phase] > cn.mb_diag['close_time_max']:
                                    status += f"{phase_name[phase]}相合闸时间异常;"
                                if mb_data['合速度'][2 + phase] < cn.mb_diag['close_v_min'] or mb_data['合速度'][2 + phase] > cn.mb_diag['close_v_max']:
                                    status += f"{phase_name[phase]}相合闸速度异常;"
                                if mb_data['合带电时间'][2 + phase] > cn.mb_diag['close_cur_time_max']:
                                    status += f"{phase_name[phase]}相合线圈带电异常;"
                                if mb_data['合电流'][2 + phase] > cn.mb_diag['close_cur_max']:
                                    status += f"{phase_name[phase]}相合线圈电流异常;"
                                mylogger.info(f'{phase}相: 合找点完毕')
                            except IndexError as e:
                                mylogger.warning(f'{phase}相: 合找点错误!')
                        if op_kind == 4:  # 重合闸才有
                            try:
                                mb_data['二分行程量'][2 + phase] = abs(round((trip[phase][
                                    t_sec_stop_index] - trip[phase][t_sec_begin_index]) * cn.mb_config[phase]['trip_sep_factor'], 2))
                                virtual_high = (trip[phase][t_sec_stop_index] - trip[phase][t_sec_begin_index]) * cn.mb_config[phase]['sep_vir_per'] + \
                                    trip[phase][t_sec_begin_index]
                                virtual_sec = np.argmin(
                                    abs(trip[phase][t_sec_begin_index:] - virtual_high)) + t_sec_begin_index
                                vir_dots['sec'] = virtual_sec
                                mb_data['二分时间'][2 + phase] = cn.mb_config[phase]['sep_speed_factor'] * round(
                                    (virtual_sec - sec_begin_index) * cn.mb_time_inter, 2)
                                mb_data['二分速度'][2 + phase] = round(
                                    abs(trip[phase][virtual_sec] -
                                        trip[phase][virtual_sec +
                                                    int(10 / cn.mb_time_inter)]) / 10, 2)
                                mb_data['二分电流'][2 +
                                                phase] = round(max(cur_sep[sec_begin_index:sec_stop_index]), 2)
                                mb_data['二分带电时间'][2 + phase] = round(
                                    (sec_stop_index - sec_begin_index) * cn.mb_time_inter, 2)
                                if mb_data['二分行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['二分行程量'][2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['二分时间'][2 + phase] < cn.mb_diag['sep_time_min'] or mb_data['二分时间'][2 + phase] > cn.mb_diag['sep_time_max']:
                                    status += f"{phase_name[phase]}相分闸时间异常;"
                                if mb_data['二分速度'][2 + phase] < cn.mb_diag['sep_v_min'] or mb_data['二分速度'][2 + phase] > cn.mb_diag['sep_v_max']:
                                    status += f"{phase_name[phase]}相分闸速度异常;"
                                if mb_data['二分带电时间'][2 + phase] > cn.mb_diag['sep_cur_time_max']:
                                    status += f"{phase_name[phase]}相分线圈带电异常;"
                                if mb_data['二分电流'][2 + phase] > cn.mb_diag['sep_cur_max']:
                                    status += f"{phase_name[phase]}相分线圈电流异常;"
                                mylogger.info(f'{phase}相: 二分找点完毕')
                            except IndexError:
                                mylogger.warning(f'{phase}相: 二分找点错误!')
                    except Exception as e:
                        mylogger.error("找点错误!")
                temp_vir[phase] = [0 for i in range(len(trip[phase]))]
                if vir_dots['close']:
                    temp_vir[phase][vir_dots['close']:] = [1 for i in range(
                        len(temp_vir[phase][vir_dots['close']:]))]
                if vir_dots['sep']:
                    if vir_dots['close'] != 0 and vir_dots['sep'] > vir_dots['close']:
                        temp_vir[phase][vir_dots['sep']:] = [0 for i in range(
                            len(temp_vir[phase][vir_dots['sep']:]))]
                    else:
                        temp_vir[phase][:vir_dots['sep']] = [1 for i in range(
                            len(temp_vir[phase][:vir_dots['sep']]))]
                if vir_dots['sec']:
                    temp_vir[phase][vir_dots['sec']:] = [0 for i in range(
                        len(temp_vir[phase][vir_dots['sec']:]))]
                vir_dots = {'sep': 0, 'close': 0, 'sec': 0}
                # # 绘制校准曲线
                # _mb_draw_dot(cur, switch, trip, temp_vir, phase, get_time, close_i,
                #              sep_i, cur_close, cur_sep, trip_tc, trip_ts,
                #              cur_close_tc, cur_close_ts, cur_sep_tc,
                #              cur_sep_ts, cur_sec_tc, cur_sec_ts)
            # 三相时间最大 - 最小
            phase_3time = [
                mb_data['一分时间'][2:], mb_data['合时间'][2:], mb_data['二分时间'][2:]
            ]
            mb_data['一分同期'][2] = round(
                max(phase_3time[0]) - min(phase_3time[0]), 2)
            mb_data['合同期'][2] = round(
                max(phase_3time[1]) - min(phase_3time[1]), 2)
            mb_data['二分同期'][2] = round(
                max(phase_3time[2]) - min(phase_3time[2]), 2)

            curve_data = {'cur': [], 'switch': [], 'trip': [], 'vir': []}
            curve_filter = {'cur': [], 'switch': [], 'trip': [], 'vir': []}
            for i in range(3):
                curve_data['vir'].append(temp_vir[i])
                curve_filter['vir'].append(temp_vir[i])
                # curve_data['trip'].append(trip[i].tolist())
                smooth_trip = sh.wave_smooth(trip[i]).tolist()
                smooth_trip[-5:] = smooth_trip[-10:-5]
                curve_data['trip'].append(smooth_trip)
                curve_filter['trip'].append(smooth_trip)
                temp_cur, filter_cur, temp_switch, filter_switch = [], [], [], []
                for j in range(3):
                    # temp_cur.append(cur[i][j].tolist())
                    temp_cur.append(sh.wave_smooth(cur[i][j]).tolist())
                    filter_cur.append(sh.wave_smooth(cur[i][j]).tolist())
                    temp_switch.append(switch[i][j].tolist())
                    filter_cur.append(sh.wave_smooth(switch[i][j]).tolist())
                curve_data['cur'].append(temp_cur)
                curve_filter['cur'].append(temp_cur)
                curve_data['switch'].append(temp_switch)
                curve_filter['switch'].append(temp_switch)
            # with open(cn.data_path + '/mb_data.json', 'w',
            #           encoding='utf-8') as file:
            #     json.dump(mb_data, file, ensure_ascii=False, indent=4)
            with open(cn.data_path + f"/{get_time[:-4]}.json", 'w') as file:
                json.dump(curve_data, file, indent=4)
            with open(cn.data_path + f"/\'{get_time[:-4]}.json", 'w') as file:
                json.dump(curve_filter, file, indent=4)
            real_time, status_flag = 0, 0
            if status == "":
                status = "正常"
            else:
                status_flag = 1
            dbh.add_update(module, location, num, 3, real_time, infolist, act_name, status_flag,
                           status, mb_data, curve_filter)
    # plt.savefig(fname=cn.root_path + 'rc\'')


def _mb_draw_raw(cur, switch, trip, get_time):
    # for i in range(3):
    # fig = plt.figure(figsize=(21, 9))
    # plt.title('Original', fontsize='13', fontweight='bold')
    # plt.subplot(3, 1, 1)  # 电流
    # for j in range(3):
    #     x = np.arange(0, len(cur[i][j]))
    #     plt.plot(x, cur[i][j] + j * 1.5, label=f'cur[{j}]')
    #     plt.legend(loc='upper right')
    #     plt.yticks([0, 1.5, 3], ['0', '0', '0'])
    # plt.subplot(3, 1, 2)  # 辅助开关
    # for j in range(3):
    #     plt.plot(x, switch[i][j] + j * 1.5, label=f'switch[{j}]')
    #     plt.yticks([], [])
    #     plt.legend(loc='upper right')
    # plt.subplot(3, 1, 3)  # 行程
    # x = np.arange(0, len(trip[i]))
    # plt.plot(x, trip[i], label=f'trip[{i}]')
    # plt.legend()
    # name = f"r'{i}'{get_time}"
    # plt.savefig(fname=cn.data_path + name)
    fig = plt.figure(figsize=(21, 9))
    json_cur = {}
    for i in range(3):
        json_cur[f'{i}相'] = {}
        for j in range(3):
            x = np.arange(200, 500)
            plt.plot(x, cur[i][j][200:500] * 4096 * (1 + 49.4 / 5.1) /
                     33 + j * 1.5, label=f'cur[{i}][{j}]')
            json_cur[f'{i}相'][f'{j}'] = cur[i][j][200:500].tolist()
    name = f"ir'{get_time}"
    plt.legend()
    plt.savefig(fname=cn.data_path + name)
    with open(cn.data_path + name[:-4]+".json", 'w', encoding="utf-8") as file:
        json.dump(json_cur, file, indent=4, ensure_ascii=False)
    fig = plt.figure(figsize=(21, 9))
    json_trip = {}
    for i in range(3):
        x = np.arange(200, 500)
        plt.plot(x, trip[i][200:500] * (cn.mb_config[i]['ppr']*4) /
                 360 + cn.mb_config[i]['ppr']*2, label=f'trip[{i}]')
        json_trip[f"{i}相"] = trip[i][200:500].tolist()
    name = f"tr'{get_time}"
    plt.legend()
    plt.savefig(fname=cn.data_path + name)
    with open(cn.data_path + name[:-4]+".json", 'w', encoding="utf-8") as file:
        json.dump(json_trip, file, indent=4,
                  ensure_ascii=False)
    # plt.show()


def _mb_single_complete(cur, switch, trip, cs_stamp, trip_stamp, cs_phase,
                        trip_phase, phase_has_data):
    cs_len = [len(t_cur) for t_cur in cur.values()]
    for phase, v in cs_phase.items():
        if not v:  # 电流开关[[0],[0],[0]],时间戳设为有数据的一组
            phase_has_data[phase] = False
            cur[phase] = [
                [0 for i in range(cn.mb_config[phase]['cs_dot'])] for i in range(3)]
            switch[phase] = [
                [0 for i in range(cn.mb_config[phase]['cs_dot'])] for i in range(3)]
            cs_stamp[phase] = cs_stamp[cs_len.index(max(cs_len))]
            mylogger.info(f'{phase}相 电流/开关: 已完成补相')
    trip_len = [len(t_trip) for t_trip in trip.values()]
    for k, v in trip_phase.items():
        if not v:  # 行程[0],时间戳设为有数据的一组
            trip[k] = [0 for i in range(max(trip_len))]
            trip_stamp[k] = trip_stamp[trip_len.index(max(trip_len))]
            mylogger.info(f'{k}相 行程: 已完成补相')


def _mb_correct(cur, switch, trip, cs_stamp, trip_stamp):
    cur_first = min(cs_stamp.values())  # 电流最早时间
    trip_len = max([len(temp_t) for temp_t in trip.values()])  # 行程数据长度
    trip_before_cur = [False, False, False]
    cs_head_zeros, trip_head_zeros, total_dot = {}, {}, [0, 0, 0]
    for t_phase, t_stamp in cs_stamp.items():  # 电流/辅助开关 位移点数列表
        cs_head_zeros[t_phase] = int(
            (t_stamp - cur_first) / (cn.mb_time_inter * 10**3))
    for t_phase, t_stamp in trip_stamp.items():  # 行程 位移点数列表
        trip_head_zeros[t_phase] = int(
            (t_stamp - cur_first) / (cn.mb_time_inter * 10**3))
        if trip_head_zeros[t_phase] < 0:
            trip_before_cur[t_phase] = True
    for phase, is_before in enumerate(trip_before_cur):
        if not is_before:
            total_dot[phase] = min(
                trip_head_zeros.values()) + trip_len  # 数据总长度
        else:
            total_dot[phase] = cn.mb_config[phase]['cs_dot']
    # region 校准电流
    for phase in range(3):
        head_zero = cs_head_zeros[phase]
        if head_zero > total_dot[phase]:  # 位移点数 > 长度 则清零
            for i in range(3):
                cur[phase][i] = np.array([0 for j in range(total_dot[phase])])
                switch[phase][i] = np.array(
                    [0 for j in range(total_dot[phase])])
        elif head_zero < total_dot[phase]:  # 位移点数 < 长度 则补0往后移动
            for i in range(3):
                moved_c, moved_s = [], []
                moved_c += [cur[phase][i][0] for index in range(head_zero)]
                moved_c += [cur[phase][i][index - head_zero]
                            for index in range(head_zero, head_zero + cn.mb_config[phase]['cs_dot'])]
                moved_c += [cur[phase][i][-1]
                            for index in range(head_zero + cn.mb_config[phase]['cs_dot'], total_dot[phase])]
                cur[phase][i] = np.array(moved_c)
                moved_s += [switch[phase][i][0] for index in range(head_zero)]
                moved_s += [switch[phase][i][index - head_zero]
                            for index in range(head_zero, head_zero + cn.mb_config[phase]['cs_dot'])]
                moved_s += [switch[phase][i][-1]
                            for index in range(head_zero + cn.mb_config[phase]['cs_dot'], total_dot[phase])]
                switch[phase][i] = np.array(moved_s)
    # endregion
    # region 校准行程
    for phase in range(3):
        head_zero = trip_head_zeros[phase]
        if head_zero >= total_dot[phase]:  # 位移点数 > 长度 则清零
            trip[phase] = np.array([0 for j in range(total_dot[phase])])
        elif 0 < head_zero < total_dot[phase]:  # 位移点数 < 长度 则补0往后移动
            trip[phase] = np.array([trip[phase][0] if index < head_zero else trip[phase][index - head_zero]
                                    for index in range(total_dot[phase])])
        elif 0 < -head_zero < trip_len:  # 超前电流 < 长度 则往前移动补0
            trip[phase] = np.array([trip[phase][-head_zero + index] if index < trip_len + head_zero
                                    else trip[phase][-1] for index in range(total_dot[phase])])
        elif -head_zero > trip_len:  # 超前电流 > 长度 则清零
            trip[phase] = np.array([0 for j in range(total_dot[phase])])
    # endregion
    # region 电流零漂/系数
    for phase in range(3):
        for j in range(3):
            if j == cn.close_order:
                cur[phase][j] = (cur[phase][j] - sh.find_base_value(cur[phase]
                                                                    [j], "close")) * cn.mb_config[phase]['close_cur_factor']
            elif j == cn.subsep_order:
                cur[phase][j] = (cur[phase][j] - sh.find_base_value(cur[phase]
                                                                    [j], "sep")) * cn.mb_config[phase]['subsep_cur_factor']
            elif j == cn.sep_order:
                cur[phase][j] = (cur[phase][j] - sh.find_base_value(cur[phase]
                                                                    [j], "sep")) * cn.mb_config[phase]['sep_cur_factor']
    # endregion
    # 行程曲线翻转 + 系数修改
    for phase in range(3):
        if cn.mb_config[phase]['trip_direction']:
            min_trip = min(trip[phase])
            trip[phase] = -(trip[phase] - min_trip) - min_trip
        trip[phase] = trip[phase] * cn.mb_config[phase]['trip_factor']


def _mb_draw_dot(cur, switch, trip, temp_vir, phase, get_time, close_i, sep_i, cur_close,
                 cur_sep, trip_tc, trip_ts, cur_close_tc, cur_close_ts,
                 cur_sep_tc, cur_sep_ts, cur_sec_tc, cur_sec_ts):
    label_cur = [
        '分闸线圈电流', '副分线圈电流', '合闸线圈电流'
    ]
    label_switch = ['分合闸开关', '', '']
    # fig = plt.figure(figsize=(8, 5))
    # ax = axisartist.Subplot(fig, 111)
    # fig.add_axes(ax)
    # # 零偏置处理
    # fig.add_axes(ax)
    # j = 0
    # x = range(len(cur[phase][j]))
    # plt.plot(x, cur[phase][j], c='red')
    # plt.xlabel(r'$ t/ms $')
    # plt.ylabel(r'$ i/A $')
    # plt.xlim(0, 3200)
    # plt.ylim(-0.1, 1.2)
    # xmajor = MultipleLocator(800)
    # xminor = MultipleLocator(400)
    # ymajor_1 = MultipleLocator(0.4)
    # yminor_1 = MultipleLocator(0.2)
    # ax.xaxis.set_minor_locator(xminor)
    # ax.xaxis.set_major_locator(xmajor)
    # ax.yaxis.set_minor_locator(yminor_1)
    # ax.yaxis.set_major_locator(ymajor_1)
    # ax.axis["top"].set_visible(False)
    # # ax.axis["left"].set_axisline_style("->", size=1.2)
    # ax.axis["right"].set_visible(False)
    # # ax.axis["bottom"].set_axisline_style("->", size=1.2)
    # plt.savefig(fname=cn.data_path + f'{phase}\'' + get_time)
    # # 滤波处理
    # j = 0
    # x = np.arange(0, 1100)
    # # y = [temp + random.uniform(-0.05, 0.05)
    # #      for temp in cur[phase][j][-1500:-400]]
    # y = []
    # temp = random.uniform(-0.05, 0.05)
    # for i in range(-1500, -400):
    #     if i % 2 == 0:
    #         y.append(cur[phase][j][i] + temp)
    #     else:
    #         y.append(cur[phase][j][i] - temp)
    #         temp = random.uniform(-0.02, 0.02)
    # y = [temp if temp > 0 else 0 for temp in y]
    # y[525] += 0.1
    # # y = sh.wave_smooth(y)
    # plt.plot(x, y, c='red')
    # plt.xlabel(r'$ t/ms $')
    # plt.ylabel(r'$ i/A $')
    # plt.xlim(0, 1200)
    # plt.ylim(-0.1, 0.8)
    # xmajor = MultipleLocator(300)
    # xminor = MultipleLocator(150)
    # ymajor_1 = MultipleLocator(0.2)
    # yminor_1 = MultipleLocator(0.1)
    # ax.xaxis.set_minor_locator(xminor)
    # ax.xaxis.set_major_locator(xmajor)
    # ax.yaxis.set_minor_locator(yminor_1)
    # ax.yaxis.set_major_locator(ymajor_1)
    # ax.axis["top"].set_visible(False)
    # # ax.axis["left"].set_axisline_style("->", size=1.2)
    # ax.axis["right"].set_visible(False)
    # # ax.axis["bottom"].set_axisline_style("->", size=1.2)
    # plt.savefig(fname=cn.data_path + f'{phase}\'' + get_time)
    fig = plt.figure(figsize=(16, 9), dpi=200)
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    plt.subplot(4, 1, 1)  # 电流图像
    for j in range(3):
        x = np.arange(0, len(cur[phase][j]))
        plt.plot(x, cur[phase][j] + j * 1.5, label=label_cur[j])
        plt.xlabel('t/ms')
        plt.ylabel('I/mA')
        plt.yticks([0,  1.5, 3.0], ['0', '0',  '0'])
        plt.legend(loc='upper right')
        for temp_cur in [cur_close_tc, cur_close_ts]:
            temp_cur = [p for p in temp_cur if p != 0]
            plt.scatter(temp_cur, [cur_close[u] +
                                   close_i * 1.5 for u in temp_cur])
        for temp_cur in [cur_sep_tc, cur_sep_ts]:
            temp_cur = [p for p in temp_cur if p != 0]
            plt.scatter(
                temp_cur, [cur_sep[u] + sep_i * 1.5 for u in temp_cur])
        for temp_cur in [cur_sec_tc, cur_sec_ts]:
            temp_cur = [p for p in temp_cur if p != 0]
            plt.scatter(
                temp_cur, [cur_sep[u] + sep_i * 1.5 for u in temp_cur])
    plt.subplot(4, 1, 2)  # 辅助开关图像
    for j in range(3):
        plt.plot(x, switch[phase][j] + j * 1.5, label=label_switch[j])
        plt.xlabel('t/ms')
        plt.yticks([], [])
        plt.legend(loc='upper right')
    x = np.arange(0, len(trip[phase]))
    plt.subplot(4, 1, 3)  # 行程图像
    plt.plot(x, trip[phase], label=f'trip')
    plt.xlabel('t/ms')
    plt.ylabel('s/mm')
    plt.legend(loc='upper right')
    for temp_trip in [trip_tc, trip_ts]:
        temp_trip = [p for p in temp_trip if p != 0]
        plt.scatter(temp_trip, [trip[phase][u] for u in temp_trip])
    plt.subplot(4, 1, 4)  # 断口曲线
    plt.plot(x, temp_vir[phase], label=f'virtual')
    plt.legend(loc='upper right')
    plt.savefig(fname=cn.data_path + f'{phase}\'' + get_time)


def _get_es(is_cur: bool, datalist: list):
    """
    拆分三相电流,三个两路弹簧
    :param datalist:
    :return: cur:[np,np,np]  or  spring:[[分],[合]]
    """
    if is_cur:
        cur = []
        for i in range(3):
            temp_cur = (np.array(
                (datalist[i * cn.es_cur_dot:(i + 1) * cn.es_cur_dot])) * 3.3 / 4096 - 1.633) \
                * 15 / 0.625 * cn.es_cur_factors[i]
            cur.append(temp_cur)
        return cur
    else:
        spring = []
        data_len = int(len(datalist) / 2)
        for i in range(2):
            spring.append(
                (np.array(datalist[i * data_len:(i + 1) * data_len])
                 / 4096 * 3.3) / 66 * 1000 * 1.9445)
        spring[0][-7:] = spring[0][-14:-7]
        spring[1][:7] = spring[1][7:14]
        return spring


def _es_s_handle(spring_group: list):
    """
    处理仅有弹簧: 每相单独录入
    情况: 实时 + 分闸
    """
    module, location, num, doi, phase, infolist, datalist = spring_group
    if infolist:
        spring = _get_es(False, datalist)
        es_data = copy.deepcopy(cn.es_data)
        real_time, status_flag, status, act_name = 0, 0, '正常', ''
        # es_state = dbh.select_data(module, location, 0,'储能状态')[0][0]
        # 没有动作
        if len(spring[0]) == (100 - 14) / 2:
            real_time = 1
            es_data['分弹簧压力'][2] = \
                round(np.average(spring[0]), 2)
            es_data['合弹簧压力'][2] = \
                round(np.average(spring[1]), 2)
            if es_data['合弹簧压力'][2] >= cn.es_spring_max:
                es_data['储能状态'][2] = 1
            elif es_data['合弹簧压力'][2] < cn.es_spring_max:
                es_data['储能状态'][2] = 0
        # 分闸: 无电流 无异常
        elif len(spring[0]) == (12000 - 14) / 2:
            act_name = '分闸'
            # es_state = 0
        # 所有情况
        es_data['分弹簧压力最大值'][2] = round(np.max(spring[0]), 2)
        es_data['合弹簧压力最大值'][2] = round(np.max(spring[1]), 2)
        count = dbh.select_data(module, location, 0,
                                '储能次数')[0][0]
        es_data['储能次数'][2] = int(count)
        # region 绘制图片
        # plt.figure(figsize=(16, 9))
        # plt.subplot(211)
        # x = range(0, len(spring[0]))
        # plt.plot(x, spring[0])
        # plt.subplot(212)
        # x = range(0, len(spring[1]))
        # plt.plot(x, spring[1])
        # get_time = time.localtime(
        #     int(_get_timestamp(infolist) / (10**6)))
        # get_time = time.strftime(
        #     "%Y-%m-%d %H'%M'%S", get_time) + '.png'
        # plt.savefig(fname=cn.data_path + f'es\'{phase}\'' + get_time)
        # for i in range(2):
        #     spring[i] = spring[i].tolist()
        # with open(cn.data_path + f"/es\'{phase}\'{get_time[:-4]}.json", 'w') as file:
        #     json.dump(spring, file, indent=4)
        # endregion
        curve_data = {}
        if len(spring[0]) != (100 - 14) / 2:
            curve_data = {
                'spring_sep': spring[0].tolist(),
                'spring_close': spring[1].tolist()
            }
        dbh.add_update(cn.modules[3], location, 0, 1, real_time, infolist,
                       act_name, status_flag, status, es_data, curve_data)


def _es_cs_handle(spring_group: list, cur_list: list):
    """
    处理同时有电流和弹簧: 弹簧数据长度 => 第n相动作 => 取出第n相电流
    情况: 合闸
    """
    module, location, num, doi, phase, infolist, datalist = spring_group
    if infolist:
        # if doi[0] == 7:
        #     cur = _get_es(True, datalist)  # 默认abc
        spring = _get_es(False, datalist)
        es_data = copy.deepcopy(cn.es_data)
        real_time, status_flag, status, act_name = 0, 0, '正常', ''
        # 没有动作
        if len(spring[0]) == (100 - 14) / 2:
            real_time = 1
            es_data['分弹簧压力'][2] = \
                round(np.average(spring[0]), 2)
            es_data['合弹簧压力'][2] = \
                round(np.average(spring[1]), 2)
            if es_data['合弹簧压力'][2] >= cn.es_spring_max:
                es_data['储能状态'][2] = 1
            elif es_data['合弹簧压力'][2] < cn.es_spring_max:
                es_data['储能状态'][2] = 0
        # 合闸 (有电流,不会是合闸)
        elif len(spring[0]) == (12000 - 14) / 2:
            _, _, _, _, _, _, c_datalist = cur_list
            cur_three = _get_es(True, c_datalist)
            # 取出弹簧相对应的电流
            cur = cur_three[phase]
            # 交流电转有效值
            # cur = cur - np.average(cur[0:10])
            cur_dot = int(20 / (1 / cn.es_frequency))
            cur = np.array([np.sqrt(np.sum(np.power(cur[i:i+cur_dot], 2) / cur_dot))
                            for i in range(len(cur) - cur_dot)])
            cur_begin_dots, _ = sh.find_turn_dot(
                cur, *cn.es_find_begin)
            _, cur_stop_dots = sh.find_turn_dot(
                cur, *cn.es_find_end)
            # 起止点
            cur_begin_index, cur_stop_index = cur_begin_dots[0], cur_stop_dots[1]
            # 中间下陷点
            cur_begin_front = cur_begin_index + 50
            cur_mid_min = np.argmin(
                cur[cur_begin_front:int(cn.es_cur_dot/2)]) + cur_begin_front
            # region 绘图
            # plt.figure(figsize=(15, 4.8))
            # # plt.plot(range(len(cur)), cur)
            # # for index in cur_begin_dots:
            # #     plt.scatter(cur_begin_dots[0],
            # #                 cur[cur_begin_dots[0]], c='red')
            # # for index in cur_stop_dots:
            # #     plt.scatter(cur_stop_dots[1],
            # #                 cur[cur_stop_dots[1]], c='blue')
            # # plt.scatter(cur_mid_min,
            # #             cur[cur_mid_min], c='green')
            # plt.plot(range(len(spring[0])), spring[0])
            # plt.plot(range(len(spring[1])), spring[1])
            # plt.show()
            # endregion
            es_data['启动电流'][2] = round(np.max(cur), 2)
            es_data['启动时间'][2] = round(cur_begin_index * cn.es_T, 2)
            cur_mid_length = cur_stop_index - cur_begin_index
            cur_mid_20 = int(cur_begin_index + cur_mid_length * 0.2)
            cur_mid_90 = int(cur_begin_index + cur_mid_length * 0.9)
            es_data['储能电机电流'][2] = round(np.average(
                cur[cur_mid_20:cur_mid_90]), 2)
            es_data['储能状态'][2] = 1
            es_data['储能时间'][2] = round(cur_stop_index - cur_begin_index, 2)
            count = dbh.select_data(module, location, 0,
                                    '储能次数')[0][0]
            es_data['储能次数'][2] = int(count + 1)
            act_name = '合闸'
            if es_data['启动电流'][2] > cn.es_cur_max:
                status_flag, status = 1, '电机电流异常'
            if round(np.max(spring[1]), 2) < cn.es_spring_max:
                status_flag, status = 1, '储能异常'
                es_data['储能状态'][2] = 0
        # 所有情况
        es_data['分弹簧压力最大值'][2] = round(np.max(spring[0]), 2)
        es_data['合弹簧压力最大值'][2] = round(np.max(spring[1]), 2)
        curve_data = {
            'spring_sep': spring[0].tolist(),
            'spring_close': spring[1].tolist(),
            'cur': cur.tolist()
        }
        dbh.add_update(cn.modules[3], location, 0, 1, real_time, infolist,
                       act_name, status_flag, status, es_data, curve_data)


def es():
    """
    储能模块: 
        - 数据收入: [[弹簧], 电流]
        - 数据情况: 
            - 弹簧: 没动作43+43; 动作
            - 电流、开关: 只有合闸才有; 3+3
        - 数据输出: 界面三个
    Record表: n x (3 x ...)
    ResultCal表: n x (3 x 10行量值)
    curve表: n x (3 x {'spring_sep':[], 'spring_close':[], 'cur':[]})
    """
    for data_group in rh.read_files(cn.func_es):
        # 不含电流 (正常情况 + 分闸)
        if len(data_group) == 1:
            _es_s_handle(data_group[0])
        # 包含电流 (合闸)
        elif len(data_group) == 2:
            _es_cs_handle(data_group[0], data_group[1])


def _get_vb(is_bus: bool, datalist: list):
    """
    对振动进行数值转换
    :return: 断路器:[]  or  母线:[[x],[y],[z]]
    """
    if is_bus:  # 母线
        datalist = np.array(datalist) * 3.3 / (1.8 * 1024) - 2
        return datalist[0:3995], datalist[3995:3995 * 2], datalist[3995 *
                                                                   2:3995 * 3]
    else:  # 断路器
        return 100 * np.array(datalist) / 4096 - 50


def vb():
    """
    振动模块:注意是一个模块三个编号,但单独工作(断路器单轴、母线三轴需要区分)
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 4行量值)
    curve表-母线: n x (1 x {{'x':{'data':[], 'abs':[], 'angle':[]},
                            {'y':{'data':[], 'abs':[], 'angle':[]},
                            {'z':{'data':[], 'abs':[], 'angle':[]} })
    curve表-断路器: n x (1 x {'data':[], 'abs':[], 'angle':[]})
    """
    for module, location, num, doi, phase, infolist, datalist in rh.read_files(
            cn.func_vb):
        if infolist:
            datalist = datalist[:-1]
            vb_data = copy.deepcopy(cn.vb_data)
            db_curve, curve_data = {}, {}
            fs = cn.vb_frequency * 1000
            if doi[-1] >= 6:  # 断路器
                curve_data['x'] = {
                    'data': _get_vb(False, datalist),
                    'abs': sh.wave_fft(datalist)[0],
                    'angle': sh.wave_fft(datalist)[1]
                }
                vb_data['加速度'][2] = round(
                    max(np.abs(curve_data['x']['data'])), 2)
                act_name = ''
                status = '正常'
            else:  # 母线
                curve_data = {'x': {}, 'y': {}, 'z': {}}
                curve_data['x']['data'], curve_data['y']['data'], curve_data[
                    'z']['data'] = _get_vb(True, datalist)
                data_i = 2
                for temp_value in curve_data.values():
                    temp_value['abs'] = sh.wave_fft(
                        temp_value['data'])[0]
                    temp_value['angle'] = sh.wave_fft(
                        temp_value['data'])[1]
                    vb_data['加速度'][data_i] = round(
                        max(np.abs(temp_value['data'])), 2)
                    data_i += 1
                act_name = ''
                status = '正常'
            for temp_phase, one_phase in curve_data.items():
                fig = plt.figure()
                fig.subplots_adjust(left=0.1, right=0.95,
                                    bottom=0.1, top=0.95, hspace=0.4)
                ax1 = fig.add_subplot(3, 1, 1)
                x = np.arange(0, len(one_phase['data']))
                y1 = np.array(one_phase['data'])
                y1 = y1 - np.median(one_phase['data'])
                ax1.plot(x, y1)
                ax1.set_ylabel('m/s²')
                ax1.set_xlabel('T/s')
                fx = np.linspace(1, fs, len(one_phase['abs']))  # 横轴频率计算
                ax2 = fig.add_subplot(3, 1, 2)
                ax2.plot(fx, one_phase['abs'])
                ax2.set_xlabel('f/Hz')
                ax3 = fig.add_subplot(3, 1, 3)
                ax3.plot(fx, one_phase['angle'])
                ax3.set_xlabel('f/Hz')
                # plt.show()
                plt.savefig(fname=cn.data_path +
                            _get_name(_get_timestamp(infolist), doi, temp_phase))
                imfs, res, E_Imfs = sh.getE_Imfs(one_phase['data'])
                # 绘制 IMF
                include_residue = True
                num_rows, t_length = imfs.shape
                num_rows += include_residue is True
                t = range(t_length)
                fig, axes = plt.subplots(
                    num_rows, 1, figsize=(8, num_rows * 1.5))
                if num_rows == 1:
                    axes = list(axes)
                for num, imf in enumerate(imfs):
                    ax = axes[num]
                    ax.plot(t, imf)
                    ax.set_ylabel("IMF " + str(num + 1))
                if include_residue:
                    ax = axes[-1]
                    ax.plot(t, res)
                    ax.set_ylabel("Res")
                plt.tight_layout()
                plt.savefig(fname=cn.data_path +
                            _get_name(_get_timestamp(infolist), doi, f"{temp_phase}-imf"))
                # 特征值
                for i, value in enumerate(E_Imfs):
                    if not vb_data.get(f'IMF{i+1}'):
                        vb_data[f'IMF{i+1}'] = ['m²/s', 1]
                        if temp_phase == 'y':
                            vb_data[f'IMF{i+1}'].append(0)
                        elif temp_phase == 'z':
                            vb_data[f'IMF{i+1}'] += [0, 0]
                    vb_data[f'IMF{i+1}'].append(value)
                # 曲线
                db_curve[temp_phase] = {}
                for keys, values in one_phase.items():
                    values = values.tolist()
                    db_curve[temp_phase][keys] = [values[j]
                                                  for j in range(len(values)) if j % 5 == 0]
                # db_curve['imfs'] = []
                # for one_curve in imfs:
                #     db_curve['imfs'].append(one_curve.tolist())
            dbh.add_update(module, location, num, 1, 0, infolist, act_name, 0,
                           status, vb_data, db_curve)


def la():
    pass


# 图片是否需要存储 and 局放和视频的普遍问题 => 图片覆盖
def touch():
    """
    触头模块: 一个位置三个传感器,但每个单独工作
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 2行量值)
    curve表: n x (1 x {'名1':值1 , ...})
    """
    for module, location, num, doi, phase, infolist, datalist in rh.read_files(
            cn.func_touch):
        if infolist:
            touch_data = copy.deepcopy(cn.touch_data)
            pic_data, red_data = datalist[0], datalist[1]
            # print(''.join(map(lambda x: ('/x' if len(hex(x))
            #                              >= 4 else '/x0')+hex(x)[2:], pic_data[:10])))
            # 视频(帧内bug)
            pic_data = pic_data[:4] + pic_data[7:]
            video_name = cn.data_path + \
                _get_name(_get_timestamp(infolist), doi, "v")
            if os.path.exists(video_name):
                with open(video_name, "wb+") as file_pic:
                    file_pic.write(pic_data)
            else:
                with open(video_name, "ab+") as file_pic:
                    file_pic.write(pic_data)
            # plt.subplot(121)
            # try:
            #     plt.imshow(plt.imread(cn.touch_pic_temp), aspect='auto')
            # except TypeError as e:
            #     print(e.args)
            # 红外
            red_list, red_data = [], binascii.b2a_hex(red_data)[:-16]
            for x in range(0, len(red_data), 4):
                red_list.append(
                    int(red_data[x + 2:x + 4] + red_data[x:x + 2], 16) / 100)
            red_list = red_list[:-1]
            red_np = np.array(red_list).reshape(24, 32)
            red_np[0, 0] = red_np[0, -1]  # 红外程序bug修复
            for x in range(4):
                red_np = np.repeat(red_np, 2, axis=1)[:, :-1]
                red_np[:, 1::2] = (red_np[:, 2::2] + red_np[:, 1::2]) / 2
            for x in range(4):
                red_np = np.repeat(red_np, 2, axis=0)[:-1, :]
                red_np[1::2, :] = (red_np[2::2, :] + red_np[1::2, :]) / 2
            red_np = np.flip(red_np, axis=1)
            # plt.subplot(122)
            fig = plt.figure(figsize=(6, 4.8))
            fig.subplots_adjust(left=0.07, right=1.05, bottom=0.08, top=0.95)
            plt.imshow(red_np, cmap="jet", aspect='auto')
            max_index = np.unravel_index(
                np.argmax(red_np, axis=None), red_np.shape)
            for i in range(100, 150):
                plt.scatter(max_index[1], max_index[0],
                            marker='o', c='none', edgecolors='k', s=i)
            plt.colorbar()
            red_name = cn.data_path + \
                _get_name(_get_timestamp(infolist), doi, "r")
            plt.savefig(red_name)
            touch_data['温度'][2] = np.max(red_np)
            touch_data['位置'][2] = th.breaking_identify(video_name)
            real_time, status_flag, status, act_name = 0, 0, '正常', ''
            dbh.add_update(module, location, num, 1, real_time, infolist, act_name, status_flag,
                           status, touch_data)


def ev():
    """
    环境模块:注意是一个模块测三个机构,即由三相 变为 三位置
    Record表: n x (1 x ...)
    ResultCal表: n x (1 x 2行量值)
    curve表: n x (1 x {'名1':值1 , ...})
    """
    for module, location, num, doi, phase, infolist, datalist in rh.read_files(
            cn.func_ev):
        if infolist:
            real_time, status_flag, status, act_name = 0, 0, '正常', ''
            ev_data = copy.deepcopy(cn.ev_data)
            ev_data['温度'][2] = round((datalist[0] * 3.3 / 4095 -
                                      1.25) * 10 * 6.25 - 55, 1)
            ev_data['湿度'][2] = round((datalist[1] * 3.3 / 4095 -
                                      1.25) * 10 * 6.25 - 25, 1)
            if ev_data['温度'][2] > cn.env_temp_high:
                status_flag, status = 1, '温度过高'
            elif ev_data['温度'][2] < cn.env_temp_low:
                status_flag, status = 1, '温度过低'
            if ev_data['湿度'][2] > cn.env_humidity:
                status_flag, status = 1, '湿度过高'
            dbh.add_update(module, location, num, 1, real_time, infolist, act_name, status_flag,
                           status, ev_data, None, _get_timestamp(infolist))


def si():
    pass


if __name__ == "__main__":
    gas()
    pd()
    ms()
    mb()
    vb()
    touch()
    ev()
    # 储能最后防卡线程 + 不会无限开新线程(需要等待20s再检测)
    es()

    dbh.conn.close()
