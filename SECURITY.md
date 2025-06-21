# Security Guide for Weibo Discord Bot

## 🔒 Security Overview

This document outlines security best practices, potential vulnerabilities, and mitigation strategies for the Weibo Discord Bot.

## 🛡️ Security Features Implemented

### 1. Input Validation & Sanitization
- **URL Validation**: All URLs are validated against a whitelist of allowed domains
- **File Extension Validation**: Only allowed image extensions are processed
- **Database Path Validation**: Prevents path traversal attacks
- **Webhook URL Validation**: Ensures Discord webhook URLs are properly formatted

### 2. Rate Limiting
- **Request Rate Limiting**: Maximum 5 requests per minute to prevent API abuse
- **Automatic Delays**: Random delays between requests to avoid detection
- **Error Cooldown**: Automatic cooldown periods after consecutive errors

### 3. File Security
- **Size Limits**: Maximum file sizes enforced (3MB for images, 50MB for downloads)
- **Content Type Validation**: Only image content types are accepted
- **Safe File Operations**: All file operations are contained within the working directory
- **Automatic Cleanup**: Temporary files are automatically deleted

### 4. Database Security
- **SQL Injection Prevention**: All database queries use parameterized statements
- **Connection Timeouts**: Database connections have timeout limits
- **Automatic Cleanup**: Old records are automatically cleaned up
- **WAL Mode**: Database uses Write-Ahead Logging for better data integrity

### 5. WebDriver Security
- **Headless Mode**: Browser runs in headless mode to prevent UI access
- **Security Flags**: Multiple Chrome security flags enabled
- **Anti-Detection**: WebDriver properties are hidden to avoid detection
- **Resource Limits**: Memory and CPU usage are limited

### 6. Logging & Monitoring
- **Structured Logging**: All operations are logged with appropriate levels
- **Error Tracking**: Comprehensive error handling and logging
- **Log Rotation**: Log files are automatically rotated to prevent disk space issues
- **No Sensitive Data**: No sensitive information is logged

## ⚠️ Potential Security Risks

### 1. Webhook URLs
- **Risk**: Discord webhook URLs can be used to send messages to your channels
- **Mitigation**: 
  - Keep webhook URLs private and secure
  - Use environment variables for sensitive configuration
  - Regularly rotate webhook URLs
  - Monitor webhook usage

### 2. Image Downloads
- **Risk**: Malicious images could contain embedded scripts or exploits
- **Mitigation**:
  - Only download from trusted domains
  - Validate file content types
  - Process images through PIL to strip metadata
  - Limit file sizes

### 3. Network Requests
- **Risk**: Network requests could be intercepted or redirected
- **Mitigation**:
  - Use HTTPS only
  - Validate SSL certificates
  - Implement request timeouts
  - Use rate limiting

### 4. File System Access
- **Risk**: Unauthorized file system access
- **Mitigation**:
  - Restrict all operations to working directory
  - Validate all file paths
  - Use safe file operations
  - Implement proper file permissions

## 🔧 Security Configuration

### Environment Variables
```bash
# Use environment variables for sensitive data
export DISCORD_WEBHOOK_URL="your_webhook_url"
export WEIBO_API_KEY="your_api_key"  # If applicable
```

### Configuration File Security
- Keep `config.toml` secure and restrict access
- Use `security_config.toml` for security settings
- Regularly review and update security settings

### File Permissions
```bash
# Set appropriate file permissions
chmod 600 config.toml
chmod 600 security_config.toml
chmod 644 *.py
```

## 🚨 Incident Response

### If Webhook is Compromised
1. Immediately delete the compromised webhook
2. Create a new webhook with different URL
3. Update configuration files
4. Review logs for unauthorized activity
5. Consider implementing webhook authentication

### If Malicious Files are Detected
1. Stop the bot immediately
2. Scan downloaded files for malware
3. Clean up any suspicious files
4. Review and update domain whitelist
5. Implement additional file validation

### If Rate Limiting is Triggered
1. Check logs for unusual activity
2. Review rate limiting settings
3. Implement additional anti-detection measures
4. Consider using proxy rotation if necessary

## 📋 Security Checklist

### Before Deployment
- [ ] Review and update security configuration
- [ ] Set appropriate file permissions
- [ ] Configure logging and monitoring
- [ ] Test rate limiting and error handling
- [ ] Validate all webhook URLs
- [ ] Review domain whitelist

### Regular Maintenance
- [ ] Update dependencies regularly
- [ ] Review security logs
- [ ] Rotate webhook URLs periodically
- [ ] Clean up old database records
- [ ] Monitor disk space usage
- [ ] Review error patterns

### Monitoring
- [ ] Set up log monitoring
- [ ] Monitor webhook usage
- [ ] Track error rates
- [ ] Monitor file system usage
- [ ] Watch for unusual network activity

## 🔍 Security Testing

### Manual Testing
```bash
# Test URL validation
python -c "from app import ImageManager; print(ImageManager._validate_url('https://malicious.com/image.jpg'))"

# Test file size limits
python -c "from app import WeiboScraper; scraper = WeiboScraper(); print(scraper.compress_image('large_image.jpg', 1.0))"

# Test rate limiting
python -c "from app import RateLimiter; rl = RateLimiter(1, 60); print([rl.can_proceed() for _ in range(5)])"
```

### Automated Testing
- Run the test suite regularly
- Test error conditions and edge cases
- Validate security configurations
- Test file cleanup procedures

## 📞 Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** create a public issue
2. **Do not** discuss the vulnerability publicly
3. Contact the maintainer privately
4. Provide detailed information about the vulnerability
5. Allow time for the issue to be addressed

## 📚 Additional Resources

- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Discord Webhook Security](https://discord.com/developers/docs/resources/webhook)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- [Selenium Security Considerations](https://selenium-python.readthedocs.io/installation.html#security-considerations)

---

**Remember**: Security is an ongoing process. Regularly review and update security measures to protect against new threats. 