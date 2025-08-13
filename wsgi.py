#!/usr/bin/env python3
"""
WSGI configuration for TeleShop Bot on PythonAnywhere
This file is used if you want to run a web interface alongside the bot.
"""

import sys
import os

# Add your project directory to Python path
project_home = '/home/yourusername/teleshop'  # Update this path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

# This is just a placeholder - modify according to your needs
def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b"TeleShop Bot is running as a background task."]
