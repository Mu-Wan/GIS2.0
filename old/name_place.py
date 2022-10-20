import platform
import json

# 1.根路径:win
data_path = 'D:/同步空间/School/Codes/数据/DATA/'
data_sec_path = data_path + 'OLD_DIR/'
process_path = data_path
bd_path = data_path + 'GISdb.db'
remove_path = "/media/nvme"
# 1.根路径:linux
user_name = '/pi'
if platform.system().lower() == 'linux':
    data_path = '/home/DATA/'
    data_sec_path = data_path + 'OLD_DIR/'
    process_path = '/home/pi/gis/gis/'
    bd_path = process_path + 'GISdb.db'
json_path = process_path + 'Config.json'


##############################################################################################################
##############################################################################################################

# 1.数据库名
form_record, form_result, form_curve, form_ui, form_61850 = 'Record', 'ResultCal', 'Curve', 'UI', 'To61850'
# 2.模块
modules = ['气体', '局放', '机械特性', '储能', '振动', '避雷器', '隔离开关触头', '环境']
# 3.位置 + 传感器套数/种类
gas_loc = [['断路器A相气室', 1], ['断路器B相气室', 1], ['断路器C相气室', 1], ['Ⅰ母母线气室', 1],
           ['Ⅱ母母线气室', 1], ['母线侧隔离开关QSF1气室', 1], ['母线侧隔离开关QSF2气室', 1],
           ['出线侧隔离开关QS3气室', 1], ['出线侧隔离开关QS4气室', 1]]
pd_loc = [['断路器A相', 1], ['断路器B相', 1], ['断路器C相', 1], ['Ⅰ母母线', 1], ['Ⅱ母母线', 1]]
mc_loc = [['母线侧隔离开关QSF1', 1], ['母线侧隔离开关QSF2', 1], ['出线侧隔离开关QS3', 1],
          ['出线侧隔离开关QS4', 1], ['断路器', 1]]
es_loc = [['断路器A相', 1], ['断路器B相', 1], ['断路器C相', 1]]
vb_loc = [['Ⅰ母母线', 3], ['Ⅱ母母线', 3], ['断路器A相', 3], ['断路器B相', 3], ['断路器C相', 3]]
la_loc = [['避雷器A相', 1], ['避雷器B相', 1], ['避雷器C相', 1]]
touch_loc = [['母线侧隔离开关QSF1触头状态', 3], ['母线侧隔离开关QSF2触头状态', 3],
             ['出线侧隔离开关QS3触头状态', 3]]
ev_loc = [['柜内温湿度', 1], ['环境温湿度', 1], ['断路器机构箱温湿度', 1], ['隔离开关机构箱1', 1],
          ['隔离开关机构箱2', 1], ['隔离开关机构箱3', 1], ['快速接地', 1]]
