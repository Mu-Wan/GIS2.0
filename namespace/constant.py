"""
通用常量
"""
from namespace import file_path
import yaml

# 0. 轮询时间
readInterval = 5

# 0. 配置文件常量
with open(file_path.configPath, encoding='utf-8') as file:
    config = yaml.safe_load(file)

# 1. 模块中文名
Gas, Env, Vib, = '气体', '环境', '振动'
Ms, Mb, Es, La = '机械特性-隔离开关', '机械特性-断路器', '储能', '避雷器'
Pd, eContact = '局放', '隔离开关触头'

# 2. 区间码
nameToSection = {
    Gas: ['0', '1'], Pd: ['2', '3'], Ms: ['4'], Mb: ['5', '6'],
    Es: ['7', '8'], Vib: ['9', 'a'], La: ['b'],
    eContact: ['c'], Env: ['d', 'e', 'f']
}

# 3. 位置码
# 0x
gasCode2Loc = {
    '1': '断路器A相气室',
    '2': '断路器B相气室',
    '3': '断路器C相气室',
    '4': 'Ⅰ母母线气室',
    '5': 'Ⅱ母母线气室',
    '6': '母线侧隔离开关QSF1气室',
    '7': '母线侧隔离开关QSF2气室',
    '8': '出线侧隔离开关QS3气室',
    '9': '出线侧隔离开关QS4气室'
}
# dx
envCode2Loc = {
    '0': '柜内温湿度',
    '1': '环境温湿度',
    '2': '断路器机构箱温湿度',
    '3': '隔离开关机构箱1',
    '4': '隔离开关机构箱2',
    '5': '隔离开关机构箱3',
    '6': '快速接地'
}
# 9x
vibCode2Loc = {
    '0': 'Ⅰ母母线',
    '3': 'Ⅱ母母线',
    '6': '断路器A相',
    '9': '断路器B相',
    'b': '断路器C相'
}
# 4x
msCode2Loc = {
    # 按下位机的内容顺序
    '0': ['母线侧隔离开关QSF1', '母线侧隔离开关QSF2', '出线侧隔离开关QS3'],
}
# 5x 6x
mbCode2Loc = '断路器'
# 7x
esCurCode2Loc = {
    # 按下位机的内容顺序
    '0': ['断路器A相', '断路器B相', '断路器C相']
}
# 8x
esSpringCode2Loc = {
    '0': '断路器A相',
    '1': '断路器B相',
    '2': '断路器C相'
}
# bx
laCode2Loc = {
    '0': '避雷器A相',
    '1': '避雷器B相',
    '2': '避雷器C相'
}
# 2x 3x
pdCode2Loc = {
    '0': '断路器A相',
    '1': '断路器B相',
    '2': '断路器C相',
    '3': 'Ⅰ母母线',
    '4': 'Ⅱ母母线'
}
# cx
eContactCode2Loc = {
    '0': '母线侧隔离开关QSF1触头状态',
    '1': '母线侧隔离开关QSF2触头状态',
    '2': '出线侧隔离开关QS3触头状态'
}
