#!/usr/bin/env python3
"""
Startup script for TeleShop Bot on PythonAnywhere
Use this script in your "Always-On Tasks" section.
"""

import os
import sys
from pathlib import Path

# Set up the project path
project_path = Path(__file__).parent
sys.path.insert(0, str(project_path))

# Change to project directory
os.chdir(project_path)

# Import and run the bot
if __name__ == "__main__":
    from bot import main
    main()