# 4.记录数据 { '数据名': [单位,正误,实时,值(a,b,c)]}
gas_data = {
    '相对压力': ['MPa', 1, 0],
    '温度': ['℃', 1, 0],
    '密度': ['MPa', 1, 0],
    '微水': ['ppm', 1, 0]
}
pd_data = {
    '局部放电幅值': ['dBm', 1, 0],
    '局部放电功率': ['mW', 1, 0],
    '局部放电频次': ['次/s', 1, 0],
    '脉冲个数': ['个', 1, 0],
}
ms_data = {
    '分闸时间': ['ms', 1, 0, 0, 0],
    '合闸时间': ['ms', 1, 0, 0, 0],
    '电流持续时间': ['ms', 1, 0, 0, 0],
    '最大工作电流': ['A', 1, 0, 0, 0],
    '平均工作电流': ['A', 1, 0, 0, 0]
}
mb_data = {
    '操作类型': ['', 1, 0, 0, 0],
    # '机械操作次数': ['次', 0, 1, 0, 0, 0],
    '一分行程量': ['mm', 1, 0, 0, 0],
    '一分时间': ['ms', 1, 0, 0, 0],
    '一分速度': ['m/s', 1, 0, 0, 0],
    '一分电流': ['A', 1, 0, 0, 0],
    '一分带电时间': ['ms', 1, 0, 0, 0],
    '一分同期': ['ms', 1, 0, 0, 0],
    '合行程量': ['mm', 1, 0, 0, 0],
    '合时间': ['ms', 1, 0, 0, 0],
    '合速度': ['m/s', 1, 0, 0, 0],
    '合电流': ['A', 1, 0, 0, 0],
    '合带电时间': ['ms', 1, 0, 0, 0],
    '合同期': ['ms', 1, 0, 0, 0],
    '二分行程量': ['mm', 1, 0, 0, 0],
    '二分时间': ['ms', 1, 0, 0, 0],
    '二分速度': ['m/s', 1, 0, 0, 0],
    '二分电流': ['A', 1, 0, 0, 0],
    '二分带电时间': ['ms', 1, 0, 0, 0],
    '二分同期': ['ms', 1, 0, 0, 0]
}
es_data = {
    '储能电机电流': ['A', 1, 0],
    '启动电流': ['A', 1, 0],
    '启动时间': ['ms', 1, 0],
    '储能状态': ['', 1, 0],
    '储能时间': ['ms', 1, 0],
    '储能次数': ['次', 1, 0],
    '分弹簧压力': ['kN', 1, 0],
    '合弹簧压力': ['kN', 1, 0],
    '分弹簧压力最大值': ['kN', 1, 0],
    '合弹簧压力最大值': ['kN', 1, 0]
}
vb_data = {
    '加速度': ['g', 1, 0, 0, 0],
    '频率': ['Hz', 1, 0, 0, 0],
}
la_data = {
    '全电流': ['mA', 1, 0],
    '阻性电流': ['mA', 1, 0],
    '阻容比': ['', 1, 0],
    '最近落雷时间': ['s', 1, 0],
    '最近落雷次数': ['', 1, 0],
    '参考相角': ['°', 1, 0],
    '传感器电池电压': ['V', 1, 0],
    '传感器电池充放电电流': ['A', 1, 0]
}
touch_data = {'位置': ['', 1, 0, 0, 0], '温度': ['℃', 1, 0, 0, 0]}
ev_data = {'温度': ['℃', 1, 0], '湿度': ['%', 1, 0]}
# 5.对应关系(61850初始化)
mod_loc_data = {
    modules[0]: [gas_loc, gas_data],
    modules[1]: [pd_loc, pd_data],
    modules[2]: [mc_loc, ms_data, mb_data],
    modules[3]: [es_loc, es_data],
    modules[4]: [vb_loc, vb_data],
    modules[5]: [la_loc, la_data],
    modules[6]: [touch_loc, touch_data],
    modules[7]: [ev_loc, ev_data]}

# 1.函数参数
func_gas, func_pd, func_ms, func_mb, func_es, func_vb, func_la, func_touch, func_ev = \
    'gas', 'pd', 'ms', 'mb', 'es', 'vb', 'la', 'touch', 'ev'
# 2.函数参数与功能码对应
mod_doi = {
    func_gas: [0, 1],
    func_pd: [2, 3],
    func_ms: [4],
    func_mb: [5, 6],
    func_es: [7, 8],
    func_vb: [9, 10],
    func_la: [11],
    func_touch: [12],
    func_ev: [13, 14]
}
# 3.函数参数与模块对应(与loc.data联系)
func_mod = {
    func_gas: modules[0],
    func_pd: modules[1],
    func_ms: modules[2],
    func_mb: modules[2],
    func_es: modules[3],
    func_vb: modules[4],
    func_la: modules[5],
    func_touch: modules[6],
    func_ev: modules[7]
}

##############################################################################################################
##############################################################################################################
read_dict = {}
with open(json_path, 'r', encoding='utf-8') as file:
    read_dict = json.load(file)  # type: dict
    read_gas = read_dict['气体模块']
    read_mb = read_dict['机械特性模块']
    read_ms = read_dict['隔离开关模块']
    read_es = read_dict['储能模块']
    read_vb = read_dict['振动模块']
    read_env = read_dict['环境模块']
# 气体
gas_break_high = read_gas['断路器气室']['低气压报警阈值']
gas_break_low = read_gas['断路器气室']['低气压闭锁阈值']
gas_other_high = read_gas['其他气室']['低气压报警阈值']
# 局放
pd_frequency = 7.6*(10**6)
pd_T = 1 / pd_frequency
# 机械 - 隔离开关
ms_frequency = read_ms['电机电流']['采样率/KHz']
ms_dot = read_ms['电机电流']['每路采集点数']
ms_cur_factor_list = [read_ms['电机电流']['QSF1电流系数'],
                      read_ms['电机电流']['QSF2电流系数'],
                      read_ms['电机电流']['QS3电流系数']]
