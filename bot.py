import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import os
import datetime
import logging
from flask import Flask, request

# Flask app for hosting
app = Flask(__name__)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot Token (gp.soulixer environment variable से लें)
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8304954508:AAHLxY3YfPHwF1dnBxv8noLUhmz9YxV5MxU")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Bot Settings
BOT_STATUS = True  # Always online

# Unlimited Users
UNLIMITED_USERS = [
    "1382801385", 
    "5145179256",
    "8270660057",
    "7176223037"
]

# Admin Users
ADMIN_USERS = ["8270660057"]

# Channels
CHANNELS = [
    {"id": -1002851939876, "url": "https://t.me/+eB_J_ExnQT0wZDU9", "name": "Main Channel"},
    {"id": -1002321550721, "url": "https://t.me/taskblixosint", "name": "Updates Channel"},
    {"id": -1002921007541, "url": "https://t.me/CHOMUDONKIMAKICHUT", "name": "News Channel"}
]

# Database setup
def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False, timeout=10)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def execute_db(query, params=(), fetch_all=False):
    """Thread-safe database execution"""
    try:
        connection = get_db_connection()
        if connection is None:
            return None
            
        with connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                if fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.fetchone()
            else:
                result = None
            connection.close()
            return result
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None

# Create users table with click tracking
execute_db('''CREATE TABLE IF NOT EXISTS users 
             (user_id TEXT PRIMARY KEY, 
              credits INTEGER DEFAULT 3,
              daily_credits_claimed INTEGER DEFAULT 0,
              last_claim_date TEXT,
              referrals INTEGER DEFAULT 0,
              total_referrals INTEGER DEFAULT 0,
              vip_level INTEGER DEFAULT 0,
              total_earned_credits INTEGER DEFAULT 0,
              last_active_date TEXT,
              referral_bonus_claimed INTEGER DEFAULT 0,
              unlimited_until TEXT,
              daily_click_date TEXT,
              daily_click_count INTEGER DEFAULT 0)''')

# Helper Functions
def get_credits(user_id):
    if str(user_id) in UNLIMITED_USERS:
        return "♾️ Unlimited"
    
    result = execute_db("SELECT unlimited_until FROM users WHERE user_id=?", (str(user_id),))
    if result and result[0]:
        try:
            unlimited_until = datetime.datetime.strptime(result[0], "%Y-%m-%d")
            if datetime.datetime.now() < unlimited_until:
                return "♾️ Unlimited (Referral Reward)"
        except:
            pass
    
    result = execute_db("SELECT credits FROM users WHERE user_id=?", (str(user_id),))
    return result[0] if result else 0

def get_referrals_count(user_id):
    result = execute_db("SELECT referrals FROM users WHERE user_id=?", (str(user_id),))
    return int(result[0]) if result and result[0] is not None else 0

def get_total_referrals(user_id):
    result = execute_db("SELECT total_referrals FROM users WHERE user_id=?", (str(user_id),))
    return int(result[0]) if result and result[0] is not None else 0

def use_credit(user_id):
    user_id_str = str(user_id)
    
    if user_id_str in UNLIMITED_USERS:
        return True
    
    result = execute_db("SELECT unlimited_until FROM users WHERE user_id=?", (user_id_str,))
    if result and result[0]:
        try:
            unlimited_until = datetime.datetime.strptime(result[0], "%Y-%m-%d")
            if datetime.datetime.now() < unlimited_until:
                return True
        except:
            pass
    
    result = execute_db("SELECT credits FROM users WHERE user_id=?", (user_id_str,))
    if result and result[0] and int(result[0]) > 0:
        execute_db("UPDATE users SET credits=credits-1 WHERE user_id=?", (user_id_str,))
        return True
    return False

def add_user(user_id):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    execute_db("INSERT OR IGNORE INTO users (user_id, last_claim_date, last_active_date, credits, referrals, total_referrals, vip_level, total_earned_credits, referral_bonus_claimed, daily_click_date, daily_click_count) VALUES (?, ?, ?, 3, 0, 0, 0, 0, 0, ?, 0)", 
              (str(user_id), today, today, today))

def add_referral(referrer_id, new_user_id):
    if referrer_id and referrer_id != new_user_id:
        execute_db("UPDATE users SET referrals=referrals+1, total_referrals=total_referrals+1, credits=credits+1 WHERE user_id=?", 
                  (str(referrer_id),))
        execute_db("UPDATE users SET credits = credits + 1 WHERE user_id = ?", (str(new_user_id),))
        return True
    return False

