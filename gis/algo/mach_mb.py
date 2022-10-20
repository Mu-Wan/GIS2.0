"""
机械特性-断路器模块
"""
from input.read_module import read_mb_file
from algo.utils import *
import algo.curve_utils as cu
from namespace import constant as cn
from namespace import algo_param as ap

import numpy as np
from typing import Iterable

springCloseMax = cn.eConfig['es']['spring']['closeMax']
curMax = cn.eConfig['es']['cur']['max']
sampleT = 1 / cn.bConfig['es']['base']['rate']


def mb1time() -> Iterable[OutData]:
    """ 处理一次扫描的所有机械特性-断路器文件
    param
    return
        OutData, ......
    """
    # (spring, cur)
    # spring.data = [[分],[合]]
    for sData, cData in read_mb_file():


def __handle_one_norm(sensorData) -> OutData:
    """ 处理机械特性-断路器的数据
    param
        sensorData: 弹簧数据
    return
        OutData
    """
    splitData, closeData = springData.data
    # 算法处理
    outDict = {'split_spring_pressure': round(np.average(splitData), 2),
               'closing_spring_pressure': round(np.average(closeData), 2),
               'state': 100,
               'exception': '',
               'step': '',
               'remark': ''}
    return OutData(springData, outDict)


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
            get_time = time.localtime(int(max(cs_stamp.values()) / (10 ** 6)))
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
                        cur_sep[:int(len(cur_sep) / 2)], *cn.sep_cur_find)  # 电流 一分
                    if cur_sep_tc[0] != 0 and cur_sep_ts[-1] != 0:
                        trip_tc, trip_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][:int(cur_close_tc[0])]), *cn.trip_sep_find)  # 行程 重合闸的一分
                    else:
                        trip_tc, trip_ts = sh.find_turn_dot(
                            trip[phase], *cn.trip_close_find)  # 行程 仅合闸
                    cur_sec_tc, cur_sec_ts = sh.find_turn_dot(
                        cur_sep[cur_close_tc[0]:], *cn.sep_cur_find)  # 电流 二分
                    if cur_sep_tc[0] != 0 and cur_sep_ts[-1] != 0:
                        cur_sec_tc = [temp + cur_close_tc[0]
                                      for temp in cur_sec_tc]
                        cur_sec_ts = [temp + cur_close_tc[0]
                                      for temp in cur_sec_ts]
                        trip_close_tc, trip_close_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][cur_close_tc[0]:cur_sec_ts[1]]),
                            *cn.trip_close_find)  # 行程 重合闸的合闸
                        trip_sec_tc, trip_sec_ts = sh.find_turn_dot(
                            sh.trip_wave_smooth(trip[phase][cur_sec_tc[0]:]), *cn.trip_sec_find)  # 行程 重合闸的二分
                        trip_tc += [trip_close_tc[0] + cur_close_tc[0],
                                    trip_sec_tc[1] + cur_sec_tc[0]]
                        trip_ts += [trip_close_ts[0] + cur_close_tc[0],
                                    trip_sec_ts[1] + cur_sec_tc[0]]
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
                elif op_kind == 6:  # 无数据不操作
                    mylogger.info(f'{phase}相: 无数据')
                else:
                    try:
                        if op_kind != 1:  # 除合闸外均有分闸过程
                            try:
                                mb_data['一分行程量'][2 + phase] = round(
                                    abs(trip[phase][t_sep_stop_index] - trip[phase][t_sep_begin_index]) *
                                    cn.mb_config[phase]['trip_sep_factor'], 2)
                                virtual_high = (trip[phase][t_sep_stop_index] - trip[phase][t_sep_begin_index]) * \
                                               cn.mb_config[phase]['sep_vir_per'] + \
                                               trip[phase][t_sep_begin_index]
                                virtual_sep = np.argmin(
                                    abs(trip[phase][
                                        t_sep_begin_index:t_sep_stop_index] - virtual_high)) + t_sep_begin_index
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
                                if mb_data['一分行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['一分行程量'][
                                    2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['一分时间'][2 + phase] < cn.mb_diag['sep_time_min'] or mb_data['一分时间'][
                                    2 + phase] > cn.mb_diag['sep_time_max']:
                                    status += f"{phase_name[phase]}相分闸时间异常;"
                                if mb_data['一分速度'][2 + phase] < cn.mb_diag['sep_v_min'] or mb_data['一分速度'][
                                    2 + phase] > cn.mb_diag['sep_v_max']:
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
                                    abs(trip[phase][t_close_stop_index] - trip[phase][t_close_begin_index]) *
                                    cn.mb_config[phase]['trip_close_factor'], 2)
                                virtual_high = (trip[phase][t_close_stop_index] - trip[phase][t_close_begin_index]) * \
                                               cn.mb_config[phase]['close_vir_per'] + \
                                               trip[phase][t_close_begin_index]
                                virtual_close = np.argmin(
                                    abs(trip[phase][
                                        t_close_begin_index:t_close_stop_index] - virtual_high)) + t_close_begin_index
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
                                if mb_data['合行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['合行程量'][
                                    2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['合时间'][2 + phase] < cn.mb_diag['close_time_min'] or mb_data['合时间'][
                                    2 + phase] > cn.mb_diag['close_time_max']:
                                    status += f"{phase_name[phase]}相合闸时间异常;"
                                if mb_data['合速度'][2 + phase] < cn.mb_diag['close_v_min'] or mb_data['合速度'][
                                    2 + phase] > cn.mb_diag['close_v_max']:
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
                                                                                  t_sec_stop_index] - trip[phase][
                                                                                  t_sec_begin_index]) *
                                                                             cn.mb_config[phase]['trip_sep_factor'], 2))
                                virtual_high = (trip[phase][t_sec_stop_index] - trip[phase][t_sec_begin_index]) * \
                                               cn.mb_config[phase]['sep_vir_per'] + \
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
                                if mb_data['二分行程量'][2 + phase] < cn.mb_diag['trip_min'] or mb_data['二分行程量'][
                                    2 + phase] > cn.mb_diag['trip_max']:
                                    status += f"{phase_name[phase]}相行程异常;"
                                if mb_data['二分时间'][2 + phase] < cn.mb_diag['sep_time_min'] or mb_data['二分时间'][
                                    2 + phase] > cn.mb_diag['sep_time_max']:
                                    status += f"{phase_name[phase]}相分闸时间异常;"
                                if mb_data['二分速度'][2 + phase] < cn.mb_diag['sep_v_min'] or mb_data['二分速度'][
                                    2 + phase] > cn.mb_diag['sep_v_max']:
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
    with open(cn.data_path + name[:-4] + ".json", 'w', encoding="utf-8") as file:
        json.dump(json_cur, file, indent=4, ensure_ascii=False)
    fig = plt.figure(figsize=(21, 9))
    json_trip = {}
    for i in range(3):
        x = np.arange(200, 500)
        plt.plot(x, trip[i][200:500] * (cn.mb_config[i]['ppr'] * 4) /
                 360 + cn.mb_config[i]['ppr'] * 2, label=f'trip[{i}]')
        json_trip[f"{i}相"] = trip[i][200:500].tolist()
    name = f"tr'{get_time}"
    plt.legend()
    plt.savefig(fname=cn.data_path + name)
    with open(cn.data_path + name[:-4] + ".json", 'w', encoding="utf-8") as file:
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
            (t_stamp - cur_first) / (cn.mb_time_inter * 10 ** 3))
    for t_phase, t_stamp in trip_stamp.items():  # 行程 位移点数列表
        trip_head_zeros[t_phase] = int(
            (t_stamp - cur_first) / (cn.mb_time_inter * 10 ** 3))
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
                                                                    [j], "close")) * cn.mb_config[phase][
                                    'close_cur_factor']
            elif j == cn.subsep_order:
                cur[phase][j] = (cur[phase][j] - sh.find_base_value(cur[phase]
                                                                    [j], "sep")) * cn.mb_config[phase][
                                    'subsep_cur_factor']
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
        plt.yticks([0, 1.5, 3.0], ['0', '0', '0'])
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
