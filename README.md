# TeleShop Bot - Refactored Architecture

A comprehensive Telegram e-commerce bot built with Python, featuring a clean, modular architecture with proper separation of concerns.

## 🏗️ Project Structure

```
TELESHOP/
├── core/                    # Core application components
│   ├── __init__.py
│   ├── exceptions.py        # Custom exception classes
│   └── middleware.py        # Bot middleware and decorators
├── handlers/                # Telegram bot handlers
│   ├── __init__.py
│   ├── admin_handlers.py    # Administrative operations
│   ├── order_handlers.py    # Order management
│   ├── shop_handlers.py     # Shopping functionality
│   └── user_handlers.py     # User management
├── repositories/            # Data access layer
│   ├── __init__.py
│   ├── base_repository.py   # Base repository with connection pooling
│   ├── inventory_repository.py
│   ├── location_repository.py
│   ├── order_repository.py
│   ├── promo_repository.py
│   └── user_repository.py
├── services/                # Business logic layer
│   ├── __init__.py
│   ├── admin_service.py     # Administrative operations
│   ├── order_service.py     # Order processing
│   ├── shop_service.py      # Shopping operations
│   └── user_service.py      # User management
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── helpers.py           # General helper functions
│   └── validators.py        # Input validation utilities
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── test_user_service.py
│   └── test_validators.py
├── bot.py                   # Main bot application
├── config.py                # Configuration management
├── database.py              # Database initialization
├── translations.py          # Multi-language support
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

## 🚀 Features

### User Management
- User registration with CAPTCHA verification
- Multi-language support (English, Spanish, French, etc.)
- User profiles and wallet management
- Balance tracking and transaction history

### Shopping System
- Product catalog with categories
- Location-based product filtering
- Shopping cart functionality
- Product search and recommendations
- Popular products display

### Order Management
- Complete checkout process
- Delivery information collection
- Promotional code support
- Order tracking and history
- Order cancellation system

### Administrative Panel
- User management (ban/unban, balance updates)
- Inventory management (add/update/delete products)
- Order processing and status updates
- Promotional code management
- System statistics and reporting
- Database maintenance tools

### Security & Performance
- Input validation and sanitization
- Rate limiting and spam protection
- Database connection pooling
- Error handling and logging
- Session management

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Admin Telegram User ID

### Installation

1. **Clone or download the project**
   ```bash
   cd TELESHOP
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python test_bot.py
   ```

4. **Configure the bot**
   
   1. Copy the example environment file:
      ```bash
      copy .env.example .env
      ```
   2. Edit `.env` and fill in your values:
      ```env
      BOT_TOKEN=your_bot_token_here
      ADMIN_IDS=your_user_id_here
      ADMIN_USERNAME=your_username
      PRIMARY_ADMIN_ID=your_user_id_here
      ```

5. **Add banner image (optional)**
   - Place `banner.jpg` in the project root for main menu display

6. **Run the bot**
   ```bash
   python run_bot.py
   ```

## 📋 Configuration

### Essential Settings (.env file)

```env
# Required - Get from @BotFather
BOT_TOKEN=your_bot_token_here

# Required - Your Telegram user ID (comma-separated for multiple admins)
ADMIN_IDS=your_user_id_here

# Required - Your Telegram username
ADMIN_USERNAME=your_username
PRIMARY_ADMIN_ID=your_user_id_here

