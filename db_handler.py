import sqlite3
import name_place as cn
import json


def json_data(data: dict):
    """
    无curve数据时,将点值转为曲线的json
    :param data: 数据集
    :return: Curve表需要json格式数据
    """
    j_data = {}
    for key, value in data.items():
        j_data[key] = value[2]
    return json.dumps(j_data)


def json_curve(curve: dict):
    """
    :param curve: 曲线数据
    :return: Curve表需要json格式数据
    """
    return json.dumps(curve)


def parse_info(info_list: list):
    """
    解析帧头
    :return: 时间戳
    """
    str_info = [str(x) for x in info_list]
    time_str = '/'.join(str_info[6:9]) + ' ' + '"'.join(str_info[9:12])
    return time_str


class DBHandler:
    def __init__(self):
        # 数据库建表
        self.conn = sqlite3.connect(cn.bd_path)
        cursor = self.conn.cursor()
        # 记录：id + 监测模块 -> 监测位置 -> (传感器编号) + 时间 / (类型) / 描述
        cursor.execute(
            f'''CREATE TABLE IF NOT EXISTS {cn.form_record} (
                ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                module varchar(40), 
                location varchar(40), 
                num tinyint, 
                real_time tinyint,
                act_time text, 
                act_name text, 
                status_flag tinyint,
                status text);'''
        )
        # 结果：对应记录id + (数据名 / 值 / 单位 / 判断)xN
        cursor.execute(
            f'''CREATE TABLE IF NOT EXISTS {cn.form_result} (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id int,
                value_name varchar(40),
                value_a float, 
                value_b float, 
                value_c float, 
                unit varchar(40), 
                judge tinyint) ;'''
        )
        # 曲线: 对应记录id + 曲线点 or 图片位置
        cursor.execute(
            f'''CREATE TABLE IF NOT EXISTS {cn.form_curve} (
                ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                record_id int, 
                curve text,
                timestamp int);''')
        # 界面:
        cursor.execute(
            f'''CREATE TABLE IF NOT EXISTS {cn.form_ui} (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                SensorType int, 
                SensorNum int, 
                DataAddress int, 
                DataName varchar(40), 
                Data float, 
                DataUnit varchar(40), 
                Time varchar(60), 
                Analysis int);'''
        )
        # 61850: 监测模块 -> (监测位置 => (地址:数据名/值/单位/时间)xN )xN
        cursor.execute(
            f'''CREATE TABLE IF NOT EXISTS {cn.form_61850} (
                ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                module varchar(40), 
                location varchar(40), 
                num tinyint, 
                phase tinyint, 
                address int, 
                data_name varchar(40), 
                data float, 
                data_unit varchar(40), 
                time varchar(60));''')
        # 初始化61850
        if not cursor.execute(f"SELECT ID FROM {cn.form_61850}").fetchall():
            main_key = 1
            for module, loc_data in cn.mod_loc_data.items():  # 模块循环
                locs, data, con_count, phase = loc_data[0], loc_data[1], 0, 1
                for loc, num in locs:  # 位置循环
                    for i in range(num):  # 编号循环
                        if module == "机械特性" and loc == "断路器":
                            phase, data = 3, loc_data[2]
                        for j in range(phase):  # 相数循环
                            for name, data_unit in data.items():  # 数据循环
                                sql_add = f"INSERT INTO {cn.form_61850} VALUES ({main_key}, " \
                                          f"'{module}', '{loc}', {i}, {j}, " \
                                          f"{10000 * (cn.modules.index(module) + 1) + con_count}, " \
                                          f"'{name}', {data_unit[2]}, '{data_unit[0]}', '{''}')"
                                cursor.execute(sql_add)
                                con_count += 1
                                main_key += 1
        self.conn.commit()
        cursor.close()

    def add_update(self,
                   module: str,
                   location: str,
                   num: int,
                   phase_count: int,
                   real_time: int,
                   info_list: list,
                   act_name: str,
                   status_flag: int,
                   status: str,
                   data: dict,
                   curve_data=None,
                   timestamp: int = 0):
        """
        合并处理 三表添加 61850更新

        无曲线数据时: 默认会将数据值转为曲线数据

        有曲线数据时: 正常传入工作

        :param module: 模块名
        :param location: 检测位置
        :param num: 编号
        :param phase_count: 总相数!!!(不是phase,是总数)
        :param real_time: 实时
        :param info_list: 帧头列表
        :param act_name: 动作名称
        :param status_flag: 状态标志
        :param status: 动作状态
        :param data: 数值
        :param curve_data: 曲线数据(无时默认)
        :return:
        """
        if curve_data is None:
            curve_data = {}
        time_str = parse_info(info_list)
        record_id = self.record_add(module, location, num, real_time, time_str, act_name,
                                    status_flag, status)
        self.result_add(record_id, data)
        if not curve_data:
            curve_data = json_data(data)
        else:
            curve_data = json_curve(curve_data)
        self.curve_add(record_id, curve_data, timestamp)
        # 相数逻辑上有问题,三相时其余表是一次添加的,而61850需要循环添加
        self.update_61850(module, location, num, phase_count, data, time_str)

    def record_add(self, module: str, location: str, num: int, real_time: int, act_time: str,
                   act_name: str, status_flag: int, status: str):
        """
        记录表insert
        """
        main_key = self.get_id(cn.form_record)
        cursor = self.conn.cursor()
        sql_add = f"INSERT INTO {cn.form_record} " \
            "(module, location, num,  real_time, act_time, act_name, status_flag, status) VALUES " \
            f"('{module}', '{location}', {num}, {real_time}, '{act_time}', '{act_name}', {status_flag}, '{status}')"
        cursor.execute(sql_add)
        self.conn.commit()
        cursor.close()
        return main_key

    def result_add(self, record_id: int, data: dict):
        """
        结果表insert
        """
        # 存储时: [单位,判断,实时,数据(1/3)]
        cursor = self.conn.cursor()
        for data_name, unitJ_data in data.items():
            value_b, value_c = 0, 0
            if len(unitJ_data) == 5:
                value_b, value_c = unitJ_data[3], unitJ_data[4]
            sql_add = f"INSERT INTO {cn.form_result} " \
                "(record_id, value_name, value_a, value_b, value_c, unit, judge) VALUES " \
                f"({record_id}, '{data_name}', {unitJ_data[2]}, {value_b}, {value_c}," \
                f"'{unitJ_data[0]}', '{unitJ_data[1]}')"
            cursor.execute(sql_add)
        self.conn.commit()
        cursor.close()

    def curve_add(self, record_id: int, data: json = '', timestamp: int = 0):
        """
        曲线表insert
        :param record_id: 对应记录表的id => 对应查找
        :param data: 曲线json/图片url
        """
        cursor = self.conn.cursor()
        sql_add = f"INSERT INTO {cn.form_curve} "\
            "(record_id, curve, timestamp) VALUES " \
            f"({record_id},'{data}', {timestamp})"
        cursor.execute(sql_add)
        self.conn.commit()
        cursor.close()

    def update_61850(self, module: str, location: str, num: int, phase: int,
                     data: dict, time: str):
        """
        更新To61850表
        :param module: 模块名
        :param location: 位置
        :param num: 编号
        :param phase: 相数
        :param data: 数据集
        :param time: 采集时间
        """
        cursor = self.conn.cursor()
        for data_name, unit_ju_data in data.items():
            for i in range(phase):
                sql_update = f"UPDATE To61850 set data = {unit_ju_data[i + 2]}, time='{time}' " \
                             f"where module='{module}' and location='{location}' and num={num} and phase={i} " \
                             f"and data_name='{data_name}' "
                cursor.execute(sql_update)
        self.conn.commit()
        cursor.close()

    def get_id(self, form_name: str):
        """
        :param form_name: 表名
        :return: 主键值
        """
        cursor = self.conn.cursor()
        main_key = cursor.execute(
            f"SELECT ID FROM {form_name}").fetchall()  # 主键获取
        if not main_key:
            main_key = 1
        else:
            main_key = main_key[-1][0] + 1
        cursor.close()
        return main_key

    def select_data(self, module: str, location: str, phase: int,
                    data_name: str):
        """
        数据库累计值的查询(通过61850)

        :param module: 模块
        :param location: 位置
        :param phase: 相数
        :param data_name: 数据名
        :return: [列1,列2,列3] x n
        """
        cursor = self.conn.cursor()
        try:
            rows = cursor.execute(
                f"SELECT data FROM {cn.form_61850} "
                f"where module='{module}' and location='{location}' and phase={phase} "
                f"and data_name='{data_name}'").fetchall()
            self.conn.commit()
            cursor.close()
        except Exception as e:
            return []
        return rows

    def select_curve(self, module: str, location: str):
        """
        曲线查询
        :param module: 模块
        :param location: 位置
        :param phase: 相数
        :param data_name: 数据名
        :return: [列1,列2,列3] x n
        """
        cursor = self.conn.cursor()
        try:
            rows = cursor.execute(
                f"SELECT ID FROM {cn.form_record} "
                f"where module='{module}' and location='{location}'").fetchall()
            rows = cursor.execute(
                f"SELECT curve FROM {cn.form_curve} "
                f"where record_id='{rows[-1][0]}'").fetchall()
            self.conn.commit()
            cursor.close()
        except Exception as e:
            return []
        return json.loads(rows[0][0])


if __name__ == "__main__":
    db = DBHandler()
    db.conn.close()
