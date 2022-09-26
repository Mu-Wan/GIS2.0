"""
算法参数常量
"""
smoothDefault = 800
# 机械特性-断路器
closeCurFind = [1, 8, 0.005, 0.20]
sepCurFind = [1, 7, 0.005, 0.25]
# 第一个参数不变; 第二个参数为连续增长多少个点; 第三个参数为每点至少增长多少; 第四个参数为整体增长高度%
tripSepFind = [1, 15, 0.01, 0.03]
tripCloseFind = [1, 100, 0, 0]
tripSecFind = [1, 15, 0.01, 0.03]
# 机械特性-隔离开关
msFindBegin = [1, 8, 0.005, 0.3]
msFindEnd = [1, 10, 0.005, 0.05]
# 储能电机电流
esFindBegin = [1, 20, 0.005, 0.4]
esFindEnd = [1, 20, 0.005, 0.1]