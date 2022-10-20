"""
入口文件
"""
from algo.gas import gas1time
from algo.env import env1time
from algo.vib import vib1time
from algo.es import es1time
from algo.mach_ms import ms1time
from algo.mach_mb import mb1time
from algo.pd import pd1time
from algo.e_contact import econtact1time

from namespace.constant import readInterval

import time

if __name__ == "__main__":
    # 气体测试
    for d in gas1time():
        print(d)

    # 环境测试
    for d in env1time():
        print(d)

    # 振动测试
    for d in vib1time():
        print(d)

    # 储能测试
    # while True:
    #     for d in es1time():
    #         print(d)
    #     time.sleep(readInterval)

    # 机械特性-隔离开关测试
    for d in ms1time():
        print(d)

    # 机械特性-断路器测试
    while True:
        for d in mb1time():
            print(d)
        time.sleep(readInterval)

    # 触头测试
    # for d in econtact1time():
    #     print(d)

    # 局放测试
    # print(pd1time())
