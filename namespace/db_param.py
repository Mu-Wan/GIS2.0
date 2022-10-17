"""
数据库常量
"""

# 1.数据
gasData = {
    '相对压力': 'MPa',
    '温度': '℃',
    '密度': 'MPa',
    '微水': 'ppm',
}
pdData = {
    '局部放电幅值': 'dBm',
    '局部放电功率': 'mW',
    '局部放电频次': '次/s',
    '脉冲个数': '个',
}
msData = {
    '分闸时间': 'ms',
    '合闸时间': 'ms',
    '电流持续时间': 'ms',
    '最大工作电流': 'A',
    '平均工作电流': 'A',
}
mbData = {
    '操作类型': '',
    # '机械操作次数': '次', 0,
    '一分行程量': 'mm',
    '一分时间': 'ms',
    '一分速度': 'm/s',
    '一分电流': 'A',
    '一分带电时间': 'ms',
    '一分同期': 'ms',
    '合行程量': 'mm',
    '合时间': 'ms',
    '合速度': 'm/s',
    '合电流': 'A',
    '合带电时间': 'ms',
    '合同期': 'ms',
    '二分行程量': 'mm',
    '二分时间': 'ms',
    '二分速度': 'm/s',
    '二分电流': 'A',
    '二分带电时间': 'ms',
    '二分同期': 'ms',
}
esData = {
    '储能电机电流': 'A',
    '启动电流': 'A',
    '启动时间': 'ms',
    '储能状态': '',
    '储能时间': 'ms',
    '储能次数': '次',
    '分弹簧压力': 'kN',
    '合弹簧压力': 'kN',
    '分弹簧压力最大值': 'kN',
    '合弹簧压力最大值': 'kN',
}
vbData = {
    '加速度': 'g',
    '频率': 'Hz',
}
laData = {
    '全电流': 'mA',
    '阻性电流': 'mA',
    '阻容比': '',
    '最近落雷时间': 's',
    '最近落雷次数': '',
    '参考相角': '°',
    '传感器电池电压': 'V',
    '传感器电池充放电电流': 'A',
}
touchData = {
    '位置': '',
    '温度': '℃',
}
evData = {
    '温度': '℃',
    '湿度': '%',
}

# 2.数据库名
formRecord, formResult, formCurve, formUI, form61850 = \
    'Record', 'ResultCal', 'Curve', 'UI', 'To61850'

# 4.对应关系(61850初始化)
# modLocData = {
#     modules[0]: [gasLoc, gasData],
#     modules[1]: [pdLoc, pdData],
#     modules[2]: [machLoc, msData, mbData],
#     modules[3]: [esLoc, esData],
#     modules[4]: [vibLoc, vbData],
#     modules[5]: [laLoc, laData],
#     modules[6]: [eContactLoc, touchData],
#     modules[7]: [envLoc, evData]
# }