def earn_credits(user_id, amount=1):
    execute_db("UPDATE users SET credits = credits + ?, total_earned_credits = total_earned_credits + ? WHERE user_id = ?",
              (amount, amount, str(user_id)))
    return f"🎉 {amount} credits added!"

def get_daily_credits(user_id):
    result = execute_db("SELECT unlimited_until FROM users WHERE user_id=?", (str(user_id),))
    if result and result[0]:
        try:
            unlimited_until = datetime.datetime.strptime(result[0], "%Y-%m-%d")
            if datetime.datetime.now() < unlimited_until:
                return "♾️ Unlimited (Referral Reward)"
        except:
            pass
    
    referrals_count = get_referrals_count(user_id)
    if referrals_count >= 200:
        return "♾️ Unlimited"
    
    result = execute_db("SELECT daily_credits_claimed FROM users WHERE user_id = ?", (str(user_id),))
    if result:
        daily_claimed = int(result[0]) if result[0] is not None else 0
        return f"{3 - daily_claimed}/3"
    return "0/3"

# API Functions - Working APIs
def search_phone_number(phone_number):
    """Search phone number using working APIs"""
    try:
        # Try multiple API sources
        apis = [
            f"http://apilayer.net/api/validate?access_key=demo&number={phone_number}&country_code=IN&format=1",
            f"https://phonevalidation.abstractapi.com/v1/?api_key=demo&phone={phone_number}",
            f"https://numverify.com/php_helper_scripts/phone_api.php?number={phone_number}"
        ]
        
        for api_url in apis:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return data
            except:
                continue
                
        # If all APIs fail, return simulated data
        return simulate_phone_data(phone_number)
            
    except Exception as e:
        logger.error(f"API Request Error: {e}")
        return simulate_phone_data(phone_number)

def simulate_phone_data(phone_number):
    """Simulate phone data when APIs are down"""
    carriers = ["Jio", "Airtel", "Vi", "BSNL"]
    states = ["Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Uttar Pradesh"]
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
    
    return {
        "valid": True,
        "number": phone_number,
        "carrier": random.choice(carriers),
        "country": "India",
        "region": random.choice(states),
        "city": random.choice(cities),
        "timezone": "Asia/Kolkata",
        "line_type": "mobile",
        "simulated": True
    }

def format_phone_info(api_data):
    """Format API response into readable text"""
    if not api_data:
        return "❌ No information found for this number."
    
    result = "📋 Phone Number Information:\n\n"
    
    # Basic info
    if api_data.get("number"):
        result += f"• 📞 Number: {api_data['number']}\n"
    if api_data.get("carrier"):
        result += f"• 📱 Carrier: {api_data['carrier']}\n"
    if api_data.get("country"):
        result += f"• 🌍 Country: {api_data['country']}\n"
    if api_data.get("region"):
        result += f"• 🗺️ Region: {api_data['region']}\n"
    if api_data.get("city"):
        result += f"• 🏙️ City: {api_data['city']}\n"
    if api_data.get("timezone"):
        result += f"• 🕐 Timezone: {api_data['timezone']}\n"
    if api_data.get("valid"):
        result += f"• ✅ Valid: {'Yes' if api_data['valid'] else 'No'}\n"
    
    # Additional info if available
    if api_data.get("line_type"):
        result += f"• 📞 Line Type: {api_data['line_type']}\n"
    
    if api_data.get("simulated"):
        result += "\n⚠️ Note: This is simulated data (APIs temporarily unavailable)\n"
    
    result += "\n🔍 More details available in our premium version!"
    
    return result

