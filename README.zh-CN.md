# 微博-Discord-机器人

*用其他语言阅读: [English](README.md)*

这个项目是一个基于 Python 的机器人，可以扫描指定的微博账户，并将新的微博发送到相应的 Discord 频道。如果你想要跟踪某些微博账户，并直接将更新信息发送到你的 Discord 服务器，这将是一个非常好用的工具。

## 🚀 功能特性

* **多账户监控**: 按预定的时间间隔扫描多个微博账户的新帖子
* **丰富内容支持**: 处理各种类型的微博帖子，包括：
  * 仅文本的帖子
  * 带有图片（单张或多张）的帖子
  * 带有视频内容的帖子
  * 带有转发内容的帖子
* **智能图片处理**: 
  * 为多张图片创建拼图
  * 单独发送 GIF 文件以获得更好的 Discord 兼容性
  * 自动图片压缩和调整大小（最大 1024x1024）
  * 积极压缩以保持在 Discord 的 8MB 限制内
* **重复预防**: 在 SQLite 数据库中存储已处理帖子的 ID
* **状态监控**: 每 6 小时发送状态更新以确认机器人正在运行
* **跨平台支持**: 支持 Windows、macOS 和 Linux
* **自动驱动管理**: 自动下载和管理 ChromeDriver/GeckoDriver
* **企业级安全**: 全面的安全功能和输入验证
* **速率限制**: 内置速率限制以防止 API 滥用
* **全面日志记录**: 详细的日志记录，支持文件轮转和监控
* **浏览器内 AJAX 抓取**: 在 Selenium 中直接获取 JSON，无需手动提供 AJAX URL
* **可选移动端 DOM 抽取**: 在代码中切换，修改 `core/settings.py` 的 `EXTRACTION_METHOD`

## 🛡️ 安全功能

* **输入验证**: 针对白名单的 URL 验证，文件扩展名验证
* **速率限制**: 每分钟最多 5 个请求以防止 API 滥用
* **文件安全**: 大小限制，内容类型验证，安全的文件操作
* **数据库安全**: SQL 注入防护，连接超时，自动清理
* **WebDriver 安全**: 无头模式，反检测措施，安全标志
* **日志记录和监控**: 结构化日志记录，错误跟踪，不暴露敏感数据

## 🔄 工作流程

1. **内容获取**: 机器人从微博 AJAX 端点获取内容
2. **重复检查**: 检查帖子 ID 是否存在于 SQLite 数据库中
3. **内容处理**: 
   - **转发**: 将转发内容发送到 Discord
   - **图片**: 下载、压缩，并在需要时创建拼图
   - **视频**: 将视频链接发送到 Discord
   - **文本**: 发送纯文本帖子
4. **数据库更新**: 记录新帖子 ID 以防止重复
5. **状态更新**: 发送定期状态更新以确认机器人运行

## 📋 系统要求

* Python 3.7 或更高版本
* Chrome 或 Firefox 浏览器（用于网页抓取）
* 互联网连接（用于自动下载驱动程序）

## 🚀 快速开始

```bash
git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
cd weibo-discord-bot
pip install -r requirements.txt
cp config.toml.example config.toml
# 编辑 config.toml 后运行：
python app.py
```

## ⚙️ 配置

1. **复制并编辑配置文件**
   ```bash
   cp config.toml.example config.toml
   ```

2. **使用你的设置编辑 `config.toml`**
   ```toml
   [weibo]
       [weibo.your_account_name]
           read_link_url = "https://weibo.com/u/YOUR_UID"
           message_webhook = "YOUR_DISCORD_WEBHOOK_URL"
           avatar_url = "OPTIONAL_AVATAR_URL"
           title = "Your Account Title"
   
   [status]
       message_webhook = "YOUR_STATUS_WEBHOOK_URL"
   ```

- 抽取方式在代码中设置：编辑 `core/settings.py` 的 `EXTRACTION_METHOD` 为 `"ajax_json"` 或 `"mobile_dom"`。

3. **可选：配置安全设置**
   ```bash
   # 编辑 security_config.toml 进行高级安全设置
   # 查看 SECURITY.md 了解详细的安全文档
   ```

## 🎯 使用方法

### 基本使用
```bash
python app.py
```

### 生产部署（可选）
```bash
pm2 start ecosystem.config.js
```

### 使用 Conda 环境
```bash
conda activate web
python app.py
```

## 🔧 运行参数（在代码中修改）

- 抽取方式：`core/settings.py` → `EXTRACTION_METHOD`（默认 `"ajax_json"`，可改为 `"mobile_dom"`）
- 速率限制：`core/settings.py` → `RATE_LIMIT_MAX_REQUESTS`、`RATE_LIMIT_TIME_WINDOW`
- 超时与大小：`core/settings.py` → `REQUEST_TIMEOUT_SECONDS`、`IMAGE_MAX_DOWNLOAD_BYTES`、`DISCORD_ATTACHMENT_MAX_MB`
- AJAX 等待时间：`core/settings.py` → `AJAX_WAIT_MS`

## 📊 监控和日志记录

机器人提供全面的日志记录：
- **文件日志记录**: `weibo_bot.log` 支持自动轮转
- **控制台输出**: 实时状态更新
- **错误跟踪**: 详细的错误日志记录，包含堆栈跟踪
- **性能监控**: 数据库清理，内存使用跟踪

### 日志级别
- `DEBUG`: 详细的调试信息
- `INFO`: 一般操作信息
- `WARNING`: 潜在问题的警告消息
- `ERROR`: 包含完整上下文的错误消息

> 说明：机器人会在浏览器会话内自动发起 AJAX 请求，你无需手动收集或提供 AJAX URL。

 

> 临时 JSON 保存在 `weibo_tmp/` 下，随时可删除。数据库位于 `data/weibo.db`。

 

 

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE)。

 
