# Weibo-Discord-Bot

*Read this in other languages: [简体中文](README.zh-CN.md)*

This project is a Python-based bot that scans specified Weibo accounts and sends new posts to corresponding Discord channels. It's a great tool if you want to keep track of certain Weibo accounts and have updates delivered directly to your Discord server.

## Features

* Scans multiple Weibo accounts for new posts at scheduled intervals.
* Sends new posts to corresponding Discord channels configured for each Weibo account.
* Handles different types of Weibo posts including:
  * Text only posts.
  * Posts with images (single or multiple).
  * Posts with video content.
  * Posts with retweeted content.
* If a post contains multiple images, it creates a collage of the images. Each GIF file will be send separately following the embed message.
* Stores the ID of each processed Weibo post in a SQLite database to prevent duplication.
* Sends a status update to a specified Discord channel every scheduled hours to indicate that the script is still running.
* Uses Discord Webhook to deliver posts to Discord.

## Workflow

1. The bot first retrieves all contents from the Weibo AJAX request URL of each Weibo account.
2. For each retrieved post, it checks if the ID of the post is already in the SQLite database.
   * If the ID is in the database, the bot skips this post.
   * If the ID is not in the database, indicating it's a new post, the bot proceeds with the following steps:
     * Checks whether the post is a retweet.
       * If the post is a retweet, it sends the retweeted content to the configured Discord channel.
       * If the post is not a retweet, it checks whether the post contains images or video.
         * If the post contains a single image, it sends the image directly to the Discord channel.
         * If the post contains multiple images, it creates a collage of the images and sends it to the Discord channel. Each GIF found among the images is sent separately following the embed message.
         * If the post contains a video, it sends the video to the Discord channel.
         * If the post does not contain any images or video, it sends the text of the post to the Discord channel.
3. The bot records the ID of each new Weibo post in a SQLite database to prevent sending duplicate posts.
4. Every scheduled hours, the bot sends a status update to a specified Discord channel to indicate that it is still running.

These operations are performed continuously according to the configured schedule.

## Requirements

* Python 3.7 or above
* Selenium
* Requests
* Discord Webhook
* Schedule
* Pytz
* SQLite3
* TOML

You can install these packages using pip:
```bash
  pip install -r requirements.txt
```

## Usage

1. Clone this repository.

```bash
  git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
  cd weibo-discord-bot
```

2. Install the required packages.

```bash
  pip install -r requirements.txt
```

3. Configure a `config.toml` file with your Weibo and Discord information. Please refer to `config_example.toml` file and fill in your details.

4. Change the list `accounts` in `app.py` to reflect your changes in `config.toml` file.
   
5. Run the script.

```bash
  python app.py
```

For `pm2`, configure the `ecosystem.config.js` file then run
```bash
  pm2 start ecosystem.config.js
```
For more details about pm2, check [pm2 documentation](https://pm2.keymetrics.io/docs/usage/quick-start/).

## Obtaining the AJAX URL from Weibo

To get the AJAX URL for a specific Weibo account, you need to perform the following steps:

1. Open the Weibo page of the account in a web browser.
2. Open the Network tab in the browser's Developer Tools.
3. Reload the Weibo page.
4. In the Network tab, look for a request of name `mymblog`. This is usually an XHR request.
5. Right-click this request and select "Copy > Copy link address" (the exact wording may vary depending on your browser).
6. The copied URL is the AJAX URL for this Weibo account. Paste this URL into the `config.toml` file.

For example, the AJAX URL could look like this: 

```url
https://weibo.com/ajax/statuses/mymblog?uid=7618923072&page=1&feature=0
```

In this URL:

* `uid` represents the User ID of the Weibo account. This is the user ID of the Weibo account you want to monitor.
* `page` represents the page number of the Weibo account's posts. Usually, you would set this to 1 to get the most recent posts.
* `feature` is a filter used to specify the type of posts you want to retrieve. For instance, `feature=0` generally returns all types of posts, `feature=1` returns original posts (not including reposts or retweets), `feature=2` returns image posts, `feature=3` returns video posts, `feature=4` returns music posts. You can adjust this parameter according to your needs.

Please note that the AJAX URL can change over time or depending on the Weibo platform updates. If the bot stops working, you might need to update the AJAX URL.


## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE) file in the repository.