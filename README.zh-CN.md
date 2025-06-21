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

## 🚀 安装

### Windows（推荐）

1. **使用 Conda 快速安装**
   ```bash
   git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
   cd weibo-discord-bot
   setup_windows.bat
   ```

2. **手动安装**
   ```bash
   git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
   cd weibo-discord-bot
   python setup_windows.py
   ```

### macOS/Linux

```bash
git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
cd weibo-discord-bot
pip install -r requirements.txt
```

## ⚙️ 配置

1. **复制并编辑配置文件**
   ```bash
   cp config_example.toml config.toml
   ```

2. **使用你的设置编辑 `config.toml`**
   ```toml
   [weibo]
       [weibo.your_account_name]
           ajax_url = "https://weibo.com/ajax/statuses/mymblog?uid=YOUR_UID&page=1&feature=0"
           read_link_url = "https://weibo.com/u/YOUR_UID"
           message_webhook = "YOUR_DISCORD_WEBHOOK_URL"
           avatar_url = "OPTIONAL_AVATAR_URL"
           title = "Your Account Title"
   
   [status]
       message_webhook = "YOUR_STATUS_WEBHOOK_URL"
   ```

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

### 使用 PM2 进行生产部署
```bash
# 配置 ecosystem.config.js 然后运行：
pm2 start ecosystem.config.js
```

### 使用 Conda 环境
```bash
conda activate web
python app.py
```

## 🔧 高级配置

### 安全配置
机器人包含一个全面的安全配置文件（`security_config.toml`），具有以下设置：
- 速率限制参数
- 文件大小限制
- 超时设置
- 允许的域名和文件扩展名
- 日志配置
- 反检测设置

### 环境变量
为了增强安全性，你可以使用环境变量：
```bash
export DISCORD_WEBHOOK_URL="your_webhook_url"
export WEIBO_API_KEY="your_api_key"  # 如果适用
```

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

## 🔍 获取微博 AJAX URL

1. 在浏览器中打开微博账户页面
2. 打开开发者工具 → 网络标签页
3. 重新加载页面
4. 查找 `mymblog` XHR 请求
5. 复制请求 URL

示例 AJAX URL：
```
https://weibo.com/ajax/statuses/mymblog?uid=7618923072&page=1&feature=0
```

**参数说明：**
- `uid`: 微博账户用户 ID
- `page`: 页码（通常为 1 以获取最新帖子）
- `feature`: 内容过滤器（0=全部，1=原创，2=图片，3=视频，4=音乐）

## 🛠️ 故障排除

### 常见问题

1. **Webhook 错误（413 负载过大）**
   - 机器人自动压缩图片以保持在 Discord 限制内
   - 检查日志了解压缩详情
   - 图片调整到最大 1024x1024 像素

2. **Chrome 驱动程序问题**
   - 机器人自动下载和管理驱动程序
   - 检查互联网连接以下载驱动程序
   - 防病毒软件可能暂时阻止驱动程序下载

3. **数据库错误**
   - 删除 `weibo.db` 以重置数据库
   - 检查项目目录中的文件权限
   - 数据库自动清理旧记录

4. **速率限制**
   - 机器人包含内置速率限制（每分钟 5 个请求）
   - 检查日志中的速率限制警告
   - 如有需要，在 `security_config.toml` 中调整设置

### Windows 特定问题

1. **权限错误**
   - 以管理员身份运行命令提示符/PowerShell
   - 暂时禁用防病毒软件以下载驱动程序

2. **Chrome 语音转录日志**
   - 这些是正常的 Chrome 内部日志
   - 机器人抑制大多数 Chrome 警告
   - 日志不影响功能

### 调试模式
```bash
# 测试配置和依赖项
python test_app.py

# 检查最近的数据库记录
python -c "from app import DatabaseManager; db = DatabaseManager(); print(db.get_recent_ids(10))"
```

## 🔒 安全注意事项

### Webhook 安全
- 保持 webhook URL 私密和安全
- 定期轮换 webhook URL
- 监控 webhook 使用情况以发现未授权活动

### 文件安全
- 机器人仅从受信任的域名下载
- 所有文件都经过内容类型和大小验证
- 临时文件自动清理

### 网络安全
- 所有请求都使用 HTTPS
- 速率限制防止 API 滥用
- 请求超时防止连接挂起

有关详细的安全信息，请参阅 [SECURITY.md](SECURITY.md)。

## 📈 性能特性

- **图片优化**: 自动压缩和调整大小
- **数据库索引**: 使用适当索引的优化查询
- **内存管理**: 自动清理旧记录和文件
- **连接池**: 高效的数据库和网络连接
- **批量操作**: 优化的数据库操作

## 🤝 参与贡献

欢迎贡献！请：
1. Fork 仓库
2. 创建功能分支
3. 进行更改
4. 如果适用，添加测试
5. 提交拉取请求

### 开发设置
```bash
git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
cd weibo-discord-bot
pip install -r requirements.txt
# 进行更改
python test_app.py  # 运行测试
```

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE)。

## 🙏 致谢

- 微博提供平台
- Discord 提供 webhook 功能
- Selenium 提供网页自动化
- 本项目的所有贡献者和用户

---

**⚠️ 重要提示**: 此机器人仅供教育和个人使用。请尊重微博的服务条款和速率限制。机器人包含内置速率限制以尊重微博服务器。