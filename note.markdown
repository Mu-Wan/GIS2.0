#### 核心
##### 1. 模块间设计
生产 --> 消费 (只管干自己的)
##### 2. 模块内设计
类 + 函数(入出用类)\
数据类：(方便f/m交互 + 易于扩展)\
函数：入出包装 (统一形式 防止混乱)
##### 3. 编写规范

#### 编码注意
- 循环中的变量 常可用_
- 模块 (下划)
  ```python
  """ 
  描述 
  """
  ```
- 类 (驼峰)
  ```python
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
- 函数 (下划 + 输入输出)
  ```python
  # 私有函数__func
  from typing import Dict
  def func_todo(a, b = ..., *args, **kwargs) -> Dict[int, str]: 
    """ 描述 
    param
      a: ...
      b: ...
    return
      ... 
    """
  ```
- 变量 (驼峰)
  ```python
  paramName = 0 
  ```
#### markdown
- 代码块 ```语言 ```
- 换行 \
