import struct
import os
import shutil
import platform
import threading
from collections import deque

import name_place as cn
from logger import mylogger

import time
'''
完成文件内容读取,并转为对应的float/int数组
'''


def read_files(func_name: str, pd_num: int = 0):
    """
    各模块输入汇总:
        485: (有帧头帧尾)
            - 气体: 00-1f
                单文件
                [数值] 
            - 隔离开关: 40-4f
                单文件
                [交流电x3(三个位置) 辅助开关x3(对应三个位置)]
            - 机械特性(断路器): 50-5f(电流开关) / 60-6f(行程)
                双文件x3
                [(单相)行程]x3 [(单相)电流x3 + 开关x3(分 合 副分)]x3
            - 储能: 70-7f(电流开关) / 80-8f(弹簧)
                不动作: 三文件 [分,合(100)]x3(相)
                动作:
                    分闸: 三文件 [分,合(1.2w)]x3(相)
                    合闸: 3+1文件 [分,合(1.2w)]x3(相) [交流电x3相]
            - 振动: (3传感器测一位置)
                母线: 90-95
                    单文件 
                断路器: 96-9f
                    单文件 
            - 环境: d0-ff
                单文件
                [数值]
        网口: (无帧头帧尾)
            - 局放: 20-2f(超) / 30-3f(特)
                单文件
                [脉冲]
            - 触头: c0-cf (3传感器测一位置)
                单文件
                [视频 0xffff 红外]
    :return: 注意两种返回值
            单文件: module, location, num, (doi_high, doi_low)(区别传感器), phase_count, infolist, datalist
            多文件: [ [...] , [...] , ...] => 依据mod\loc\doi区分
    """
    # 所有文件
    file_list = os.listdir(cn.data_sec_path)
    file_list = [file for file in file_list if file.lower().find('done') == -1]
    mod_doi = cn.mod_doi[func_name]
    # 局放: 统计
    if func_name == cn.func_pd:
        file_list = [x for x in file_list
                     if (_get_doi(x, 0) in mod_doi) and (_get_doi(x, 1) == pd_num)]  # 对应区间段筛选
        file_list.sort(key=_get_time)
        for file_name in file_list:
            module, location, num, doi, phase, infolist, datalist = \
                _read_1file(func_name, file_name)
            yield module, location, num, doi, phase, infolist, datalist
    # 储能: 三相独立 1 + 0/1
    elif func_name == cn.func_es:
        # 分组 [弹簧,(电流)]
        cur_list = [x for x in file_list if _get_doi(x, 0) == mod_doi[0]]
        force_list = [x for x in file_list if _get_doi(x, 0) == mod_doi[1]]
        t_list, result_list = [], []
        for force_one in force_list:
            # 被定时器加载的 不再执行
            if 'load' not in force_one.lower():
                # 动作: 必须电流文件
                if os.path.getsize(cn.data_sec_path + force_one) > 15 * (10**3):
                    has_cur = False
                    for cur_file in cur_list:
                        if _match_time(cur_file, force_one, cn.es_per):
                            has_cur = True
                            yield [_read_1file(func_name, force_one),
                                   _read_1file(func_name, cur_file, False)]
                            break
                    # 无则定时器等待
                    if not has_cur:
                        file_path = cn.data_sec_path + force_one
                        os.rename(file_path, file_path + '-load')
                        t = threading.Timer(cn.es_per, es_wait,
                                            [mod_doi, force_one + '-load', func_name, result_list])
                        t_list.append(t)
                        t.start()
                # 不动作: 直接生成
                else:
                    yield [_read_1file(func_name, force_one)]
        # 等待本次动作执行完
        has_t = False
        for t in t_list:
            t.join()
            has_t = True
        # 把电流清空
        if has_t:
            file_list = os.listdir(cn.data_sec_path)
            cur_list = [x for x in file_list if _get_doi(x, 0) == mod_doi[0]]
            for cur_file in cur_list:
                if 'done' not in cur_file.lower():
                    file_path = cn.data_sec_path + cur_file
                    os.rename(file_path, file_path + 'Done')
                    remove_file(file_path + 'Done')
        for result in result_list:
            yield result
    # 机械特性(断路器): 3 + 3
    elif func_name == cn.func_mb:
        # 行程[] 电流[]
        cur_list, trip_list = [x for x in file_list if _get_doi(x, 0) == mod_doi[0]], \
                              [x for x in file_list if _get_doi(x, 0) == mod_doi[1]]
        # [cur_a[], b[], c[], trip_a[], b[], c[]]
        search_list = []
        for i in range(3):
            cur_phase = deque([x for x in cur_list if _get_doi(x, 1) == i])
            search_list.append(cur_phase)
        for i in range(3):
            trip_phase = deque([x for x in trip_list if _get_doi(x, 1) == i])
            search_list.append(trip_phase)
        # [[a,b,c,a,b,c], [], [], ...]
        file_list = []
        for i in range(6):
            while len(search_list[i]) != 0:
                one_phase = search_list[i].pop()
                one_time = [one_phase]
                for j in range(6):
                    if i == j:
                        continue
                    else:
                        none_match = True
                        for k in range(len(search_list[j])):
                            if _match_time(one_phase, search_list[j][k]):
                                match_value = search_list[j][k]
                                one_time.append(match_value)
                                search_list[j].remove(match_value)
                                none_match = False
                                break
                        if none_match:
                            if j >= 3:
                                one_time.append(f"0x6{j % 3}" + one_phase[4:])
                            else:
                                one_time.append(f"0x5{j % 3}" + one_phase[4:])
                one_time.sort()
                file_list.append(one_time)
        # 读取
        for one_time_list in file_list:
            yield _read_3file(func_name, one_time_list)
    # 剩余: 单文件
    else:
        file_list = [x for x in file_list
                     if _get_doi(x, 0) in mod_doi]  # 对应区间段筛选
        for file_name in file_list:
            yield _read_1file(func_name, file_name)


