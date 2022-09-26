#### 核心
##### 1. 模块间设计
生产 --> 消费 (只管干自己的)
##### 2. 模块内设计
类 + 函数(入出用类)\
数据类：(方便f/m交互 + 易于扩展)\
函数：入出包装 (统一形式 防止混乱)
##### 3. 编写规范
- 文档
  ```python
  """ 
  描述 
  """
  ```
- 类
  ```python
  # 驼峰
  class ObjectName(object): 
    """ 意义
    arr
      a: ...
      b: ...
    method
      funA: ...
      funB: ...
    """
  ```
- 函数
  ```python
  from typing import Dict
  # 下划 + 输入输出
  def func_todo(a, b = ..., *args, **kwargs) -> Dict[int, str]: 
    """ 描述 
    param
      a: ...
      b: ...
    return
      ... 
    """
  ```
- 变量
  ```python
  # 驼峰
  paramName = 0 
  ```
#### 编码注意
- 循环中的变量 简短or_
#### markdown
- 代码块 ```语言 ```
- 换行 \