# Channel Functions
def is_user_joined(user_id, channel_id):
    try:
        member = bot.get_chat_member(channel_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

def check_all_channels(user_id):
    not_joined = []
    for channel in CHANNELS:
        if not is_user_joined(user_id, channel["id"]):
            not_joined.append(channel)
    return not_joined

def show_channel_join_menu(user_id):
    markup = InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(InlineKeyboardButton(f"📢 Join {channel['name']}", url=channel["url"]))
    markup.add(InlineKeyboardButton("✅ I've Joined", callback_data="verify_join"))
    
    try:
        bot.send_message(user_id, "🤖 To use this bot, please join all our channels first:", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending channel join menu: {e}")

# Main Handlers
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    
    if not BOT_STATUS:
        bot.send_message(user_id, "🤖 Bot is currently offline. Please try again later.")
        return
    
    not_joined = check_all_channels(message.from_user.id)
    if not_joined:
        show_channel_join_menu(user_id)
        return
    
    add_user(user_id)
    
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id != user_id:
            success = add_referral(referrer_id, user_id)
            bot.send_message(user_id, "🎉 You joined using a referral link! +1 extra credit added to your account!")
            
            if success:
                referrals_count = get_referrals_count(referrer_id) or 0
                total_refs = get_total_referrals(referrer_id) or 0
                bot.send_message(referrer_id, f"🎉 New referral! +1 credit added! Total: {referrals_count}/200 (All: {total_refs})")
    
    show_main_menu(user_id)

def show_main_menu(user_id):
    credits = get_credits(user_id)
    daily_credits = get_daily_credits(user_id)
    referrals_count = get_referrals_count(user_id) or 0
    
    status_message = f"👥 Referrals: {referrals_count}/200 (Need {200-referrals_count} more for unlimited)"
    if referrals_count >= 200:
        status_message = "🏆 200+ Referrals - DAILY UNLIMITED CREDITS! 🎉"
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📞 Number Info", callback_data="number"))
    markup.row(InlineKeyboardButton("💳 Balance", callback_data="balance"))
    markup.row(InlineKeyboardButton("🤝 Referral Program", callback_data="referral"))
    markup.row(InlineKeyboardButton("🎁 Daily Reward", callback_data="daily"))
    
    if str(user_id) in ADMIN_USERS:
        markup.row(InlineKeyboardButton("👑 Admin Dashboard", callback_data="admin_dashboard"))
    
    welcome_text = f"""
👋 Welcome!

💎 Available Credits: {credits}
📅 Daily Credits: {daily_credits}

{status_message}

✨ Choose an option below:
"""
    
    bot.send_message(user_id, welcome_text, reply_markup=markup)

# Callback Handlers
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    
    if call.data == "number":
        not_joined = check_all_channels(call.from_user.id)
        if not_joined:
            show_channel_join_menu(user_id)
        else:
            msg = bot.send_message(user_id, "📞 Enter phone number (10 digits only):")
            bot.register_next_step_handler(msg, process_number)
    
    elif call.data == "balance":
        credits = get_credits(user_id)
        daily_credits = get_daily_credits(user_id)
        referrals_count = get_referrals_count(user_id) or 0
        
        stats_text = f"""
📊 **Your Account Balance:**

💎 Available Credits: {credits}
📅 Daily Credits: {daily_credits}
👥 Successful Referrals: {referrals_count}/200
"""
        if referrals_count >= 200:
            stats_text += "🎉 **UNLIMITED DAILY CREDITS ACTIVATED!** 🎉"
        
        bot.send_message(user_id, stats_text, parse_mode="Markdown")
    
    elif call.data == "daily":
        earn_credits(user_id, 3)
        bot.answer_callback_query(call.id, "🎉 3 daily credits added to your account!")
    
    elif call.data == "verify_join":
        not_joined = check_all_channels(call.from_user.id)
        if not_joined:
            bot.answer_callback_query(call.id, "Please join all channels first!")
            show_channel_join_menu(user_id)
        else:
            bot.answer_callback_query(call.id, "Thanks for joining!")
            show_main_menu(user_id)

def process_number(message):
    user_id = str(message.from_user.id)
    phone_number = message.text.strip()
    
    if not phone_number.isdigit() or len(phone_number) != 10:
        msg = bot.send_message(user_id, "❌ Invalid phone number! Please enter 10 digits only:")
        bot.register_next_step_handler(msg, process_number)
        return
    
    if not use_credit(user_id):
        bot.send_message(user_id, "❌ You don't have enough credits!")
        return
    
    # Show searching message
    search_msg = bot.send_message(user_id, f"🔍 Searching for information on: {phone_number}...")
    
    # Call the API
    api_data = search_phone_number(phone_number)
    
    # Format and send the results
    formatted_info = format_phone_info(api_data)
    bot.edit_message_text(
        chat_id=user_id,
        message_id=search_msg.message_id,
        text=formatted_info
    )

# Flask routes for gp.soulixer
@app.route('/')
def index():
    return "Telegram Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK'
    else:
        return 'Invalid content type', 400

# Start bot in polling mode for gp.soulixer
def run_bot():
    logger.info("Starting bot in polling mode...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.polling(none_stop=True, interval=1, timeout=30)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        time.sleep(5)
        run_bot()

if __name__ == "__main__":
    # Start bot in background thread
    import threading
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
