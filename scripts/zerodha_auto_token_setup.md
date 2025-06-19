# Zerodha Automated Token Generation Setup Guide

This guide helps you set up automated daily token generation for Zerodha Kite Connect at 7 AM IST.

## Prerequisites

1. Install required Python packages:
```bash
pip install kiteconnect pyotp requests python-dotenv schedule
```

2. Enable TOTP (Time-based OTP) on your Zerodha account:
   - Log in to Zerodha Console: https://console.zerodha.com/
   - Go to Account > Security > Two-factor authentication
   - Enable TOTP and save the secret key

## Configuration

1. Create a `.env` file in your project root with your credentials:

```env
# Zerodha API Credentials
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here

# Zerodha Login Credentials
ZERODHA_USER_ID=your_user_id_here
ZERODHA_PASSWORD=your_password_here
ZERODHA_TOTP_KEY=your_totp_secret_key_here
```

**Security Note**: Keep your `.env` file secure and never commit it to version control!

## Usage

### Manual Token Generation

Run once to generate a token immediately:
```bash
python scripts/zerodha_auto_token.py
```

### Scheduled Token Generation

Run continuously with automatic generation at 7 AM IST daily:
```bash
python scripts/zerodha_auto_token.py --schedule
```

### Check Token Validity

Check if the current token is still valid:
```bash
python scripts/zerodha_auto_token.py --check
```

## Setting up as a System Service

### On Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task:
   - Name: "Zerodha Token Generator"
   - Trigger: Daily at 7:00 AM
   - Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\scripts\zerodha_auto_token.py`
   - Start in: `C:\path\to\project`

### On Linux (systemd)

1. Create a service file `/etc/systemd/system/zerodha-token.service`:

```ini
[Unit]
Description=Zerodha Token Generator
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/project
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/scripts/zerodha_auto_token.py --schedule
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zerodha-token.service
sudo systemctl start zerodha-token.service
```

### On Linux (cron)

Add to crontab:
```bash
crontab -e
```

Add this line:
```
0 7 * * * cd /path/to/project && /usr/bin/python3 scripts/zerodha_auto_token.py
```

## Integration with Freqtrade

The generated token is automatically saved to:
- `~/.cache/ccxt-zerodha/token.json`

You can use it in Freqtrade in three ways:

1. **Direct in config.json**:
```json
{
    "exchange": {
        "name": "zerodha",
        "key": "YOUR_API_KEY",
        "secret": "YOUR_API_SECRET",
        "password": "AUTO_GENERATED_TOKEN"
    }
}
```

2. **Environment Variable**:
```bash
export FREQTRADE__EXCHANGE__PASSWORD="AUTO_GENERATED_TOKEN"
```

3. **Automatic Loading** (modify your Freqtrade startup script):
```python
import json
from pathlib import Path

# Load token from cache
token_file = Path.home() / '.cache' / 'ccxt-zerodha' / 'token.json'
if token_file.exists():
    with open(token_file) as f:
        token_data = json.load(f)
        config['exchange']['password'] = token_data['access_token']
```

## Troubleshooting

### Common Issues

1. **TOTP Code Invalid**
   - Ensure your system time is synchronized
   - Verify the TOTP secret key is correct
   - Check if TOTP is enabled on your Zerodha account

2. **Login Failed**
   - Verify username and password
   - Check if account has any restrictions
   - Ensure API access is enabled

3. **Token Generation at Wrong Time**
   - Check system timezone settings
   - The script uses IST (Asia/Kolkata) timezone

### Logs

Check the log file for detailed information:
```bash
tail -f zerodha_token_generator.log
```

## Security Best Practices

1. **Protect Your Credentials**:
   - Use environment variables or `.env` file
   - Set file permissions: `chmod 600 .env`
   - Never share or commit credentials

2. **Secure Token Storage**:
   - Token files are automatically created with restricted permissions
   - Default location: `~/.cache/ccxt-zerodha/`

3. **Monitor Access**:
   - Regularly check Zerodha Console for API access logs
   - Set up alerts for unusual activity

## Advanced Configuration

### Custom Token Validation

You can add custom token validation in your trading bot:

```python
import json
from pathlib import Path
from datetime import datetime
import pytz

def is_zerodha_token_valid():
    token_file = Path.home() / '.cache' / 'ccxt-zerodha' / 'token.json'
    if not token_file.exists():
        return False
    
    with open(token_file) as f:
        data = json.load(f)
    
    login_time = datetime.fromisoformat(data['login_time'])
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Token expires at 6 AM IST next day
    # Add your validation logic here
    return True  # Simplified
```

### Multiple Account Support

For multiple accounts, create separate configuration files:

```bash
# Account 1
ZERODHA_USER_ID=user1 python scripts/zerodha_auto_token.py

# Account 2  
ZERODHA_USER_ID=user2 python scripts/zerodha_auto_token.py
```

## Support

For issues or questions:
1. Check the log file for detailed error messages
2. Verify all prerequisites are installed
3. Ensure Zerodha API access is active
4. Review Zerodha Kite Connect documentation

Remember: The token expires daily at 6:00 AM IST and must be regenerated! 