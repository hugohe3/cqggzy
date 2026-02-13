# 重庆公共资源交易网爬虫

抓取 [重庆市公共资源交易网](https://www.cqggzy.com/) 的交易结果及详细信息。

## 特性

*   **全自动反爬**：使用 Playwright 自动处理 JSL 加密验证。
*   **极速抓取**：验证通过后立即切换到 HTTP 并发模式，详情抓取速度提升 10-50x。
*   **灵活筛选**：支持通过命令行参数指定关键词、区域、业务类型、信息类型和时间范围。
*   **断点续传**：抓取详情时支持中断后自动恢复，避免重复工作。
*   **结构化输出**：结果自动保存为 CSV（Excel 可直接打开）和 JSON 格式。

## 架构设计

```
浏览器开门 + HTTP 干活

┌───────────────┐     ┌──────────────────┐
│   Playwright  │     │      httpx       │
│   (最小化)     │     │   (高性能)        │
│               │     │                  │
│  1. JSL 验证  │────▶│  2. API 翻页      │
│  2. 拦截请求体 │     │  3. 并发抓详情     │
│  3. 拿 Cookie │     │  4. HTML 解析      │
│  4. 关闭浏览器 │     │                  │
└───────────────┘     └──────────────────┘
     ~30秒                  ~2-5分钟
```

## 环境准备

1.  Python 3.10+
2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

## 使用方式

### 第一步：获取链接列表

运行 `step1_fetch_links.py` 获取符合条件的交易信息链接。

**基本用法（默认配置）：**
```bash
python step1_fetch_links.py
```
*（默认：搜索全部 + 区域全部 + 业务全部 + 交易结果 + 近三月）*

**自定义筛选参数：**

| 参数 | 简写 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `--keyword` | `-k` | 标题关键词（支持空） | `-k "出租"` |
| `--region` | `-r` | 行政区域 | `-r "渝北区"` |
| `--biz-type` | `-b` | 业务类型 | `-b "工程建设"` |
| `--info-type` | `-i` | 信息类型（默认：交易结果） | `-i "招选公告"` |
| `--time-period` | `-t` | 发布时间（默认：近三月） | `-t "近一月"` |

**示例命令：**
```bash
# 搜索渝北区近一月的出租信息
python step1_fetch_links.py -k "出租" -r "渝北区" -t "近一月"
```

运行完成后，结果将保存至 `output/links.json`，Cookie 保存至 `output/cookies.json`。

### 第二步：抓取详情数据

运行 `step2_scrape_details.py` 读取上一步获取的链接，**异步并发**抓取详情页数据。

```bash
python step2_scrape_details.py
```

*   **Cookie 复用**：自动使用 step1 保存的 Cookie，过期时自动重新获取。
*   **并发抓取**：默认 10 并发，速度提升 10-50x。
*   **断点续传**：已完成的记录自动记录在 `output/progress.json` 中。如果程序中断，再次运行将自动跳过已完成的条目。
*   **进度保存**：每抓取 10 条数据会自动保存一次进度。

## 项目结构

```
cqggzy/
├── common/                 # 公共模块
│   ├── __init__.py
│   ├── config.py           # 全局配置常量
│   ├── browser.py          # 浏览器工具 (JSL验证/Cookie管理)
│   └── parser.py           # 数据解析 (API JSON / 详情页 HTML)
├── step1_fetch_links.py    # 第一步：获取链接列表
├── step2_scrape_details.py # 第二步：抓取详情数据
├── requirements.txt        # Python 依赖
├── README.md
├── AGENTS.md
└── .gitignore
```

## 输出文件

所有输出文件位于 `output/` 目录下：

| 文件名 | 说明 |
| :--- | :--- |
| `links.json` | 第一步生成的链接列表（JSON 格式） |
| `cookies.json` | JSL 验证 Cookie（step2 自动复用） |
| `details.csv` | **最终结果**，包含所有详细字段（BOM UTF-8 编码，Excel 可读） |
| `details.json` | 最终结果的 JSON 原始数据 |
| `progress.json` | 抓取进度记录文件（用于断点续传） |

## 性能对比

| 指标 | 原版 | 优化版 |
| :--- | :--- | :--- |
| 500条详情耗时 | ~30 分钟 | ~3 分钟 |
| 内存占用 | ~500MB | ~50MB |
| 浏览器使用 | 全程 | 仅验证阶段 |

## 常见问题

1.  **验证超时/失败**：脚本会自动重试。如果长时间无法通过，请检查网络连接或尝试手动运行浏览器查看情况。
2.  **搜索无结果**：请确认关键词是否准确，或者该条件下确实没有数据。
3.  **Cookie 过期**：step2 会自动检测并重新获取，无需手动处理。
4.  **并发数调整**：修改 `common/config.py` 中的 `MAX_CONCURRENT`（默认 10，建议不超过 20）。
