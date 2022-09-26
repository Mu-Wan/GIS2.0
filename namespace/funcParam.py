"""
函数调用参数常量
"""
import db

# 1. 模块名
funcGas, funcPd, funcMs, funcMb, funcEs, funcVib, funcLa, funcTouch, funcEnv = \
    'gas', 'pd', 'ms', 'mb', 'es', 'vb', 'la', 'touch', 'ev'
# 2. 模块名 转 区间码
modToSec = {
    funcGas: [0, 1],
    funcPd: [2, 3],
    funcMs: [4],
    funcMb: [5, 6],
    funcEs: [7, 8],
    funcVib: [9, 10],
    funcLa: [11],
    funcTouch: [12],
    funcEnv: [13, 14]
}
# 3.函数参数与模块对应(与loc.data联系)
funcToMod = {
    funcGas: db.modules[0],
    funcPd: db.modules[1],
    funcMs: db.modules[2],
    funcMb: db.modules[2],
    funcEs: db.modules[3],
    funcVib: db.modules[4],
    funcLa: db.modules[5],
    funcTouch: db.modules[6],
    funcEnv: db.modules[7]
}
