"""
配置文件读取
"""
# 跨目录调用: 路径添加
import sys
import inspect
sys.path.append(inspect.getfile(inspect.currentframe()))
from namespace import filePath
# ...
import yaml
from collections import namedtuple


class Config(object):
    """ obj={'x':{}, ...} => obj['x'] => obj.x
    attr:
    method:
    """
    def __new__(cls, data):
        if isinstance(data, dict):
            return namedtuple('Config', data.keys())(*(Config(v) for v in data.values()))
        elif isinstance(data, (tuple, list, set, frozenset)):
            return type(data)(Config(_) for _ in data)
        else:
            return data


def read_config() -> Config:
    """ read yaml
    param:
    return:
        Config()
    """
    try:
        with open(filePath.configPath, encoding='utf-8') as file:
            config = Config(yaml.safe_load(file))
    except FileNotFoundError:
        config = Config({})
    return config
