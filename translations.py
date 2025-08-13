from typing import Dict, Any

# Translation dictionaries for supported languages
TRANSLATIONS = {
    'en': {
        # Main Menu
        'main_menu_title': '🏪 <b>TELESHOP</b> 🏪',
        'main_menu_separator': '━━━━━━━━━━━━━━━━━━━━',
        'user_info': '👤 <b>User Info:</b>',
        'user_id': '🆔 ID: {}',
        'balance': '💰 Balance: {}',
        'discount': '🎯 Discount: {}%',
        'member_since': '📅 Member since: {}',
        'choose_option': '<b>Choose an option below:</b>',
        
        # Menu Buttons
        'btn_buy': '🛒 Buy Products',
        'btn_wallet': '💳 Wallet',
        'btn_history': '📋 Order History',
        'btn_help': '❓ Help & Support',
        'btn_language': '🌐 Language',
        'btn_back_menu': '🔙 Back to Menu',
        'btn_back': '🔙 Back',
        'btn_main_menu': '🏠 Main Menu',
        
        # Cities
        'select_city': '🏙️ <b>Select City</b>\n\nChoose your city for delivery:',
        'city_gdansk': '🏙️ Gdansk',
        
        # Products
        'select_product': '🌿 <b>Select Product</b>\n\nChoose what you\'re looking for:',
        'product_weed': '🌿 Weed',
        'select_strain': '🧬 <b>Select Strain</b>\n\nChoose your preferred strain:',
        'strain_amnesia': '🌿 Amnesia Haze',
        
        # Locations
        'select_location': '📍 <b>Select Location</b>\n\nChoose your preferred area:',
        'location_wrzeszcz': '📍 Wrzeszcz',
        'location_forum': '📍 Forum',
        'location_oliwa': '📍 Oliwa',
        'location_zaspa': '📍 Zaspa',
        'location_morena': '📍 Morena',
        
        # Wallet
        'wallet_title': '💰 <b>Wallet</b>',
        'wallet_balance_label': '💵 Balance: {}',
        'wallet_discount_label': '🎯 Discount: {}',
        'wallet_select_option': 'Select an option:',
        'btn_bitcoin_unavailable': '₿ Bitcoin (Unavailable)',
        'btn_bitcoin_payment': '₿ Bitcoin Payment',
        'btn_blik_unavailable': '💳 Blik (Unavailable)',
        'btn_promo_code': '🎫 Promo Code',
        'btn_back_wallet': '🔙 Back to Wallet',
        
        # Cryptocurrency Payment
        'crypto_payment_title': '₿ <b>Cryptocurrency Payment</b>',
        'crypto_payment_description': 'Add funds to your wallet using Bitcoin. Fast, secure, and anonymous.',
        'crypto_select_option': 'Select a payment option:',
        'btn_add_custom_amount': '💰 Add Custom Amount',
        'btn_payment_history': '📋 Payment History',
        'bitcoin_payment_title': '₿ <b>Bitcoin Payment</b>',
        'select_amount_to_add': 'Select the amount you want to add to your wallet:',
        'btn_custom_amount': '✏️ Custom Amount',
        'bitcoin_payment_details': '₿ <b>Bitcoin Payment Details</b>',
        'amount_label': 'Amount:',
        'btc_amount_label': 'BTC Amount:',
        'payment_address_label': 'Payment Address:',
        'bitcoin_payment_instructions': '📱 Scan the QR code or copy the address above to send Bitcoin.\n\n⚠️ Send the exact BTC amount shown above.',
        'payment_timeout_warning': 'This payment request expires in 30 minutes.',
        'btn_payment_sent': '✅ Payment Sent',
        'btn_check_payment': '🔍 Check Payment',
        'btn_cancel_payment': '❌ Cancel Payment',
        'custom_amount_title': '💰 <b>Custom Amount</b>',
        'custom_amount_instructions': 'Enter the amount you want to add to your wallet (in PLN):',
        'min_amount_note': 'Minimum amount: {}',
        'max_amount_note': 'Maximum amount: {}',
        'amount_too_low': '❌ Amount too low. Minimum amount is {}',
        'amount_too_high': '❌ Amount too high. Maximum amount is {}',
        'invalid_amount_format': '❌ Invalid amount format. Please enter a valid number.',
        'payment_not_found': '❌ Payment not found or expired.',
        'payment_still_pending': '⏳ Payment is still pending. Please wait for confirmation.',
        'payment_confirmed_title': '✅ <b>Payment Confirmed!</b>',
        'payment_amount_added': 'Amount added: {}',
        'new_balance_label': 'New balance: {}',
        'payment_success_message': 'Your Bitcoin payment has been confirmed and your balance has been updated.',
        'payment_cancelled': '❌ Payment cancelled.',
        'payment_history_title': '📋 <b>Payment History</b>',
        'no_payment_history': 'No payment history found.',
        
        # Order History
        'order_history': '📋 <b>Order History</b>\n\nYour recent orders:',
        'no_orders': 'No orders found.',
        'order_item': '📦 Order #{} - {} - {}',
        'select_order_details': 'Select an order to view details:',
        
        # Help & Support
        'help_title': '❓ <b>Help & Support</b>\n\nHow can we help you?',
        'btn_contact_admin': '👨‍💼 Contact Admin',
        'btn_how_to_use': '📖 How to Use',
        
        # Language Selection
        'language_title': '🌐 <b>Language Selection</b>\n\nChoose your preferred language:',
        'btn_english': '🇺🇸 English',
        'btn_polish': '🇵🇱 Polski',
        'btn_russian': '🇷🇺 Русский',
        
        # Admin Panel
        'admin_panel': '🔧 <b>Admin Panel</b>\n\nSelect an option:',
        'btn_add_product': '➕ Add Product',
        'btn_manage_inventory': '📦 Manage Inventory',
        'btn_create_promo': '🎟️ Create Promo Code',
        'btn_create_discount': '💰 Create Discount',
        'btn_statistics': '📊 Statistics',
        'btn_user_management': '👥 User Management',
        
        # Messages
        'access_denied': '❌ Access denied. You are not authorized.',
        'user_not_found': '❌ User not found. Please start with /start',
        'session_expired': '❌ Session expired. Please start again with /start',
        'incorrect_answer': '❌ Incorrect answer. Please try again.',
        'loading': '🔄 Loading',
        'coming_soon': '🚧 Coming Soon',
        'error_creating_user': '❌ Error creating user account. Please try again.',
        'error_user_not_found': '❌ User account not found. Please restart with /start',
        
        # Promo Code Messages
        'promo_redeemed_title': '✅ <b>Promo Code Redeemed!</b>',
        'promo_code_label': '🎫 Code: {}',
        'promo_amount_label': '💰 Amount: {}',
        'promo_new_balance': '💵 New Balance: {}',
        'invalid_promo_title': '❌ <b>Invalid Promo Code</b>',
        'promo_error_default': 'Code not found or expired.',
        'promo_already_used': 'Promo code already used.',
        
        # General Messages
        'unknown_user': 'Unknown',
        'language_changed': '✅ Language changed to English!',
        'contact_admin_message': 'You can contact the admin here: @{}',
        
        # Purchase Messages
        'purchase_success': '✅ <b>Purchase Successful!</b>',
        'order_id_label': '📦 Order ID: {}',
        'coordinates_label': '📍 Coordinates: `{}`',
        'total_paid': '💰 Total Paid: {}',
        'insufficient_balance': '❌ Insufficient balance. Please add funds to your wallet.',
        'purchase_error': '❌ Error processing purchase. Please try again.',
        
        # Promo Code Entry
        'enter_promo_code': 'Please enter your promo code:',
        
        # Order Details
        'order_not_found': '❌ Order not found.',
        'order_details_title': '📦 <b>Order Details</b>',
        'order_date': '📅 Date: {}',
        'order_status': '📋 Status: {}',
        'order_product': '🌿 Product: {}',
        'order_location': '📍 Location: {}',
        
        # Wallet Messages
        'bitcoin_unavailable': '₿ Bitcoin payments are currently unavailable.',
        'blik_unavailable': '💳 Blik payments are currently unavailable.',
        
        # Purchase Confirmation
        'location_not_found': '❌ Location not found.',
        'purchase_confirmation_title': '🛒 <b>Purchase Confirmation</b>',
        'location_label': '📍 Location: {}',
        'price_label': '💰 Price: {}',
        'product_label': '📦 Product: {} - {}',
        'city_label': '🏙️ City: {}',
        'your_balance': '💵 Your Balance: {}',
        'after_purchase': '💸 After Purchase: {}',
        'confirm_purchase_question': 'Confirm your purchase?',
        'btn_confirm_purchase': '✅ Confirm Purchase',
        'btn_cancel': '❌ Cancel',
        
        # Order Receipt
        'order_receipt_title': '🧾 <b>Order Receipt</b>',
        'btn_download_receipt': '📄 Download Receipt',
        'thank_you_purchase': '✅ Thank you for your purchase!',
        
        # Contact Admin
        'contact_admin_title': '👨‍💼 <b>Contact Admin</b>',
        'contact_admin_text': 'To contact an administrator, please send a direct message to:\n@{}\n\nOr use this link: https://t.me/{}',
        'contact_admin_smart_text': '🕐 <b>Available Now:</b> {}\n\nClick the button below to start a conversation with @{}\n\n💡 <i>Our admins work in shifts to provide you with the best support!</i>',
        'contact_admin_button': 'Contact {}',
        
        # How to Use
        'how_to_use_title': '📖 <b>How to Use TeleShop</b>',
        'how_to_use_content': '1️⃣ <b>Browse Products</b>: Select your city and browse available products\n2️⃣ <b>Choose Strain</b>: Pick your preferred strain and location\n3️⃣ <b>Make Payment</b>: Use promo codes or contact admin for balance\n4️⃣ <b>Get Coordinates</b>: Receive pickup location after payment\n5️⃣ <b>Pickup</b>: Visit the location to collect your order\n\n💡 <b>Tips:</b>\n• Use promo codes to add balance\n• Check order history for past purchases\n• Contact admin for support\n• Change language in settings',
        
        # Admin Messages
        'unsupported_language': '❌ Unsupported language.',
        'access_denied': '❌ Access denied.',
        'add_product_title': '➕ <b>Add Product</b>',
        'feature_under_development': 'This feature is under development.',
        'btn_back_admin': '🔙 Back to Admin',
        
        # Captcha
        'security_verification': '🔐 <b>Security Verification</b>',
        'captcha_instruction': 'Please type the code shown in the image:',
        'captcha_hint': '💡 Type the code exactly as shown (letters and numbers)',
        'captcha_incorrect': '❌ Incorrect code. Please try again.',
        'captcha_success': '✅ Verification successful!',
        
        # How to Use
        'how_to_use': '''
📖 <b>How to Use TeleShop</b>

<b>Step 1:</b> Choose your city from the available locations
<b>Step 2:</b> Select the product category you're interested in
<b>Step 3:</b> Pick your preferred strain/variant
<b>Step 4:</b> Choose the delivery location in your area
<b>Step 5:</b> Complete the payment process
<b>Step 6:</b> Receive coordinates for pickup

<b>Important Notes:</b>
• All transactions are secure and anonymous
• Coordinates are provided after payment confirmation
• Check your order history for past purchases
• Contact admin for any issues

<b>Payment Methods:</b>
• Bitcoin (Coming Soon)
• BLIK (Coming Soon)
• Promo Codes (Available)
        '''
    },
    
    'pl': {
        # Main Menu
        'main_menu_title': '🏪 <b>TELESHOP</b> 🏪',
        'main_menu_separator': '━━━━━━━━━━━━━━━━━━━━',
        'user_info': '👤 <b>Informacje o użytkowniku:</b>',
        'user_id': '🆔 ID: {}',
        'balance': '💰 Saldo: {}',
        'discount': '🎯 Zniżka: {}%',
        'member_since': '📅 Członek od: {}',
        'choose_option': '<b>Wybierz opcję poniżej:</b>',
        
        # Menu Buttons
        'btn_buy': '🛒 Kup Produkty',
        'btn_wallet': '💳 Portfel',
        'btn_history': '📋 Historia Zamówień',
        'btn_help': '❓ Pomoc i Wsparcie',
        'btn_language': '🌐 Język',
        'btn_back_menu': '🔙 Powrót do Menu',
        'btn_back': '🔙 Wstecz',
        'btn_main_menu': '🏠 Menu Główne',
        
        # Cities
        'select_city': '🏙️ <b>Wybierz Miasto</b>\n\nWybierz swoje miasto do dostawy:',
        'city_gdansk': '🏙️ Gdańsk',
        
        # Products
        'select_product': '🌿 <b>Wybierz Produkt</b>\n\nWybierz to, czego szukasz:',
        'product_weed': '🌿 Marihuana',
        'select_strain': '🧬 <b>Wybierz Odmianę</b>\n\nWybierz preferowaną odmianę:',
        'strain_amnesia': '🌿 Amnesia Haze',
        
        # Locations
        'select_location': '📍 <b>Wybierz Lokalizację</b>\n\nWybierz preferowany obszar:',
        'location_wrzeszcz': '📍 Wrzeszcz',
        'location_forum': '📍 Forum',
        'location_oliwa': '📍 Oliwa',
        'location_zaspa': '📍 Zaspa',
        'location_morena': '📍 Morena',
        
        # Wallet
        'wallet_title': '💰 <b>Portfel</b>',
        'wallet_balance_label': '💵 Saldo: {}',
        'wallet_discount_label': '🎯 Zniżka: {}',
        'wallet_select_option': 'Wybierz opcję:',
        'btn_bitcoin_unavailable': '₿ Bitcoin (Niedostępne)',
        'btn_bitcoin_payment': '₿ Płatność Bitcoin',
        'btn_blik_unavailable': '💳 Blik (Niedostępne)',
        'btn_promo_code': '🎫 Kod Promocyjny',
        'btn_back_wallet': '🔙 Powrót do Portfela',
        
        # Cryptocurrency Payment
        'crypto_payment_title': '₿ <b>Płatność Kryptowalutą</b>',
        'crypto_payment_description': 'Dodaj środki do portfela używając Bitcoin. Szybko, bezpiecznie i anonimowo.',
        'crypto_select_option': 'Wybierz opcję płatności:',
        'btn_add_custom_amount': '💰 Dodaj Własną Kwotę',
        'btn_payment_history': '📋 Historia Płatności',
        'bitcoin_payment_title': '₿ <b>Płatność Bitcoin</b>',
        'select_amount_to_add': 'Wybierz kwotę, którą chcesz dodać do portfela:',
        'btn_custom_amount': '✏️ Własna Kwota',
        'bitcoin_payment_details': '₿ <b>Szczegóły Płatności Bitcoin</b>',
        'amount_label': 'Kwota:',
        'btc_amount_label': 'Kwota BTC:',
        'payment_address_label': 'Adres Płatności:',
        'bitcoin_payment_instructions': '📱 Zeskanuj kod QR lub skopiuj powyższy adres, aby wysłać Bitcoin.\n\n⚠️ Wyślij dokładną kwotę BTC pokazaną powyżej.',
        'payment_timeout_warning': 'To żądanie płatności wygasa za 30 minut.',
        'btn_payment_sent': '✅ Płatność Wysłana',
        'btn_check_payment': '🔍 Sprawdź Płatność',
        'btn_cancel_payment': '❌ Anuluj Płatność',
        'custom_amount_title': '💰 <b>Własna Kwota</b>',
        'custom_amount_instructions': 'Wprowadź kwotę, którą chcesz dodać do portfela (w PLN):',
        'min_amount_note': 'Minimalna kwota: {}',
        'max_amount_note': 'Maksymalna kwota: {}',
        'amount_too_low': '❌ Kwota za niska. Minimalna kwota to {}',
        'amount_too_high': '❌ Kwota za wysoka. Maksymalna kwota to {}',
        'invalid_amount_format': '❌ Nieprawidłowy format kwoty. Wprowadź prawidłową liczbę.',
        'payment_not_found': '❌ Płatność nie znaleziona lub wygasła.',
        'payment_still_pending': '⏳ Płatność nadal oczekuje. Proszę czekać na potwierdzenie.',
        'payment_confirmed_title': '✅ <b>Płatność Potwierdzona!</b>',
        'payment_amount_added': 'Dodana kwota: {}',
        'new_balance_label': 'Nowe saldo: {}',
        'payment_success_message': 'Twoja płatność Bitcoin została potwierdzona i saldo zostało zaktualizowane.',
        'payment_cancelled': '❌ Płatność anulowana.',
        'payment_history_title': '📋 <b>Historia Płatności</b>',
        'no_payment_history': 'Nie znaleziono historii płatności.',
        
        # Order History
        'order_history': '📋 <b>Historia Zamówień</b>\n\nTwoje ostatnie zamówienia:',
        'no_orders': 'Nie znaleziono zamówień.',
        'order_item': '📦 Zamówienie #{} - {} - {}',
        'select_order_details': 'Wybierz zamówienie, aby zobaczyć szczegóły:',
        
        # Help & Support
        'help_title': '❓ <b>Pomoc i Wsparcie</b>\n\nJak możemy Ci pomóc?',
        'btn_contact_admin': '👨‍💼 Kontakt z Adminem',
        'btn_how_to_use': '📖 Jak Używać',
        
        # Language Selection
        'language_title': '🌐 <b>Wybór Języka</b>\n\nWybierz preferowany język:',
        'btn_english': '🇺🇸 English',
        'btn_polish': '🇵🇱 Polski',
        'btn_russian': '🇷🇺 Русский',
        
        # Admin Panel
        'admin_panel': '🔧 <b>Panel Administracyjny</b>\n\nWybierz opcję:',
        'btn_add_product': '➕ Dodaj Produkt',
        'btn_manage_inventory': '📦 Zarządzaj Magazynem',
        'btn_create_promo': '🎟️ Utwórz Kod Promocyjny',
        'btn_create_discount': '💰 Utwórz Zniżkę',
        'btn_statistics': '📊 Statystyki',
        'btn_user_management': '👥 Zarządzanie Użytkownikami',
        
        # Messages
        'access_denied': '❌ Dostęp zabroniony. Nie masz autoryzacji.',
        'user_not_found': '❌ Użytkownik nie znaleziony. Zacznij od /start',
        'session_expired': '❌ Sesja wygasła. Zacznij ponownie od /start',
        'incorrect_answer': '❌ Nieprawidłowa odpowiedź. Spróbuj ponownie.',
        'loading': '🔄 Ładowanie',
        'coming_soon': '🚧 Wkrótce',
        
        # Promo Code Messages
        'promo_redeemed_title': '✅ <b>Kod Promocyjny Wykorzystany!</b>',
        'promo_code_label': '🎫 Kod: {}',
        'promo_amount_label': '💰 Kwota: {}',
        'promo_new_balance': '💵 Nowe Saldo: {}',
        'invalid_promo_title': '❌ <b>Nieprawidłowy Kod Promocyjny</b>',
        'promo_error_default': 'Kod nie znaleziony lub wygasł.',
        'promo_already_used': 'Kod promocyjny już został użyty.',
        
        # General Messages
        'unknown_user': 'Nieznany',
        'language_changed': '✅ Język zmieniony na Polski!',
        'contact_admin_message': 'Możesz skontaktować się z adminem tutaj: @{}',
        
        # Purchase Messages
        'purchase_success': '✅ <b>Zakup Udany!</b>',
        'order_id_label': '📦 ID Zamówienia: {}',
        'coordinates_label': '📍 Współrzędne: `{}`',
        'total_paid': '💰 Łącznie Zapłacono: {}',
        'insufficient_balance': '❌ Niewystarczające saldo. Proszę doładować portfel.',
        'purchase_error': '❌ Błąd podczas przetwarzania zakupu. Spróbuj ponownie.',
        
        # Promo Code Entry
        'enter_promo_code': 'Proszę wprowadzić kod promocyjny:',
        
        # Order Details
        'order_not_found': '❌ Zamówienie nie znalezione.',
        'order_details_title': '📦 <b>Szczegóły Zamówienia</b>',
        'order_date': '📅 Data: {}',
        'order_status': '📋 Status: {}',
        'order_product': '🌿 Produkt: {}',
        'order_location': '📍 Lokalizacja: {}',
        
        # Wallet Messages
        'bitcoin_unavailable': '₿ Płatności Bitcoin są obecnie niedostępne.',
        'blik_unavailable': '💳 Płatności Blik są obecnie niedostępne.',
        
        # Purchase Confirmation
        'location_not_found': '❌ Lokalizacja nie znaleziona.',
        'purchase_confirmation_title': '🛒 <b>Potwierdzenie Zakupu</b>',
        'location_label': '📍 Lokalizacja: {}',
        'price_label': '💰 Cena: {}',
        'product_label': '📦 Produkt: {} - {}',
        'city_label': '🏙️ Miasto: {}',
        'your_balance': '💵 Twoje Saldo: {}',
        'after_purchase': '💸 Po Zakupie: {}',
        'confirm_purchase_question': 'Potwierdź zakup?',
        'btn_confirm_purchase': '✅ Potwierdź Zakup',
        'btn_cancel': '❌ Anuluj',
        
        # Order Receipt
        'order_receipt_title': '🧾 <b>Paragon Zamówienia</b>',
        'btn_download_receipt': '📄 Pobierz Paragon',
        'thank_you_purchase': '✅ Dziękujemy za zakup!',
        
        # Contact Admin
        'contact_admin_title': '👨‍💼 <b>Kontakt z Adminem</b>',
        'contact_admin_text': 'Aby skontaktować się z administratorem, wyślij wiadomość prywatną do:\n@{}\n\nLub użyj tego linku: https://t.me/{}',
        'contact_admin_smart_text': '🕐 <b>Dostępny Teraz:</b> {}\n\nKliknij przycisk poniżej, aby rozpocząć rozmowę z @{}\n\n💡 <i>Nasi administratorzy pracują na zmiany, aby zapewnić Ci najlepsze wsparcie!</i>',
        'contact_admin_button': 'Kontakt z {}',
        
        # How to Use
        'how_to_use_title': '📖 <b>Jak Używać TeleShop</b>',
        'how_to_use_content': '1️⃣ <b>Przeglądaj Produkty</b>: Wybierz swoje miasto i przeglądaj dostępne produkty\n2️⃣ <b>Wybierz Odmianę</b>: Wybierz preferowaną odmianę i lokalizację\n3️⃣ <b>Dokonaj Płatności</b>: Użyj kodów promocyjnych lub skontaktuj się z adminem\n4️⃣ <b>Otrzymaj Współrzędne</b>: Otrzymaj lokalizację odbioru po płatności\n5️⃣ <b>Odbierz</b>: Odwiedź lokalizację, aby odebrać zamówienie\n\n💡 <b>Wskazówki:</b>\n• Używaj kodów promocyjnych do doładowania salda\n• Sprawdzaj historię zamówień\n• Kontaktuj się z adminem w razie potrzeby\n• Zmieniaj język w ustawieniach',
        
        # Admin Messages
        'unsupported_language': '❌ Nieobsługiwany język.',
        'access_denied': '❌ Dostęp zabroniony.',
        'add_product_title': '➕ <b>Dodaj Produkt</b>',
        'feature_under_development': 'Ta funkcja jest w trakcie rozwoju.',
        'btn_back_admin': '🔙 Powrót do Admina',
        
        # Captcha
        'security_verification': '🔐 <b>Weryfikacja Bezpieczeństwa</b>',
        'captcha_instruction': 'Proszę wpisać kod pokazany na obrazku:',
        'captcha_hint': '💡 Wpisz kod dokładnie tak, jak pokazano (litery i cyfry)',
        'captcha_incorrect': '❌ Nieprawidłowy kod. Spróbuj ponownie.',
        'captcha_success': '✅ Weryfikacja udana!',
        
        # How to Use
        'how_to_use': '''
📖 <b>Jak Używać TeleShop</b>

<b>Krok 1:</b> Wybierz swoje miasto z dostępnych lokalizacji
<b>Krok 2:</b> Wybierz kategorię produktu, która Cię interesuje
<b>Krok 3:</b> Wybierz preferowaną odmianę/wariant
<b>Krok 4:</b> Wybierz lokalizację dostawy w Twojej okolicy
<b>Krok 5:</b> Dokończ proces płatności
<b>Krok 6:</b> Otrzymaj współrzędne do odbioru

<b>Ważne Uwagi:</b>
• Wszystkie transakcje są bezpieczne i anonimowe
• Współrzędne są podawane po potwierdzeniu płatności
• Sprawdź historię zamówień dla poprzednich zakupów
• Skontaktuj się z adminem w przypadku problemów

<b>Metody Płatności:</b>
• Bitcoin (Wkrótce)
• BLIK (Wkrótce)
• Kody Promocyjne (Dostępne)
        '''
    },
    
    'ru': {
        # Main Menu
        'main_menu_title': '🏪 <b>TELESHOP</b> 🏪',
        'main_menu_separator': '━━━━━━━━━━━━━━━━━━━━',
        'user_info': '👤 <b>Информация о пользователе:</b>',
        'user_id': '🆔 ID: {}',
        'balance': '💰 Баланс: {}',
        'discount': '🎯 Скидка: {}%',
        'member_since': '📅 Участник с: {}',
        'choose_option': '<b>Выберите опцию ниже:</b>',
        
        # Menu Buttons
        'btn_buy': '🛒 Купить Товары',
        'btn_wallet': '💳 Кошелёк',
        'btn_history': '📋 История Заказов',
        'btn_help': '❓ Помощь и Поддержка',
        'btn_language': '🌐 Язык',
        'btn_back_menu': '🔙 Назад в Меню',
        'btn_back': '🔙 Назад',
        'btn_main_menu': '🏠 Главное Меню',
        
        # Cities
        'select_city': '🏙️ <b>Выберите Город</b>\n\nВыберите ваш город для доставки:',
        'city_gdansk': '🏙️ Гданьск',
        
        # Products
        'select_product': '🌿 <b>Выберите Товар</b>\n\nВыберите то, что ищете:',
        'product_weed': '🌿 Марихуана',
        'select_strain': '🧬 <b>Выберите Сорт</b>\n\nВыберите предпочитаемый сорт:',
        'strain_amnesia': '🌿 Amnesia Haze',
        
        # Locations
        'select_location': '📍 <b>Выберите Локацию</b>\n\nВыберите предпочитаемый район:',
        'location_wrzeszcz': '📍 Вжещ',
        'location_forum': '📍 Форум',
        'location_oliwa': '📍 Олива',
        'location_zaspa': '📍 Заспа',
        'location_morena': '📍 Морена',
        
        # Wallet
        'wallet_title': '💰 <b>Кошелёк</b>',
        'wallet_balance_label': '💵 Баланс: {}',
        'wallet_discount_label': '🎯 Скидка: {}',
        'wallet_select_option': 'Выберите опцию:',
        'btn_bitcoin_unavailable': '₿ Bitcoin (Недоступно)',
        'btn_bitcoin_payment': '₿ Платёж Bitcoin',
        'btn_blik_unavailable': '💳 Blik (Недоступно)',
        'btn_promo_code': '🎫 Промо Код',
        'btn_back_wallet': '🔙 Назад к Кошельку',
        
        # Cryptocurrency Payment
        'crypto_payment_title': '₿ <b>Криптовалютный Платёж</b>',
        'crypto_payment_description': 'Пополните кошелёк с помощью Bitcoin. Быстро, безопасно и анонимно.',
        'crypto_select_option': 'Выберите способ оплаты:',
        'btn_add_custom_amount': '💰 Добавить Свою Сумму',
        'btn_payment_history': '📋 История Платежей',
        'bitcoin_payment_title': '₿ <b>Платёж Bitcoin</b>',
        'select_amount_to_add': 'Выберите сумму для пополнения кошелька:',
        'btn_custom_amount': '✏️ Своя Сумма',
        'bitcoin_payment_details': '₿ <b>Детали Платежа Bitcoin</b>',
        'amount_label': 'Сумма:',
        'btc_amount_label': 'Сумма BTC:',
        'payment_address_label': 'Адрес Платежа:',
        'bitcoin_payment_instructions': '📱 Отсканируйте QR-код или скопируйте адрес выше для отправки Bitcoin.\n\n⚠️ Отправьте точную сумму BTC, указанную выше.',
        'payment_timeout_warning': 'Этот запрос платежа истекает через 30 минут.',
        'btn_payment_sent': '✅ Платёж Отправлен',
        'btn_check_payment': '🔍 Проверить Платёж',
        'btn_cancel_payment': '❌ Отменить Платёж',
        'custom_amount_title': '💰 <b>Своя Сумма</b>',
        'custom_amount_instructions': 'Введите сумму для пополнения кошелька (в PLN):',
        'min_amount_note': 'Минимальная сумма: {}',
        'max_amount_note': 'Максимальная сумма: {}',
        'amount_too_low': '❌ Сумма слишком мала. Минимальная сумма {}',
        'amount_too_high': '❌ Сумма слишком велика. Максимальная сумма {}',
        'invalid_amount_format': '❌ Неверный формат суммы. Введите правильное число.',
        'payment_not_found': '❌ Платёж не найден или истёк.',
        'payment_still_pending': '⏳ Платёж ещё обрабатывается. Пожалуйста, ждите подтверждения.',
        'payment_confirmed_title': '✅ <b>Платёж Подтверждён!</b>',
        'payment_amount_added': 'Добавленная сумма: {}',
        'new_balance_label': 'Новый баланс: {}',
        'payment_success_message': 'Ваш Bitcoin платёж подтверждён и баланс обновлён.',
        'payment_cancelled': '❌ Платёж отменён.',
        'payment_history_title': '📋 <b>История Платежей</b>',
        'no_payment_history': 'История платежей не найдена.',
        
        # Order History
        'order_history': '📋 <b>История Заказов</b>\n\nВаши последние заказы:',
        'no_orders': 'Заказы не найдены.',
        'order_item': '📦 Заказ #{} - {} - {}',
        'select_order_details': 'Выберите заказ для просмотра деталей:',
        
        # Help & Support
        'help_title': '❓ <b>Помощь и Поддержка</b>\n\nКак мы можем вам помочь?',
        'btn_contact_admin': '👨‍💼 Связаться с Админом',
        'btn_how_to_use': '📖 Как Использовать',
        
        # Language Selection
        'language_title': '🌐 <b>Выбор Языка</b>\n\nВыберите предпочитаемый язык:',
        'btn_english': '🇺🇸 English',
        'btn_polish': '🇵🇱 Polski',
        'btn_russian': '🇷🇺 Русский',
        
        # Admin Panel
        'admin_panel': '🔧 <b>Панель Администратора</b>\n\nВыберите опцию:',
        'btn_add_product': '➕ Добавить Товар',
        'btn_manage_inventory': '📦 Управление Складом',
        'btn_create_promo': '🎟️ Создать Промо Код',
        'btn_create_discount': '💰 Создать Скидку',
        'btn_statistics': '📊 Статистика',
        'btn_user_management': '👥 Управление Пользователями',
        
        # Messages
        'access_denied': '❌ Доступ запрещён. У вас нет авторизации.',
        'user_not_found': '❌ Пользователь не найден. Начните с /start',
        'session_expired': '❌ Сессия истекла. Начните заново с /start',
        'incorrect_answer': '❌ Неправильный ответ. Попробуйте снова.',
        'loading': '🔄 Загрузка',
        'coming_soon': '🚧 Скоро',
        
        # Promo Code Messages
        'promo_redeemed_title': '✅ <b>Промо Код Использован!</b>',
        'promo_code_label': '🎫 Код: {}',
        'promo_amount_label': '💰 Сумма: {}',
        'promo_new_balance': '💵 Новый Баланс: {}',
        'invalid_promo_title': '❌ <b>Неверный Промо Код</b>',
        'promo_error_default': 'Код не найден или истёк.',
        'promo_already_used': 'Промо код уже использован.',
        
        # General Messages
        'unknown_user': 'Неизвестный',
        'language_changed': '✅ Язык изменён на Русский!',
        'contact_admin_message': 'Вы можете связаться с админом здесь: @{}',
        
        # Purchase Messages
        'purchase_success': '✅ <b>Покупка Успешна!</b>',
        'order_id_label': '📦 ID Заказа: {}',
        'coordinates_label': '📍 Координаты: `{}`',
        'total_paid': '💰 Всего Оплачено: {}',
        'insufficient_balance': '❌ Недостаточно средств. Пожалуйста, пополните кошелёк.',
        'purchase_error': '❌ Ошибка при обработке покупки. Попробуйте снова.',
        
        # Promo Code Entry
        'enter_promo_code': 'Пожалуйста, введите промо код:',
        
        # Order Details
        'order_not_found': '❌ Заказ не найден.',
        'order_details_title': '📦 <b>Детали Заказа</b>',
        'order_date': '📅 Дата: {}',
        'order_status': '📋 Статус: {}',
        'order_product': '🌿 Товар: {}',
        'order_location': '📍 Локация: {}',
        
        # Wallet Messages
        'bitcoin_unavailable': '₿ Платежи Bitcoin в настоящее время недоступны.',
        'blik_unavailable': '💳 Платежи Blik в настоящее время недоступны.',
        
        # Purchase Confirmation
        'location_not_found': '❌ Локация не найдена.',
        'purchase_confirmation_title': '🛒 <b>Подтверждение Покупки</b>',
        'location_label': '📍 Локация: {}',
        'price_label': '💰 Цена: {}',
        'product_label': '📦 Товар: {} - {}',
        'city_label': '🏙️ Город: {}',
        'your_balance': '💵 Ваш Баланс: {}',
        'after_purchase': '💸 После Покупки: {}',
        'confirm_purchase_question': 'Подтвердить покупку?',
        'btn_confirm_purchase': '✅ Подтвердить Покупку',
        'btn_cancel': '❌ Отмена',
        
        # Order Receipt
        'order_receipt_title': '🧾 <b>Чек Заказа</b>',
        'btn_download_receipt': '📄 Скачать Чек',
        'thank_you_purchase': '✅ Спасибо за покупку!',
        
        # Contact Admin
        'contact_admin_title': '👨‍💼 <b>Связаться с Админом</b>',
        'contact_admin_text': 'Чтобы связаться с администратором, отправьте личное сообщение:\n@{}\n\nИли используйте эту ссылку: https://t.me/{}',
        'contact_admin_smart_text': '🕐 <b>Доступен Сейчас:</b> {}\n\nНажмите кнопку ниже, чтобы начать разговор с @{}\n\n💡 <i>Наши администраторы работают посменно, чтобы обеспечить вам лучшую поддержку!</i>',
        'contact_admin_button': 'Связаться с {}',
        
        # How to Use
        'how_to_use_title': '📖 <b>Как Использовать TeleShop</b>',
        'how_to_use_content': '1️⃣ <b>Просмотр Товаров</b>: Выберите свой город и просматривайте доступные товары\n2️⃣ <b>Выберите Сорт</b>: Выберите предпочитаемый сорт и локацию\n3️⃣ <b>Оплата</b>: Используйте промо коды или свяжитесь с админом\n4️⃣ <b>Получите Координаты</b>: Получите место получения после оплаты\n5️⃣ <b>Получение</b>: Посетите локацию для получения заказа\n\n💡 <b>Советы:</b>\n• Используйте промо коды для пополнения баланса\n• Проверяйте историю заказов\n• Обращайтесь к админу за поддержкой\n• Меняйте язык в настройках',
        
        # Admin Messages
        'unsupported_language': '❌ Неподдерживаемый язык.',
        'access_denied': '❌ Доступ запрещён.',
        'add_product_title': '➕ <b>Добавить Товар</b>',
        'feature_under_development': 'Эта функция находится в разработке.',
        'btn_back_admin': '🔙 Назад к Админу',
        
        # Captcha
        'security_verification': '🔐 <b>Проверка Безопасности</b>',
        'captcha_instruction': 'Пожалуйста, введите код, показанный на изображении:',
        'captcha_hint': '💡 Введите код точно как показано (буквы и цифры)',
        'captcha_incorrect': '❌ Неверный код. Попробуйте снова.',
        'captcha_success': '✅ Проверка успешна!',
        
        # How to Use
        'how_to_use': '''
📖 <b>Как Использовать TeleShop</b>

<b>Шаг 1:</b> Выберите ваш город из доступных локаций
<b>Шаг 2:</b> Выберите категорию товара, которая вас интересует
<b>Шаг 3:</b> Выберите предпочитаемый сорт/вариант
<b>Шаг 4:</b> Выберите место доставки в вашем районе
<b>Шаг 5:</b> Завершите процесс оплаты
<b>Шаг 6:</b> Получите координаты для получения

<b>Важные Заметки:</b>
• Все транзакции безопасны и анонимны
• Координаты предоставляются после подтверждения оплаты
• Проверьте историю заказов для прошлых покупок
• Свяжитесь с админом при любых проблемах

<b>Способы Оплаты:</b>
• Bitcoin (Скоро)
• BLIK (Скоро)
• Промо Коды (Доступно)
        '''
    }
}

def get_text(key: str, lang: str = 'en', **kwargs) -> str:
    """Get translated text for given key and language"""
    if lang not in TRANSLATIONS:
        lang = 'en'  # Fallback to English
    
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key))
    
    # Format with provided arguments if any
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    return text

def get_supported_languages() -> Dict[str, str]:
    """Get list of supported languages"""
    return {
        'en': '🇺🇸 English',
        'pl': '🇵🇱 Polski', 
        'ru': '🇷🇺 Русский'
    }

def is_supported_language(lang: str) -> bool:
    """Check if language is supported"""
    return lang in TRANSLATIONS