def es_wait(mod_doi, force_one, func_name, result_list):
    """
    储能模块延时读取
    """
    file_list = os.listdir(cn.data_sec_path)
    cur_list = [x for x in file_list if _get_doi(x, 0) == mod_doi[0]]
    # 合闸
    is_sep = True
    for cur_file in cur_list:
        if _match_time(cur_file, force_one, cn.es_per):
            is_sep = False
            result_list.append([_read_1file(func_name, force_one),
                                _read_1file(func_name, cur_file, False)])
            break
    # 分闸
    if is_sep:
        result_list.append([_read_1file(func_name, force_one)])


def _get_doi(name: str, loc: int):
    """
    :param name: 文件名
    :param loc: 高低位(0高,1低)
    :return:
    """
    return int(name.split('_')[0][loc - 2], 16)


def _get_time(name: str):
    """局放需要先排序"""
    time_list = name.split('_')[1].split('-')
    time_list[-1] = time_list[-1].lower().split('done')[0]
    ms, us = time_list[-2:]
    time_str = '-'.join(time_list[:-2])
    timestamp = time.mktime(time.strptime(time_str, "%Y-%m-%d-%H-%M-%S"))
    timestamp *= 10**6
    return timestamp + int(ms) * 10**3 + int(us)


def _read_1file(func_name: str, file_name: str, do_done: bool = True):
    """
    无需匹配的模块
    单文件、单编号: 气体、机械-隔离开关、避雷器、环境
    单文件、多编号: 振动、触头
    双文件: 局放
    :return: module, location, num, (doi_high, doi_low)(区别传感器), phase_count, infolist, datalist
    """
    module, location, num = cn.func_mod[func_name], '', 0
    doi_high, doi_low = _get_doi(file_name, 0), _get_doi(file_name, 1)
    phase = 0
    if func_name == cn.func_es:  # 储能特殊
        phase = doi_low % 3
    if func_name in [cn.func_vb, cn.func_touch]:
        location = cn.mod_loc_data[module][0][doi_low // 3][0]
        num = doi_low % 3
    else:
        if module == "气体":
            doi_low -= 1
        location, num = cn.mod_loc_data[module][0][doi_low]
        num -= 1
    infolist, datalist = [], []
    if func_name == cn.func_touch:
        infolist, datalist = _read_touch(file_name)
    elif func_name == cn.func_pd:
        infolist, datalist = _read_pd(file_name)
    else:
        # _read_485(file_name, module)
        infolist, datalist = _read_485(file_name, module, do_done)
    return module, location, num, (doi_high,
                                   doi_low), phase, infolist, datalist


def _read_3file(func_name: str, one_time_list: list, do_done: bool = True):
    """
    1+3文件:储能
    3+3文件:机械-断路
    :return: [module, location, num, (doi_high, doi_low), phase_count, infolist, datalist] x n
    """
    one_time = []
    for file_name in one_time_list:
        doi_high, doi_low = _get_doi(file_name, 0), _get_doi(file_name, 1)
        module, num, phase = cn.func_mod[func_name], 0, doi_low % 3
        if doi_high == cn.mod_doi[cn.func_es][0]:  # 储能电流一测三
            location = '断路器三相'
        elif doi_high in cn.mod_doi[cn.func_mb]:
            location = cn.mc_loc[-1][0]
        else:
            location = cn.mod_loc_data[module][0][doi_low][0]
        # 有文件
        if os.path.exists(cn.data_sec_path + file_name):
            infolist, datalist = _read_485(file_name, module, do_done)
        # 补相无文件: 空数据
        else:
            infolist = [int(temp) for temp in file_name[5:].split('-')]
            if file_name[2] == '5':
                datalist = [0 for i in range(cn.mb_config[0]['cs_dot'] * 4 - 14)]
            else:
                datalist = [0 for i in range(3000 - 14)]
        one_time.append([
            module, location, num, (doi_high, doi_low), phase, infolist, datalist
        ])

    return one_time


def _read_485(file_name: str, module: str, do_done: bool):
    """
    485存下的文件
    :param file_name: 文件名=>生成路径
    :param module: 模块=>区分解析方式
    :return: [帧头], [数据]
    """
    info_list, data_list = [], []
    if 'done' not in file_name.lower():  # 未完成
        file_path = cn.data_sec_path + file_name
        done_path = cn.data_sec_path + file_name + 'Done'
        with open(file_path, 'rb') as file:
            data_head, crc_after = file.read(8), []  # crc校验位
            for i in range(14):
                data = file.read(2)
                info_list.append(struct.unpack("<h", data)[0])
            bytes_data = file.read()
            if module == '气体':
                # CRC校验6字节
                for i in range(0, len(bytes_data) - 6, 4):
                    data_front, data_after = bytes_data[i:i +
                                                        2], bytes_data[i + 2:i + 4]
                    data_list.append(
                        struct.unpack("f", data_after + data_front)[0])
            else:
                # CRC校验6字节
                for i in range(0, len(bytes_data) - 6, 2):
                    data_list.append(
                        struct.unpack("H", bytes_data[i:i + 2])[0])
        # 完成修改为Done
        if do_done:
            os.rename(file_path, done_path)
            remove_file(done_path)
    return info_list, data_list


def _read_touch(file_name: str):
    """
    网口存下的视频红外
    :param file_name: 文件名=>生成路径
    :return:
    """
    info_list, pic_data, red_data = [], [], []
    if 'done' not in file_name.lower():  # 未完成
        # 没有帧头,infolist需要文件名获取
        file_path = cn.data_sec_path + file_name
        done_path = cn.data_sec_path + file_name + 'Done'
        info_list = file_name.split('_')[1].split('-')
        info_list = [int(x) for x in info_list]
        for i in range(6):
            info_list.insert(0, '')
        with open(file_path, 'rb') as file:
            data = file.read()
            bytes_list = data.split(b'\x5A\x5A\x02\x06')
            pic_data, red_data = bytes_list[0], bytes_list[1]
            # 如果有问题就是帧尾
        # 完成修改
        os.rename(file_path, done_path)
        remove_file(done_path)
    return info_list, [pic_data, red_data]  # 产出一次


def _read_pd(file_name: str):
    """
    网口存下的局放
    :param file_name: 文件名=>生成路径
    :return:
    """
    info_list, data_list = [], []
    if 'done' not in file_name.lower():  # 未完成
        # 没有帧头,infolist需要文件名获取
        file_path = cn.data_sec_path + file_name
        done_path = cn.data_sec_path + file_name + 'Done'
        info_list = file_name.split('_')[1].split('-')
        info_list = [int(x) for x in info_list]
        for i in range(6):
            info_list.insert(0, '')
        with open(file_path, 'rb') as file:
            data = file.read()
            for i in range(0, len(data) - 6, 2):
                data_list.append(
                    struct.unpack("<H", data[i:i + 2])[0])
        # 完成修改
        os.rename(file_path, done_path)
        remove_file(done_path)
    return info_list, data_list[3:-1]  # 产出一次


def remove_file(file_name: str):
    if platform.system().lower() == 'linux':
        try:
            shutil.move(file_name, cn.remove_path)
        except Exception as e:
            mylogger.error(f"{e.args}")
    # else:
    #     shutil.move(
    #         file_name, "D:/BaiduNetdiskWorkspace/School/Codes/数据/DATA/remove")


def _match_time(x: str, y: str, per_time: int = 3):
    """
    :return: 时间匹配T/F
    """
    # 编码_时间-后缀
    x_split = x.split('_')[1].split('-')
    y_split = y.split('_')[1].split('-')
    # 结尾有done的不参与匹配
    if 'done' in x_split[-1].lower() or 'done' in y_split[-1].lower():
        return False
    else:
        x_msus = (int(x_split[6]) * 10**3) + int(x_split[7])
        x = '-'.join(x_split[:6])
        x = int(time.mktime(time.strptime(x, "%Y-%m-%d-%H-%M-%S"))) * 10**6
        x += x_msus
        y_msus = (int(y_split[6]) * 10**3) + int(y_split[7])
        y = '-'.join(y_split[:6])
        y = int(time.mktime(time.strptime(y, "%Y-%m-%d-%H-%M-%S"))) * 10**6
        y += y_msus
        if abs(x - y) <= per_time * 10**6:
            return True
        else:
            return False


if __name__ == "__main__":
    # read_files(cn.func_es)
    pass
