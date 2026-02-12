# 重庆公共资源交易网爬虫使用指南

本项目包含两个主要脚本，分别用于获取交易链接和抓取详细信息。

## 1. 环境准备

确保已安装依赖：

```bash
pip install playwright
playwright install
```

## 2. 第一步：获取链接列表

`step1_fetch_links.py` 用于搜索符合条件的交易信息并保存链接。此脚本支持命令行参数来指定筛选条件。

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
运行完成后，链接列表将保存至 `output/links.json`。

---

## 3. 第二步：抓取详情数据

`step2_scrape_details.py` 会读取 `output/links.json` 中的链接，逐个访问详情页并提取结构化数据。

**运行命令：**
```bash
python step2_scrape_details.py
```

*注意：此脚本支持断点续传。如果中断，再次运行会自动跳过已抓取的记录。*

**输出：**
- `output/details.csv`: 抓取结果表格（Excel 可打开）
- `output/details.json`: 抓取结果原始数据