# Optional - Customize as needed
MIN_ORDER_AMOUNT=10.0
MAX_ORDER_AMOUNT=1000.0
SESSION_TIMEOUT=3600
```

### Getting Your User ID
1. Message @userinfobot on Telegram
2. It will reply with your user ID
3. Add this number to `ADMIN_IDS` in .env file

### Getting Bot Token
1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Copy the token to `BOT_TOKEN` in .env file

## 🎮 Usage

### For Customers
1. **Start**: Send `/start` to begin
2. **Captcha**: Complete security verification
3. **Browse**: Select city → product → strain → location
4. **Order**: Choose quantity and complete payment
5. **Receive**: Get coordinates for pickup

### For Admins
1. **Access**: Send `/admin` command
2. **Manage**: Add products, manage inventory
3. **Monitor**: View statistics and user activity
4. **Support**: Handle customer inquiries

## 🏗️ Project Structure

```
TELESHOP/
├── bot.py              # Main bot application
├── database.py         # Database management
├── captcha.py          # Captcha system
├── translations.py     # Multi-language support
├── utils.py           # Utility functions
├── config.py          # Configuration settings
├── requirements.txt   # Python dependencies
├── README.md          # This file
├── banner.jpg         # Main menu banner (optional)
└── teleshop.db        # SQLite database (auto-created)
```

## 🗄️ Database Schema

The bot automatically creates and manages these tables:
- **users**: User accounts and preferences
- **cities**: Available delivery cities
- **product_categories**: Product organization
- **products**: Main product catalog
- **product_strains**: Product variants/strains
- **locations**: Delivery areas within cities
- **inventory**: Available items for purchase
- **orders**: Order history and tracking
- **promo_codes**: Promotional code system
- **discounts**: Discount management
- **statistics**: Analytics and reporting

## 🔧 Admin Commands

- `/start` - Access main menu
- `/admin` - Open admin panel (admin only)

### Admin Panel Features
- **➕ Add Product**: Create new products and strains
- **📦 Manage Inventory**: Add/edit inventory items
- **🎟️ Create Promo Code**: Generate promotional codes
- **💰 Create Discount**: Set up discount campaigns
- **📊 Statistics**: View detailed analytics
- **👥 User Management**: Monitor user accounts

## 🛡️ Security Features

### Captcha System
- **Image Recognition**: Simple object identification
- **Emoji Selection**: Category-based emoji challenges
- **Anti-Bot Protection**: Prevents automated access

### Data Protection
- **Input Sanitization**: Prevents injection attacks
- **Coordinate Validation**: Ensures valid GPS coordinates
- **Session Management**: Secure user sessions
- **Admin Verification**: Protected admin functions

## 🌍 Supported Locations

### Gdansk Areas
- Wrzeszcz
- Forum
- Oliwa
- Zaspa
- Morena

*More cities can be added through the admin panel*

## 💳 Payment Methods

- **🎟️ Promo Codes**: Available now
- **₿ Bitcoin**: Coming soon
- **📱 BLIK**: Coming soon
- **🔧 Admin BTC**: Admin-only feature

## 📊 Analytics

The bot tracks comprehensive statistics:
- User registration and activity
- Order volumes and revenue
- Popular products and locations
- Performance metrics
- Growth trends

## 🔄 Backup & Maintenance

- **Auto-backup**: Daily database backups
- **Log rotation**: Automatic log management
- **Error handling**: Comprehensive error recovery
- **Performance monitoring**: Built-in performance tracking

## 🆘 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check bot token in config.py
   - Verify internet connection
   - Check console for error messages

2. **Admin panel not accessible**
   - Verify your user ID in ADMIN_IDS
   - Restart the bot after config changes

3. **Database errors**
   - Check file permissions
   - Ensure sufficient disk space
   - Restart bot to recreate database

4. **Captcha not working**
   - Install Pillow: `pip install Pillow`
   - Check image generation permissions

### Getting Help

1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure config.py is properly configured
4. Check file permissions in the project directory

## 📝 Development Notes

### Adding New Languages
1. Add translation dictionary to `translations.py`
2. Update `get_supported_languages()` function
3. Test all menu items and messages

### Adding New Cities
1. Use admin panel to add cities
2. Add corresponding locations
3. Update coordinate validation bounds

### Adding New Products
1. Use admin panel for easy addition
2. Set appropriate categories and pricing
3. Add inventory items with coordinates

## ⚠️ Important Notes

- **Legal Compliance**: Ensure compliance with local laws
- **Security**: Regularly update dependencies
- **Backups**: Keep regular database backups
- **Monitoring**: Monitor bot performance and errors
- **Updates**: Keep the bot software updated

## 🔮 Future Enhancements

- Real Bitcoin payment integration
- BLIK payment system
- Advanced analytics dashboard
- Mobile app companion
- Multi-vendor support
- Advanced security features
- API integration capabilities

---

**⚡ Built for speed, security, and scalability**

*This bot is designed as a comprehensive marketplace solution with enterprise-grade features and security measures.*