# Apify Store Actors Scraper

这个项目是一个使用Playwright和Python开发的网络爬虫，用于抓取[Apify商店](https://apify.com/store/categories)中的所有actors数据。

## 功能

- 自动滚动加载所有actors（共约4000+条记录）
- 提取每个actor的详细信息：
  - 标题
  - Slug (URL标识符)
  - 描述
  - 作者名称
  - 用户数
  - 评分
- 将抓取的数据保存为CSV文件

## 环境要求

- Python 3.8+
- Playwright
- Pandas
- 其他依赖库（见`requirements.txt`）

## 安装

1. 克隆本仓库：
```bash
git clone <repository-url>
cd apify
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装Playwright浏览器：
```bash
playwright install
```

## 使用方法

直接运行脚本开始抓取：

```bash
python scrape_actors.py
```

脚本将自动：
1. 打开浏览器访问Apify商店
2. 滚动页面直到加载所有actors
3. 提取所有actors的数据
4. 保存为`apify_actors.csv`文件

## 输出示例

生成的CSV文件包含以下字段：
- `title`: Actor标题
- `slug`: Actor的唯一标识符
- `description`: Actor的描述
- `author`: 作者名称
- `users`: 用户数
- `rating`: 评分
- `url`: Actor的URL

## 注意事项

- 爬虫使用无头浏览器模式运行，过程中会显示浏览器界面
- 完整抓取过程可能需要几分钟时间，取决于网络速度和总记录数
- 脚本包含自动检测，当连续多次滚动没有加载新内容时，将自动停止抓取