# 重庆公共资源交易网爬虫使用指南

本项目包含两个主要脚本，分别用于获取交易链接和抓取详细信息。

## 架构

采用 **"浏览器开门 + HTTP 干活"** 架构：
- **Playwright** 仅用于通过 JSL 反爬验证和拦截 API 请求体
- **httpx** 用于高速翻页和异步并发抓取详情页
- **BeautifulSoup** 用于解析详情页 HTML

## 1. 环境准备

确保已安装依赖：

```bash
pip install -r requirements.txt
playwright install chromium
```

## 2. 第一步：获取链接列表

`step1_fetch_links.py` 用于搜索符合条件的交易信息并保存链接。

**基本用法（使用默认配置）：**
```bash
python step1_fetch_links.py
```
*默认配置：关键词=""（全部），区域=全部，业务类型=全部，信息类型="交易结果"，发布时间="近三月"*

**使用参数自定义筛选：**

| 参数 | 简写 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `--keyword` | `-k` | 标题包含的关键词 | `-k "出租"` |
| `--region` | `-r` | 行政区域 | `-r "渝北区"` |
| `--biz-type` | `-b` | 业务类型 | `-b "工程建设"` |
| `--info-type` | `-i` | 信息类型（默认：交易结果） | `-i "招标公告"` |
| `--time-period` | `-t` | 发布时间（默认：近三月） | `-t "近一月"` |

**示例命令：**

1.  **搜索渝北区近一月的出租信息：**
    ```bash
    python step1_fetch_links.py -k "出租" -r "渝北区" -t "近一月"
    ```

2.  **搜索从中介超市发布的招选公告：**
    ```bash
    python step1_fetch_links.py -b "中介超市" -i "招选公告"
    ```

**输出：**
- `output/links.json` — 链接列表
- `output/cookies.json` — JSL 验证 Cookie（供 step2 复用）

---

## 3. 第二步：抓取详情数据

`step2_scrape_details.py` 会读取 `output/links.json` 中的链接，异步并发抓取详情页数据。

**运行命令：**
```bash
python step2_scrape_details.py
```

*注意：*
- 自动复用 step1 保存的 Cookie，过期时自动重新获取
- 默认 10 并发，可在 `common/config.py` 中调整 `MAX_CONCURRENT`
- 支持断点续传：中断后再次运行自动跳过已抓取的记录

**输出：**
- `output/details.csv` — 抓取结果表格（Excel 可打开）
- `output/details.json` — 抓取结果原始数据

---

## 4. 配置调整

所有配置集中在 `common/config.py` 中：

| 配置项 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `MAX_CONCURRENT` | 10 | 异步并发抓取数（建议不超过 20） |
| `REQUEST_TIMEOUT` | 15 | HTTP 请求超时（秒） |
| `BATCH_SIZE` | 10 | 每批保存进度的条数 |
| `PAGE_SIZE` | 20 | API 每页返回条数 |
