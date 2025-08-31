# GitHub Sentinel

![GitHub License](https://img.shields.io/github/license/your-username/github-sentinel)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![GitHub Stars](https://img.shields.io/github/stars/your-username/github-sentinel?style=social)

GitHub Sentinel 是一款开源的 AI 驱动型工具，专为开发者和项目管理人员打造，旨在自动化 GitHub 仓库的动态跟踪与协作流程。通过定期监控并汇总关注仓库的更新，帮助团队实时掌握项目进展，减少信息延迟，提升协作效率。


## 🚀 核心功能

| 功能模块         | 核心能力                                                                 |
|------------------|--------------------------------------------------------------------------|
| **订阅管理**     | 灵活添加/移除仓库订阅，支持多订阅者管理，自定义通知频率（每日/每周）     |
| **智能更新获取** | 高效抓取 GitHub 仓库动态（发布、提交、PR、Issues），自动避免重复 API 调用 |
| **多渠道通知**   | 支持邮件、Slack 等方式推送关键更新，确保重要变更不遗漏                   |
| **定制化报告**   | 生成 Markdown/HTML 格式的单仓库报告或多仓库汇总报告，支持历史报告归档   |
| **灵活配置**     | 支持环境变量、配置文件双重配置，适配开发/生产等不同场景                 |


## 📋 适用场景

- **依赖跟踪**：监控第三方库的版本更新与安全补丁
- **开源协作**：跟踪开源项目的开发动态，及时参与贡献
- **团队管理**：同步多仓库项目的变更，确保团队信息一致
- **个人项目**：集中管理个人关注的多个仓库更新，无需逐个检查


## ⚙️ 快速开始

### 1. 环境准备

- Python 3.8 及以上版本
- GitHub 个人访问令牌（[获取地址](https://github.com/settings/tokens)，需勾选 `repo` 权限）


### 2. 安装部署

#### 方式 1：直接克隆仓库

```bash
# 克隆仓库
git clone https://github.com/your-username/github-sentinel.git
cd github-sentinel

# 安装依赖
pip install -r requirements.txt
```

#### 方式 2：使用虚拟环境（推荐）

```bash
# 创建并激活虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```


### 3. 配置文件

1. 复制默认配置文件模板并修改：
   ```bash
   cp config.yaml.example config.yaml
   ```

2. 编辑 `config.yaml` 关键配置项：
   ```yaml
   # 必须配置：GitHub 个人访问令牌
   github_token: "your_github_personal_access_token_here"

   # 可选：调整任务调度时间（每日/每周）
   scheduler:
     daily_time: "08:30"       # 每日检查时间（24小时制）
     weekly_day: "monday"      # 每周检查日（monday~sunday）
     weekly_time: "09:00"      # 每周检查时间

   # 可选：配置通知方式（邮件/Slack）
   notifications:
     email:
       enabled: true
       smtp_server: "smtp.gmail.com"  # 你的SMTP服务器
       smtp_username: "your-email@gmail.com"
       smtp_password: "your-app-password"  # 邮箱密码/应用专用密码
     slack:
       enabled: false
       webhook_url: "https://hooks.slack.com/services/XXXXXX"  # 你的Slack Webhook
   ```


### 4. 启动运行

#### 方式 1：直接启动主程序

```bash
python main.py
```

#### 方式 2：运行示例脚本（生成单仓库报告）

```bash
# 生成 langchain-ai/langchain 仓库的最新报告
python examples/generate_langchain_report.py
```


### 5. 查看结果

- **报告输出**：默认保存到 `reports/` 目录，支持 Markdown/HTML 格式
- **日志输出**：控制台实时显示日志，同时保存到 `logs/github-sentinel.log`（可配置）
- **订阅数据**：订阅信息默认存储到 `data/subscriptions.json`（JSON 格式，持久化）


## 📖 使用指南

### 1. 管理订阅

#### 添加订阅

```python
from subscription.manager import SubscriptionManager
from core.config import Config

# 加载配置
config = Config.from_file("config.yaml")
# 初始化订阅管理器
sub_manager = SubscriptionManager(config)

# 添加订阅：仓库名 + 订阅者邮箱 + 通知频率
sub_manager.add_subscription(
    repository="langchain-ai/langchain",
    subscriber="user@example.com",
    daily_updates=True,  # 接收每日更新
    weekly_report=True   # 接收每周报告
)
```

#### 移除订阅

```python
# 方式 1：通过订阅ID移除
sub_manager.remove_subscription(subscription_id=1)

# 方式 2：从指定仓库移除单个订阅者
sub_manager.remove_subscriber(
    repository="langchain-ai/langchain",
    subscriber="user@example.com"
)
```

#### 查看订阅

```python
# 查看所有订阅
all_subs = sub_manager.get_all_subscriptions()

# 查看指定订阅者的所有订阅
user_subs = sub_manager.get_subscriptions_for_subscriber("user@example.com")
```


### 2. 生成报告

#### 生成单仓库报告

```python
from report.generator import ReportGenerator
from github.client import GitHubClient
from core.config import Config

config = Config.from_file("config.yaml")
github_client = GitHubClient(config.get("github_token"))
report_generator = ReportGenerator(github_client, config)

# 生成报告（支持按时间筛选）
report = report_generator.generate_repo_report(
    repo_full_name="langchain-ai/langchain",
    since=None  # None 表示获取所有最新信息，可传入 datetime 对象筛选时间范围
)

# 保存报告到文件
report_path = report_generator.save_report(report, "langchain-ai/langchain")
print(f"报告已保存：{report_path}")
```

#### 生成每周汇总报告

```python
# 获取所有订阅
subscriptions = sub_manager.get_all_subscriptions()

# 生成每周汇总报告
weekly_report = report_generator.generate_weekly_report(subscriptions)

# 保存汇总报告
report_generator.save_report(weekly_report, "weekly_summary")
```


### 3. 配置定时任务

主程序 `main.py` 已内置定时任务逻辑，启动后会根据 `config.yaml` 中的调度配置自动执行：
- 每日任务：按 `scheduler.daily_time` 检查所有订阅仓库的更新，推送通知并生成日报
- 每周任务：按 `scheduler.weekly_day` 和 `scheduler.weekly_time` 生成周报并推送


## 🛠️ 项目结构

```
github-sentinel/
├── core/                 # 核心模块
│   ├── config.py         # 配置管理（支持YAML/环境变量）
│   ├── logger.py         # 日志系统（控制台+文件输出，支持等级配置）
│   └── scheduler.py      # 定时任务调度（基于schedule库）
├── github/               # GitHub 交互模块
│   ├── client.py         # GitHub API 客户端（获取仓库信息、更新）
│   └── parser.py         # 数据解析（格式化API返回结果）
├── subscription/         # 订阅管理模块
│   ├── models.py         # 数据模型（Subscription类）
│   ├── manager.py        # 订阅业务逻辑（增删改查）
│   └── storage.py        # 订阅存储（支持内存/JSON文件）
├── notification/         # 通知模块
│   ├── base.py           # 通知基类（统一接口）
│   ├── email.py          # 邮件通知（SMTP）
│   ├── slack.py          # Slack通知（Webhook）
│   └── manager.py        # 通知管理器（协调多渠道通知）
├── report/               # 报告模块
│   ├── generator.py      # 报告生成器（单仓库/汇总报告）
│   └── formatter.py      # 报告格式化（Markdown/HTML）
├── examples/             # 示例脚本
│   └── generate_langchain_report.py  # 生成LangChain仓库报告示例
├── config.yaml.example   # 配置文件模板
├── requirements.txt      # 依赖清单
├── main.py               # 主程序入口
└── README.md             # 项目文档（本文档）
```


## 📦 依赖清单

核心依赖已整理在 `requirements.txt` 中，主要包括：
- `requests`：GitHub API 调用
- `PyYAML`：配置文件解析
- `schedule`：定时任务调度
- `python-dotenv`：环境变量管理（可选）
- `smtplib`/`email`：邮件通知（Python 标准库）


## 🔧 常见问题

### Q1: 启动时报错 `ModuleNotFoundError: No module named 'xxx'`
A1: 缺少依赖，执行 `pip install -r requirements.txt` 安装所有依赖。

### Q2: 日志等级不生效
A2: 确保 `config.yaml` 中 `logging.level` 配置正确（支持 DEBUG/INFO/WARNING/ERROR/CRITICAL），且 `core/logger.py` 已正确引入 `logging` 模块。

### Q3: 定时任务不执行
A3: 检查 `config.yaml` 中 `scheduler` 配置：
- `daily_time` 格式是否为 `"HH:MM"`（如 `"08:30"`）
- `weekly_day` 是否为小写英文（如 `"monday"`）
- 确保程序持续运行（后台运行可使用 `nohup python main.py &`，Windows 可使用任务计划程序）

### Q4: GitHub API 调用失败
A4: 
1. 检查 `github_token` 是否有效且权限足够（需 `repo` 权限）
2. 查看日志文件 `logs/github-sentinel.log` 中的具体错误信息
3. 若提示 API 速率限制，可更换令牌或等待限制重置（GitHub 匿名 API 速率较低，建议使用令牌）


## 🤝 贡献指南

欢迎通过以下方式参与项目贡献：

1. **提交 Issue**：报告 bug、提出新功能建议（[Issue 地址](https://github.com/your-username/github-sentinel/issues)）
2. **提交 PR**：
   -  Fork 本仓库
   -  创建特性分支（`git checkout -b feature/xxx`）
   -  提交代码（`git commit -m "feat: 添加xxx功能"`）
   -  推送分支（`git push origin feature/xxx`）
   -  发起 Pull Request
3. **文档改进**：优化 README 或添加使用示例


## 📄 许可证

本项目采用 **MIT 许可证**，详情见 [LICENSE](https://github.com/your-username/github-sentinel/blob/main/LICENSE) 文件。


## 📞 联系我们

若有问题或建议，可通过以下方式联系：
- GitHub Issues：[https://github.com/your-username/github-sentinel/issues](https://github.com/your-username/github-sentinel/issues)
- 邮箱：your-email@example.com