ms_cur_max = read_ms['电机电流']['最大工作电流']
# 机械-断路器
phase_number = read_mb['基础配置']['设备相数']  # 设备相数
time_allow = read_mb['基础配置']['多文件匹配允许的时间差/s']  # 匹配时间
mb_time_inter = 1 / read_mb['基础配置']['采样率/KHz']  # 时间间隔
mb_diag = {
    'trip_max': read_mb['诊断配置']["行程最大阈值"],
    'trip_min': read_mb['诊断配置']["行程最小阈值"],
    'sep_time_max': read_mb['诊断配置']["分闸时间最大阈值"],
    'sep_time_min': read_mb['诊断配置']["分闸时间最小阈值"],
    'close_time_max': read_mb['诊断配置']["合闸时间最大阈值"],
    'close_time_min': read_mb['诊断配置']["合闸时间最小阈值"],
    'sep_v_max': read_mb['诊断配置']["分闸速度最大阈值"],
    'sep_v_min': read_mb['诊断配置']["分闸速度最小阈值"],
    'close_v_max': read_mb['诊断配置']["合闸速度最大阈值"],
    'close_v_min': read_mb['诊断配置']["合闸速度最小阈值"],
    'sep_cur_time_max': read_mb['诊断配置']["分带电时间阈值"],
    'close_cur_time_max': read_mb['诊断配置']["合带电时间阈值"],
    'sep_cur_max': read_mb['诊断配置']["分电流阈值"],
    'close_cur_max': read_mb['诊断配置']["合电流阈值"]
}
phase_name, mb_config = ['A相配置', 'B相配置', 'C相配置'], [{}, {}, {}]
close_order, subsep_order, sep_order = 2, 1, 0  # 电流顺序
for index, temp_name in enumerate(phase_name):
    mb_config[index]['trip_direction'] = False
    if read_mb[temp_name]['行程']['行程方向'] == '反向':
        mb_config[index]['trip_direction'] = True
    else:
        mb_config[index]['trip_direction'] = False
    mb_config[index]['sep_vir_per'] = 1 - read_mb[temp_name]['行程']['分闸虚拟断口']
    mb_config[index]['close_vir_per'] = read_mb[temp_name]['行程']['合闸虚拟断口']
    mb_config[index]['sep_speed_factor'] = read_mb[temp_name]['行程']['分闸速度系数']
    mb_config[index]['close_speed_factor'] = read_mb[temp_name]['行程']['合闸速度系数']
    mb_config[index]['trip_factor'] = read_mb[temp_name]['行程']['行程曲线系数']
    mb_config[index]['trip_sep_factor'] = read_mb[temp_name]['行程']['分闸行程系数'] / \
        mb_config[index]['trip_factor']
    mb_config[index]['trip_close_factor'] = read_mb[temp_name]['行程']['合闸行程系数'] / \
        mb_config[index]['trip_factor']
    mb_config[index]['ppr'] = read_mb[temp_name]['行程']['每转脉冲数']
    mb_config[index]['cs_dot'] = read_mb[temp_name]['电流']['电流传感器采集点数']
    mb_config[index]['sep_cur_factor'] = read_mb[temp_name]['电流']['分闸电流系数']
    mb_config[index]['close_cur_factor'] = read_mb[temp_name]['电流']['合闸电流系数']
    mb_config[index]['subsep_cur_factor'] = read_mb[temp_name]['电流']['副分电流系数']
# 储能
es_frequency = read_es['基础配置']['采样率/KHz']
es_T = 1 / es_frequency
es_per = read_es['基础配置']['容差时间/s']
# es_spring_dot = read_es['弹簧']['每路点数']
es_cur_T = 20   # 电流周期
es_cur_dot = read_es['电流']['每路采集点数']
es_spring_max = read_es['弹簧']['合弹簧压力阈值']
es_cur_max = read_es['电流']['储能电机电流阈值']
# es_cur_factor = read_es['电流']['储能电机电流系数']
es_cur_factors = [read_es['电流']['储能A相电机电流系数'],
                  read_es['电流']['储能B相电机电流系数'],
                  read_es['电流']['储能C相电机电流系数']]

# 振动
vb_frequency = read_vb['断路器振动']['采样率/KHz']
# 环境
env_temp_high = read_env['温度高温阈值']
env_temp_low = read_env['温度低温阈值']
env_humidity = read_env['湿度阈值']
###################################################################################
smooth_default = 800
# 机械特性-断路器
close_cur_find = [1, 8, 0.005, 0.20]
sep_cur_find = [1, 7, 0.005, 0.25]
# 第一个参数不变; 第二个参数为连续增长多少个点; 第三个参数为每点至少增长多少; 第四个参数为整体增长高度%
trip_sep_find = [1, 15, 0.01, 0.03]
trip_close_find = [1, 100, 0, 0]
trip_sec_find = [1, 15, 0.01, 0.03]
# 机械特性-隔离开关
ms_find_begin = [1, 8, 0.005, 0.3]
ms_find_end = [1, 10, 0.005, 0.05]
# 储能电机电流
es_find_begin = [1, 20, 0.005, 0.4]
es_find_end = [1, 20, 0.005, 0.1]
