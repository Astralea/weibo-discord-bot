# Weibo Scraper Redirect Loop Fixes

## Problem Description

The Weibo scraper was encountering redirect loop errors when trying to access the `genshin_impact` account:
```
Reached error page: about:neterror?e=redirectLoop&u=https%3A//weibo.com/&c=UTF-8&d=%E3%81%93%E3%81%AE%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9%E3%81%B8%E3%81%AE%E3%83%AA%E3%82%AF%E3%82%A8%E3%82%B9%E3%83%88%E3%81%AB%E3%82%B5%E3%83%BC%E3%83%90%E3%83%BC%E3%81%AE%E8%87%AA%E5%8B%95%E8%BB%A2%E9%80%81%E8%A8AD%E5%AE%9A%E3%81%8C%E3%83%AB%E3%83%BC%E3%83%97%E3%81%97%E3%81%A6%E3%81%84%E3%81%BE%E3%81%99%E3%80%82
```

This Japanese error message indicates a server-side redirect loop, which can be caused by:
- Geographic restrictions
- Rate limiting
- Session/cookie corruption
- Weibo's anti-bot measures

## Implemented Solutions

### 1. Enhanced Error Detection (`_is_error_page`)

Added a method to detect various types of error pages:
- `neterror` pages
- `about:` pages
- Redirect loop indicators
- Chinese error messages

### 2. Multi-Strategy Navigation Recovery (`_handle_navigation_error`)

Implemented a comprehensive recovery system with multiple strategies:

**Strategy 1: Clear Browser Data**
- Delete all cookies
- Clear localStorage and sessionStorage
- Reset browser state

**Strategy 2: Random Delays**
- Add random delays (5-15 seconds) to avoid rate limiting
- Simulate human behavior

**Strategy 3: User Agent Rotation**
- Change user agent on retry attempts
- Use realistic browser identifiers

**Strategy 4: Mobile URL Fallback**
- Try mobile URLs if desktop URLs fail
- Alternative entry points for problematic accounts

### 3. Geographic Restriction Handling (`_handle_geographic_restrictions`)

Special handling for accounts experiencing geographic restrictions:
- Multiple alternative URLs
- Different entry points
- Account-specific recovery strategies

### 4. Session Rotation (`_rotate_session`)

Prevent detection by rotating sessions:
- Recreate WebDriver instances
- Random viewport sizes
- Fresh browser sessions
- Clear all browser data

### 5. Human-Like Behavior (`_add_human_like_delays`)

Make the scraper appear more human:
- Random delays between actions
- Progressive backoff with jitter
- Realistic timing patterns

### 6. Enhanced WebDriver Options

**Chrome Options:**
- `--disable-web-security`
- `--allow-running-insecure-content`
- `--disable-features=VizDisplayCompositor`
- `--disable-background-timer-throttling`
- Realistic user agent

**Firefox Options:**
- Network timeout configurations
- Cache disabling
- Security feature adjustments
- Connection optimization

### 7. Improved Retry Logic

Enhanced retry mechanism with:
- Progressive backoff (exponential with jitter)
- Maximum delay cap (5 minutes)
- Driver recreation on failures
- Session rotation every few retries
- Account-specific error handling

### 8. Account Disabling System

Temporary account disabling to prevent repeated failures:
- `disabled = true` flag in config
- `disabled_reason` for documentation
- Automatic skipping of disabled accounts
- Easy re-enabling when issues are resolved

## Configuration Changes

### Temporarily Disabled Account
```toml
[weibo.genshin_impact]
    read_link_url = "https://weibo.com/u/6593199887"
    message_webhook = "..."
    avatar_url = "..."
    title = "原神怎么你了？"
    disabled = true
    disabled_reason = "Temporarily disabled due to redirect loop errors - investigating geographic restrictions"
```

## Usage

### Enable/Disable Accounts
To disable an account, add these lines to `config.toml`:
```toml
disabled = true
disabled_reason = "Your reason here"
```

To re-enable, simply remove or set `disabled = false`.

### Monitor Logs
The enhanced logging will show:
- Navigation error detection
- Recovery attempts
- Session rotation
- Account skipping for disabled accounts

## Testing

The disabled account logic has been tested and verified to work correctly:
- Disabled accounts are properly identified
- Skipping logic works as expected
- Other accounts continue to function normally

## Next Steps

1. **Monitor Performance**: Watch logs to see if the recovery strategies are effective
2. **Geographic Investigation**: Research if the `genshin_impact` account has specific access restrictions
3. **Gradual Re-enabling**: Once stable, gradually re-enable the disabled account
4. **Additional Strategies**: Consider VPN/proxy rotation if geographic restrictions persist

## Files Modified

- `services/weibo_scraper.py` - Main scraper logic improvements
- `core/webdriver_manager.py` - Enhanced WebDriver options
- `config.toml` - Account disabling configuration

## Benefits

- **Resilience**: Better handling of navigation errors
- **Detection Avoidance**: Reduced likelihood of being blocked
- **Graceful Degradation**: Disabled accounts don't affect others
- **Maintainability**: Easy to enable/disable problematic accounts
- **Monitoring**: Better visibility into what's happening during failures

