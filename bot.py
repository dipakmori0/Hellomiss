import os
import sqlite3
import requests
import re
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

# ==== Enable Logging ====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==== CONFIG ====
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8319030007:AAH25q874QqP5F4eX0AalQqsQc9QhMwwfoY")
API_KEY = os.environ.get('API_KEY', "7658050410:3GTVV630")
ADMIN_ID = int(os.environ.get('ADMIN_ID', "8006485674"))

CHANNEL_LINK1 = "https://t.me/+pZ17mKu0yZYwYmVl"
CHANNEL_LINK2 = "https://t.me/taskblixosint"
INSTAGRAM_LINK = "https://www.instagram.com/dark.dex.001"
API_URL = "https://leakosintapi.com/"

# Admins who can give credits
ADMINS = [ADMIN_ID]

# ==== DB Setup ====
def init_db():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    credits INTEGER DEFAULT 5,
                    blocked INTEGER DEFAULT 0
                )""")
    conn.commit()
    return conn, c

conn, c = init_db()

# ==== Helper Functions ====
async def safe_send(update: Update, text: str, reply_markup=None):
    try:
        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Send error: {e}")

async def safe_edit_message(query, text: str, reply_markup=None):
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except BadRequest:
        pass
    except Exception as e:
        logger.error(f"Edit error: {e}")

def add_user(user_id: int, username: str):
    try:
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        if not user:
            c.execute("INSERT INTO users (user_id, username, credits, blocked) VALUES (?, ?, ?, ?)",
                      (user_id, username, 5, 0))
            conn.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Add user error: {e}")
        return False

def is_user_blocked(user_id: int):
    try:
        c.execute("SELECT blocked FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        return result and result[0] == 1
    except Exception as e:
        logger.error(f"Block check error: {e}")
        return False

def extract_phone_numbers(text):
    """Extract all phone numbers from text"""
    try:
        patterns = [
            r'\b\d{10}\b',
            r'\b\d{12}\b',
            r'\b91\d{10}\b',
            r'\b\d{10}xx\b',
            r'\b\d{9}x\b',
            r'\b\d{8}xx\b',
        ]
        
        all_numbers = []
        for pattern in patterns:
            numbers = re.findall(pattern, text)
            all_numbers.extend(numbers)
        
        clean_numbers = []
        for num in all_numbers:
            clean_num = re.sub(r'\D', '', num)
            if clean_num.startswith('91') and len(clean_num) == 12:
                clean_num = clean_num[2:]
            if len(clean_num) == 10:
                clean_numbers.append(clean_num)
        
        return list(set(clean_numbers))
    except Exception as e:
        logger.error(f"Extract numbers error: {e}")
        return []

def search_api(query):
    """Search API and return results"""
    try:
        payload = {"token": API_KEY, "request": query, "limit": 100, "lang": "en"}
        response = requests.post(API_URL, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"error": str(e)}

def format_result(data, query):
    """Format API result into readable text"""
    try:
        result_text = f"📞 *Phone:* `{query}`\n\n"
        
        if "List" in data and data["List"]:
            for source, source_data in data["List"].items():
                result_text += f"📂 *Source:* {source}\n"
                for entry in source_data.get("Data", []):
                    if entry.get("FullName"):
                        result_text += f"👤 *Name:* {entry['FullName']}\n"
                    if entry.get("FatherName"):
                        result_text += f"👨‍👦 *Father:* {entry['FatherName']}\n"
                    if entry.get("MotherName"):
                        result_text += f"👩‍👦 *Mother:* {entry['MotherName']}\n"
                    if entry.get("DocNumber"):
                        result_text += f"🆔 *DocNumber:* {entry['DocNumber']}\n"
                    if entry.get("Email"):
                        result_text += f"📧 *Email:* {entry['Email']}\n"
                    if entry.get("DOB"):
                        result_text += f"🎂 *DOB:* {entry['DOB']}\n"
                    
                    for i in range(1, 4):
                        key = f"Address{i}" if i > 1 else "Address"
                        if entry.get(key):
                            result_text += f"🏠 *{key}:* {entry[key]}\n"
                    
                    phone_count = 0
                    for i in range(1, 10):
                        key = f"Phone{i}" if i > 1 else "Phone"
                        if entry.get(key):
                            phone_count += 1
                            result_text += f"📞 *{key}:* {entry[key]}\n"
                    
                    if phone_count > 0:
                        result_text += f"📊 *Total Phones Found:* {phone_count}\n"
                    
                    result_text += "─" * 30 + "\n"
        else:
            result_text += "❌ *No information found for this number*\n\n"
        
        return result_text
    except Exception as e:
        logger.error(f"Format result error: {e}")
        return f"❌ *Error formatting result:* {e}"

# ==== VIP STYLE MENUS ====
def vip_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 VIP SEARCH", callback_data="search"), InlineKeyboardButton("💎 BUY CREDITS", callback_data="buy_credit")],
        [InlineKeyboardButton("💰 BALANCE", callback_data="check_balance"), InlineKeyboardButton("👑 CONTRACT RAJPUT", callback_data="contract_rajput")],
        [InlineKeyboardButton("⭐ ADMIN PANEL", callback_data="admin_panel")]
    ])

def vip_admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 ADD CREDIT", callback_data="admin_add_credit"), InlineKeyboardButton("🚫 BLOCK USER", callback_data="admin_block_user")],
        [InlineKeyboardButton("✅ UNBLOCK USER", callback_data="admin_unblock_user"), InlineKeyboardButton("🔙 BACK", callback_data="mainmenu")]
    ])

def vip_buy_credit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 2 DAYS - 30 CR", callback_data="buy_2day")],
        [InlineKeyboardButton("💎 7 DAYS - 120 CR", callback_data="buy_7day")],
        [InlineKeyboardButton("💎 1 MONTH - 730 CR", callback_data="buy_1month")],
        [InlineKeyboardButton("💎 LIFETIME - 4930 CR", callback_data="buy_lifetime")],
        [InlineKeyboardButton("🔙 BACK", callback_data="mainmenu")]
    ])

def vip_channel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 JOIN CHANNEL 1", url=CHANNEL_LINK1)],
        [InlineKeyboardButton("📢 JOIN CHANNEL 2", url=CHANNEL_LINK2)],
        [InlineKeyboardButton("📷 FOLLOW INSTAGRAM", url=INSTAGRAM_LINK)],
        [InlineKeyboardButton("✅ I HAVE JOINED", callback_data="joined")]
    ])

# ==== START ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
            
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        if is_user_blocked(user_id):
            await safe_send(update, "❌ You are blocked from using this bot.")
            return
        
        add_user(user_id, username)

        await update.message.reply_text(
            "🔐 *CHANNEL JOINING REQUIRED* 🔐\n\n"
            "📢 *Please join our channels first:*\n\n"
            "• Join both channels\n"
            "• Follow Instagram \n"
            "• Then click I HAVE JOINED\n\n"
            "*Note:* Joining is mandatory to use the bot.",
            parse_mode="Markdown",
            reply_markup=vip_channel_keyboard()
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

# ==== JOINED HANDLER ====
async def joined_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        await safe_edit_message(query,
            "✅ *SUCCESSFULLY JOINED!* ✅\n\n"
            "🎯 *WELCOME TO VIP OSINT BOT* 🎯\n\n"
            "You received *5 FREE CREDITS* 💎\n\n"
            "Now you can start searching!",
            reply_markup=vip_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Joined handler error: {e}")

# ==== MENU BUTTON HANDLER ====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if is_user_blocked(user_id):
            await safe_edit_message(query, "❌ You are blocked from using this bot.")
            return

        if query.data == "contract_rajput":
            await safe_edit_message(query,
                "👑 *CONTRACT RAJPUT*\n\n"
                "🌟 *Bot Owner:* [@RAJPUTTEAM302](https://t.me/RAJPUTTEAM302)\n"
                "🆔 *User ID:* `8006485674`",
                reply_markup=vip_main_menu_keyboard()
            )

        elif query.data == "check_balance":
            try:
                c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
                result = c.fetchone()
                if result:
                    credits = result[0]
                    await safe_edit_message(query,
                        f"💰 *VIP BALANCE* 💰\n\n*Current Credits:* {credits} 💎",
                        reply_markup=vip_main_menu_keyboard()
                    )
                else:
                    await safe_edit_message(query, "⚠️ Please use /start first.")
            except Exception as e:
                await safe_edit_message(query, "❌ Database error. Please try again.")

        elif query.data == "joined":
            await joined_handler(update, context)

        elif query.data == "search":
            await safe_edit_message(query,
                "🔍 *VIP SEARCH GUIDE*\n\n"
                "Simply send any *10-digit number* to search 🔍\n\n"
                "💎 Each search costs 1 credit\n\n"
                "⚠ *For educational purposes only*",
                reply_markup=vip_main_menu_keyboard()
            )

        elif query.data == "mainmenu":
            await safe_edit_message(query, "🎯 *VIP OSINT BOT* 🎯\n\nChoose an option:", reply_markup=vip_main_menu_keyboard())

    except Exception as e:
        logger.error(f"Button handler error: {e}")

# ==== MESSAGE HANDLER FOR NUMBERS ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
            
        user_id = update.effective_user.id
        
        if is_user_blocked(user_id):
            await safe_send(update, "❌ You are blocked from using this bot.")
            return

        message_text = update.message.text.strip()
        clean_text = ''.join(filter(str.isdigit, message_text))
        
        if len(clean_text) == 10 and clean_text.isdigit():
            await process_search(update, context, clean_text)
    except Exception as e:
        logger.error(f"Message handler error: {e}")

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE, number: str):
    try:
        user_id = update.effective_user.id
        
        c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        if not result:
            await safe_send(update, "⚠️ Please use /start first.")
            return

        credits = result[0]
        if credits < 1:
            await safe_send(update, "❌ No credits left! Buy more credits from the menu.")
            return

        query = "+91" + number
        processing_msg = await update.message.reply_text("🔄 *Processing your search...*", parse_mode="Markdown")

        c.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
        conn.commit()

        main_data = search_api(query)
        main_result = format_result(main_data, query)
        
        final_result = f"🎯 *SEARCH RESULT*\n\n{main_result}"
        
        c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        new_credits = c.fetchone()[0]
        final_result += f"\n💎 *Remaining Credits:* {new_credits}\n\n⚠ *For educational purposes only*"

        await processing_msg.delete()
        await safe_send(update, final_result, vip_main_menu_keyboard())

    except Exception as e:
        logger.error(f"Process search error: {e}")
        try:
            c.execute("UPDATE users SET credits = credits + 1 WHERE user_id=?", (user_id,))
            conn.commit()
            await update.message.reply_text(f"⚠️ *Error:* {e}\n\n💎 *Credit refunded*", parse_mode="Markdown")
        except:
            pass

# ==== ERROR HANDLER ====
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")

# ==== MAIN ====
def main():
    try:
        logger.info("🎯 Starting VIP Bot on Render...")
        
        # Check if BOT_TOKEN is available
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not found in environment variables!")
            return
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        logger.info("✅ Bot setup completed. Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
