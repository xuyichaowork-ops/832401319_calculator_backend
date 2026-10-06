# 后端代码规范（codestyle）

> 本仓库代码风格主要参照 **PEP 8**（Python 官方风格指南，https://peps.python.org/pep-0008/），
> 并结合 Google Python Style Guide 的命名与文档字符串约定。

## 1. 缩进与行长

- 使用 **4 个空格**缩进，禁用 Tab。
- 单行不超过 **100** 字符（PEP 8 建议 79，工程实践中 100 更宽松易读）。

## 2. 命名约定（PEP 8）

| 对象 | 风格 | 示例 |
| --- | --- | --- |
| 模块 / 包 | 全小写、下划线分隔 | `database.py`, `evaluator.py` |
| 函数 / 变量 | 全小写、下划线分隔 | `add_record`, `created_at` |
| 类 | 驼峰（CapWords） | `EvalError`, `_Parser` |
| 常量 | 全大写、下划线分隔 | `MAX_BODY`, `DB_PATH` |
| 私有成员 | 单下划线前缀 | `_send_json`, `_handle_calculate` |

## 3. 文档字符串（Docstring）

- 公共模块、类、函数均使用 Google 风格 docstring：

```python
def add_record(expression: str, result: str) -> dict:
    """Insert one successful calculation and return the stored row.

    Args:
        expression: 用户提交的表达式。
        result: 计算结果字符串。

    Returns:
        包含 id / expression / result / created_at 的字典。
    """
```

- 类型注解（type hints）随 PEP 484 规范书写。

## 4. 异常处理

- 业务错误使用自定义异常 `EvalError`，不在求值路径吞掉异常。
- 对外接口统一捕获并映射为合理 HTTP 状态码（400 / 404 / 500）。

## 5. 导入顺序

1. 标准库（`import os`, `import sys` …）
2. 第三方库（本仓库无）
3. 本地模块（`from src.model.database import ...`）
   各分组之间空一行，`isort` 风格。

## 6. 注释与可读性

- 关键算法（如递归下降文法）使用注释说明产生式（BNF）。
- 避免“显然式”注释，注释解释 **为什么** 而非 **做什么**。

## 7. 工具

- 提交前建议运行：`python -m py_compile src/**/*.py` 与 `flake8 --max-line-length=100`。
- 本仓库坚持“零第三方依赖”，因此不强制引入 formatter，以人工遵循上述规范为主。
