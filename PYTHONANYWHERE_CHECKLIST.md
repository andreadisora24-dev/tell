# PythonAnywhere Deployment Checklist

## ✅ Pre-Deployment (Completed)

- [x] Bot code prepared and tested
- [x] Database initialized with fresh schema
- [x] Environment variables configured
- [x] Dependencies validated
- [x] PythonAnywhere configuration files created
- [x] Deployment backup created

## 📋 PythonAnywhere Setup Steps

### 1. Account Setup
- [ ] Sign up for PythonAnywhere account ($5/month plan recommended)
- [ ] Access your dashboard at https://www.pythonanywhere.com/

### 2. File Upload
- [ ] Upload all project files to `/home/yourusername/teleshop/`
- [ ] Ensure all directories are preserved (handlers/, utils/, logs/, uploads/)
- [ ] Verify `.env` file is uploaded with correct permissions

### 3. Environment Configuration
- [ ] Edit `.env` file with your actual values:
  - [ ] BOT_TOKEN (from @BotFather)
  - [ ] ADMIN_IDS (your Telegram user ID)
  - [ ] SECRET_KEY (already generated)
  - [ ] Other settings as needed

### 4. Dependencies Installation
```bash
pip3.10 install --user -r requirements.txt
```
- [ ] Run the above command in PythonAnywhere console
- [ ] Verify no installation errors

### 5. Always-On Task Setup
- [ ] Go to "Tasks" tab in PythonAnywhere dashboard
- [ ] Create new "Always-On Task"
- [ ] Command: `python3.10 /home/yourusername/teleshop/start_bot.py`
- [ ] Replace `yourusername` with your actual username
- [ ] Enable the task

### 6. Verification
- [ ] Check task logs for startup messages
- [ ] Test bot with `/start` command on Telegram
- [ ] Verify admin panel access with `/admin`
- [ ] Check logs directory for application logs

## 🔧 Troubleshooting

### Common Issues:
1. **Bot not responding**: Check Always-On Task logs
2. **Import errors**: Verify all files uploaded correctly
3. **Database errors**: Check file permissions
4. **Token errors**: Verify `.env` configuration

### Log Locations:
- Always-On Task logs: PythonAnywhere dashboard
- Application logs: `/home/yourusername/teleshop/logs/`
- Error logs: Check console output

## 📞 Support

If you encounter issues:
1. Check the logs first
2. Verify all checklist items completed
3. Review DEPLOYMENT_SUMMARY.md for detailed instructions

## 🎉 Success Indicators

- [ ] Bot responds to `/start` command
- [ ] Admin panel accessible via `/admin`
- [ ] No errors in Always-On Task logs
- [ ] Database operations working (user registration, etc.)

---

**Deployment Date**: 2025-08-13 21:02:49  
**Status**: Ready for PythonAnywhere deployment