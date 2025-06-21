# Weibo-Discord-Bot

*Read this in other languages: [简体中文](README.zh-CN.md)*

This project is a Python-based bot that scans specified Weibo accounts and sends new posts to designated Discord channels. It's a great tool if you want to keep track of certain Weibo accounts and have updates delivered directly to your Discord server.

## 🚀 Features

* **Multi-Account Monitoring**: Scans multiple Weibo accounts for new posts at scheduled intervals
* **Rich Content Support**: Handles different types of Weibo posts including:
  * Text-only posts
  * Posts with images (single or multiple)
  * Posts with video content
  * Posts with retweeted content
* **Smart Image Processing**: 
  * Creates collages for multiple images
  * Sends GIFs separately for better Discord compatibility
  * Automatic image compression and resizing (max 1024x1024)
  * Aggressive compression to stay under Discord's 8MB limit
* **Duplicate Prevention**: Stores processed post IDs in SQLite database
* **Status Monitoring**: Sends status updates every 6 hours to confirm bot is running
* **Cross-Platform Support**: Works on Windows, macOS, and Linux
* **Automatic Driver Management**: ChromeDriver/GeckoDriver automatically downloaded and managed
* **Enterprise Security**: Comprehensive security features and input validation
* **Rate Limiting**: Built-in rate limiting to prevent API abuse
* **Comprehensive Logging**: Detailed logging with file rotation and monitoring

## 🛡️ Security Features

* **Input Validation**: URL validation against whitelist, file extension validation
* **Rate Limiting**: Maximum 5 requests per minute to prevent API abuse
* **File Security**: Size limits, content type validation, safe file operations
* **Database Security**: SQL injection prevention, connection timeouts, automatic cleanup
* **WebDriver Security**: Headless mode, anti-detection measures, security flags
* **Logging & Monitoring**: Structured logging, error tracking, no sensitive data exposure

## 🔄 Workflow

1. **Content Retrieval**: Bot retrieves content from Weibo AJAX endpoints
2. **Duplicate Check**: Checks if post ID exists in SQLite database
3. **Content Processing**: 
   - **Retweets**: Sends retweeted content to Discord
   - **Images**: Downloads, compresses, and creates collages if needed
   - **Videos**: Sends video links to Discord
   - **Text**: Sends text-only posts
4. **Database Update**: Records new post IDs to prevent duplicates
5. **Status Updates**: Sends periodic status updates to confirm bot operation

## 📋 Requirements

* Python 3.7 or above
* Chrome or Firefox browser (for web scraping)
* Internet connection (for automatic driver download)

## 🚀 Installation

### Windows (Recommended)

1. **Quick Setup with Conda**
   ```bash
   git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
   cd weibo-discord-bot
   setup_windows.bat
   ```

2. **Manual Setup**
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

## ⚙️ Configuration

1. **Copy and edit configuration**
   ```bash
   cp config_example.toml config.toml
   ```

2. **Edit `config.toml` with your settings**
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

3. **Optional: Configure security settings**
   ```bash
   # Edit security_config.toml for advanced security settings
   # See SECURITY.md for detailed security documentation
   ```

## 🎯 Usage

### Basic Usage
```bash
python app.py
```

### Production Deployment with PM2
```bash
# Configure ecosystem.config.js then run:
pm2 start ecosystem.config.js
```

### With Conda Environment
```bash
conda activate web
python app.py
```

## 🔧 Advanced Configuration

### Security Configuration
The bot includes a comprehensive security configuration file (`security_config.toml`) with settings for:
- Rate limiting parameters
- File size limits
- Timeout settings
- Allowed domains and file extensions
- Logging configuration
- Anti-detection settings

### Environment Variables
For enhanced security, you can use environment variables:
```bash
export DISCORD_WEBHOOK_URL="your_webhook_url"
export WEIBO_API_KEY="your_api_key"  # If applicable
```

## 📊 Monitoring & Logging

The bot provides comprehensive logging:
- **File Logging**: `weibo_bot.log` with automatic rotation
- **Console Output**: Real-time status updates
- **Error Tracking**: Detailed error logging with stack traces
- **Performance Monitoring**: Database cleanup, memory usage tracking

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages with full context

## 🔍 Obtaining Weibo AJAX URLs

1. Open the Weibo account page in your browser
2. Open Developer Tools → Network tab
3. Reload the page
4. Look for `mymblog` XHR request
5. Copy the request URL

Example AJAX URL:
```
https://weibo.com/ajax/statuses/mymblog?uid=7618923072&page=1&feature=0
```

**Parameters:**
- `uid`: Weibo account User ID
- `page`: Page number (usually 1 for recent posts)
- `feature`: Content filter (0=all, 1=original, 2=images, 3=videos, 4=music)

## 🛠️ Troubleshooting

### Common Issues

1. **Webhook Errors (413 Payload Too Large)**
   - Bot automatically compresses images to stay under Discord limits
   - Check logs for compression details
   - Images are resized to max 1024x1024 pixels

2. **Chrome Driver Issues**
   - Bot automatically downloads and manages drivers
   - Check internet connection for driver downloads
   - Antivirus may block driver downloads temporarily

3. **Database Errors**
   - Delete `weibo.db` to reset database
   - Check file permissions in project directory
   - Database automatically cleans up old records

4. **Rate Limiting**
   - Bot includes built-in rate limiting (5 requests/minute)
   - Check logs for rate limit warnings
   - Adjust settings in `security_config.toml` if needed

### Windows-Specific Issues

1. **Permission Errors**
   - Run Command Prompt/PowerShell as Administrator
   - Temporarily disable antivirus for driver downloads

2. **Chrome Voice Transcription Logs**
   - These are normal Chrome internal logs
   - Bot suppresses most Chrome warnings
   - Logs don't affect functionality

### Debug Mode
```bash
# Test configuration and dependencies
python test_app.py

# Check recent database records
python -c "from app import DatabaseManager; db = DatabaseManager(); print(db.get_recent_ids(10))"
```

## 🔒 Security Considerations

### Webhook Security
- Keep webhook URLs private and secure
- Regularly rotate webhook URLs
- Monitor webhook usage for unauthorized activity

### File Security
- Bot only downloads from trusted domains
- All files are validated for content type and size
- Temporary files are automatically cleaned up

### Network Security
- All requests use HTTPS
- Rate limiting prevents API abuse
- Request timeouts prevent hanging connections

For detailed security information, see [SECURITY.md](SECURITY.md).

## 📈 Performance Features

- **Image Optimization**: Automatic compression and resizing
- **Database Indexing**: Optimized queries with proper indexing
- **Memory Management**: Automatic cleanup of old records and files
- **Connection Pooling**: Efficient database and network connections
- **Batch Operations**: Optimized database operations

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup
```bash
git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
cd weibo-discord-bot
pip install -r requirements.txt
# Make your changes
python test_app.py  # Run tests
```

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Weibo for providing the platform
- Discord for webhook functionality
- Selenium for web automation
- All contributors and users of this project

---

**⚠️ Important**: This bot is for educational and personal use. Please respect Weibo's terms of service and rate limits. The bot includes built-in rate limiting to be respectful to Weibo's servers.