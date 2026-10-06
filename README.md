# 计算器系统 · 后端（Calculator Backend）

> 软件工程实践 · 第一次作业《前后端分离计算器系统》—— 后端仓库

## 一、技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 语言 | Python 3.9+（标准库实现，**零第三方依赖**） | 不依赖任何 Web 框架，降低部署与评测门槛 |
| HTTP 服务 | `http.server` + `ThreadingHTTPServer` | 自带多线程，足以支撑作业演示并发 |
| 数据库 | SQLite 3 | 文件型数据库，免安装、免配置，天然持久化 |
| 表达式求值 | 自研**递归下降解析器** | **不使用 `eval` / `exec`**，满足安全约束 |

## 二、运行环境

- Python 3.9 及以上（推荐 3.11 / 3.13）
- 无需 `pip install` 任何依赖（纯标准库）

## 三、安装与启动

```bash
# 1. 进入后端目录
cd calculator_backend

# 2. 初始化数据库（首次运行会自动建表，也可显式执行）
python main.py            # 会自动 init_db()

# 3. 自定义端口 / 绑定地址（可选）
python main.py --port 8000 --host 0.0.0.0

# 也支持环境变量（云平台常用）：
PORT=8000 HOST=0.0.0.0 python main.py
```

启动后：

- REST API 根地址：`http://<host>:<port>/`
- 前端静态页面（若 `static/` 已放入前端文件）：`http://<host>:<port>/`

## 四、目录结构

```
calculator_backend/
├── main.py                  # 服务入口：路由分发 + 静态文件托管
├── requirements.txt         # 纯标准库，本仓库无第三方依赖
├── codestyle.md             # 代码规范说明
├── src/
│   ├── model/
│   │   └── database.py      # SQLite 持久化层（建表 / 增 / 查 / 删）
│   ├── service/
│   │   └── evaluator.py     # 安全表达式解析与求值（无 eval/exec）
│   └── controller/
│       └── (路由逻辑位于 main.py 的 Handler 中)
└── static/                  # 部署时放置前端静态文件（可选项）
```

> 说明：为与「前端 / 后端分仓」要求保持一致，`static/` 仅作为**部署产物**。
> 本地评测时，把前端仓库的 `index.html / app.js / style.css` 复制到本目录 `static/`
> 即可由后端统一托管，实现“单一公开访问地址”。

## 五、API 设计

| 方法 | 路径 | 说明 | 成功 | 失败 |
| --- | --- | --- | --- | --- |
| `POST` | `/api/calculate` | 提交表达式，后端解析、计算、落库 | `200` 返回记录 | `400` 非法/`413` 过大/`500` |
| `GET` | `/api/history` | 获取全部历史（最新在前） | `200` `{"history":[...]}` | `500` |
| `DELETE` | `/api/history/{id}` | 按 id 删除一条历史 | `200` `{"deleted":true}` | `404` 不存在 |

请求 / 响应示例：

```http
POST /api/calculate
Content-Type: application/json

{ "expression": "(1+2)*3" }
```

```json
{ "id": 2, "expression": "(1+2)*3", "result": "9", "created_at": "2026-10-06 20:04:14" }
```

错误示例（除零）：

```json
{ "error": "除数不能为 0" }
```

## 六、数据库设计

表 `calculation_history`：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `id` | INTEGER PK AUTOINCREMENT | 记录主键 |
| `expression` | TEXT | 用户提交的表达式 |
| `result` | TEXT | 后端计算结果（字符串形式） |
| `created_at` | TEXT | 本地时间戳 `YYYY-MM-DD HH:MM:SS` |

数据库文件路径可通过环境变量 `CALC_DB` 覆盖（默认 `calculator.db`）。

## 七、前后端连接方式

- **部署态（推荐）**：后端同时托管前端静态文件，前端以 `window.location.origin + "/api"` 同源调用，单一 URL 即可完成全部功能。
- **分离态**：前端仓库可通过 `?api=https://你的后端地址` 显式指定后端基地址，实现前后端分离部署。

## 八、安全说明（作业硬性要求）

- 后端**严禁**使用 `eval` / `exec` 处理用户输入；表达式通过自研词法 + 语法分析器求值。
- 用户输入先做字符归一化（×→*、÷→/、−→-），再经严格 tokenizer 与递归下降解析；
  非法字符、括号不匹配、除零、表达式不完整等均返回 `400` 与中文错误描述。
- 前端展示层对表达式 / 结果 / 时间统一做 HTML 转义，防止存储型 XSS。
