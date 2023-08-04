# 微博-Discord-机器人

*用其他语言阅读: [English](README.md)*

这个项目是一个基于 Python 的机器人，可以扫描指定的微博账户，并将新的微博发送到相应的 Discord 频道。如果你想要跟踪某些微博账户，并直接将更新信息发送到你的 Discord 服务器，这将是一个非常好用的工具。

## 功能

* 按预定的时间间隔扫描多个微博账户的新帖子。
* 将新帖子发送到为每个微博账户配置的相应的 Discord 频道。
* 处理各种类型的微博帖子，包括：
  * 仅文本的帖子。
  * 带有图片（单张或多张）的帖子。
  * 带有视频内容的帖子。
  * 带有转发内容的帖子。
* 如果一篇帖子包含多张图片，它会创建一个图片的拼图。每个 GIF 文件将在嵌入消息后单独发送。
* 在 SQLite 数据库中存储每个处理过的微博帖子的 ID，以防止重复。
* 每隔几个小时向指定的 Discord 频道发送状态更新，以表示脚本仍在运行。
* 使用 Discord Webhook 将帖子发送到 Discord。

## 工作流程

1. 机器人首先从每个微博账户的微博 AJAX 请求 URL 中获取所有内容。
2. 对于每个检索到的帖子，它会检查帖子的 ID 是否已经在 SQLite 数据库中。
   * 如果 ID 在数据库中，机器人会跳过这个帖子。
   * 如果 ID 不在数据库中，表示它是一个新的帖子，机器人会进行以下步骤：
     * 检查帖子是否是转发。
       * 如果帖子是转发，它会将转发的内容发送到配置的 Discord 频道。
       * 如果帖子不是转发，它会检查帖子是否包含图片或视频。
         * 如果帖子包含一张图片，它会直接将图片发送到 Discord 频道。
         * 如果帖子包含多张图片，它会创建一个图片的拼图并将其发送到 Discord 频道。在图片中发现的每个 GIF 都会在嵌入消息后单独发送。
         * 如果帖子包含视频，它会将视频发送到 Discord 频道。
         * 如果帖子不包含任何图片或视频，它会将帖子的文本发送到 Discord 频道。
3. 机器人在 SQLite 数据库中记录每个新微博帖子的 ID，以防止发送重复的帖子。
4. 每隔几个小时，机器人向指定的 Discord 频道发送状态更新，以表示它仍在运行。

这些操作会根据配置的时间表连续进行。

## 需求

* Python 3.7 或更高版本
* Selenium
* Requests
* Discord Webhook
* Schedule
* Pytz
* SQLite3
* TOML

你可以使用 pip 安装这些包：
```bash
  pip install -r requirements.txt
```

## 使用方法
1. 克隆此仓库。
    ```bash
        git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
        cd weibo-discord-bot
    ```
2. 安装所需的包。
    ```bash
        pip install -r requirements.txt
    ```

3. 使用你的微博和 Discord 信息配置 config.toml 文件。请参考 config_sample.toml 文件并填写你的详细信息。

4. 运行脚本。
```bash
  python app.py
```

对于 `pm2`，配置 `ecosystem.config.js`` 文件然后运行

```bash
  pm2 start ecosystem.config.js
```
关于 pm2 的更多详细信息，请查看 [pm2 文档](https://pm2.keymetrics.io/docs/usage/quick-start/)。

## 从微博获取 AJAX URL

要获取特定微博账户的 AJAX URL，你需要执行以下步骤：

1. 在网络浏览器中打开该账户的微博页面。
2. 打开浏览器的开发者工具中的 Network 标签页。
3. 刷新微博页面。
4. 在 Network 标签页中，寻找名为 mymblog 的请求。这通常是一个 XHR 请求。
5. 右键点击此请求，选择 "Copy > Copy link address"（具体词汇可能会根据你的浏览器有所不同）。
6. 复制的 URL 就是这个微博账户的 AJAX URL。将此 URL 粘贴到 config.toml 文件中。

例如，AJAX URL 可能看起来像这样：

```url
https://weibo.com/ajax/statuses/mymblog?uid=7618923072&page=1&feature=0
```

在这个 URL 中：

* uid 代表微博账户的用户 ID。这是你想要监视的微博账户的用户 ID。
* page 代表微博账户帖子的页数。通常，你会将此设置为 1 以获取最新的帖子。
* feature 是一个用来指定你想要检索的帖子类型的过滤器。例如，feature=0 通常返回所有类型的帖子，feature=1 返回原创帖子（不包括转发或转推），feature=2 返回图片帖子，feature=3 返回视频帖子，feature=4 返回音乐帖子。你可以根据需要调整此参数。

请注意，AJAX URL 可能会随着时间的推移或微博平台更新而变化。如果机器人停止工作，你可能需要更新 AJAX URL。

## 参与贡献
欢迎参与贡献！请随时提交 Pull Request。

## 许可证
此项目根据 MIT 许可证的条款进行许可。有关更多详细信息，请查看仓库中的 LICENSE 文件。