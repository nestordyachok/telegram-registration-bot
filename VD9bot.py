# Import necessary libraries for the bot
import logging          # For logging messages and errors
import os              # For accessing environment variables
import sqlite3         # For database operations
from datetime import datetime    # For timestamp operations
from dotenv import load_dotenv   # For loading environment variables from .env file

# Import Telegram bot components
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, MenuButtonCommands
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# Load environment variables from .env file (like BOT_TOKEN)
load_dotenv()

# Set up logging to see what's happening in the console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format for log messages
    level=logging.INFO  # Show info level messages and above
)
logger = logging.getLogger(__name__)  # Create a logger for this file

# Get the bot token from environment variables (from .env file)
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Define conversation states - these are like steps in a process
# When user is in WAITING_FOR_NAME state, bot expects a name
# When user is in WAITING_FOR_PHONE state, bot expects a phone number
WAITING_FOR_NAME, WAITING_FOR_PHONE = range(2)

class UserDatabase:
    """This class handles all database operations for storing user information"""
    
    def __init__(self, db_path='users.db'):
        """Initialize the database when the class is created"""
        self.db_path = db_path  # Store the database file path
        self.init_db()          # Create the database tables if they don't exist
    
    def init_db(self):
        """Create the database tables if they don't exist"""
        # Connect to the SQLite database file
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()  # Create a cursor to execute SQL commands
        
        # Create the registered_users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registered_users (
                user_id INTEGER PRIMARY KEY,           -- Telegram user ID (unique)
                telegram_username TEXT,                -- Telegram username (@username)
                full_name TEXT,                        -- User's full name
                phone_number TEXT,                     -- User's phone number
                registration_date TIMESTAMP,           -- When they registered
                is_registered BOOLEAN DEFAULT FALSE    -- Whether registration is complete
            )
        ''')
        
        # Save changes to database and close connection
        conn.commit()
        conn.close()
    
    def is_user_registered(self, user_id):
        """Check if a user is already registered in the database"""
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Look for the user in the database and check if they're registered
        cursor.execute('SELECT is_registered FROM registered_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()  # Get the first result
        
        # Close database connection
        conn.close()
        
        # Return True if user exists and is registered, False otherwise
        return result and result[0]
    
    def save_user_data(self, user_id, telegram_username, full_name, phone_number):
        """Save user registration data to the database"""
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert or replace user data (if user_id already exists, update it)
        cursor.execute('''
            INSERT OR REPLACE INTO registered_users 
            (user_id, telegram_username, full_name, phone_number, registration_date, is_registered)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, telegram_username, full_name, phone_number, datetime.now(), True))
        
        # Save changes and close connection
        conn.commit()
        conn.close()
    
    def get_user_data(self, user_id):
        """Get user data from database"""
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user information from database
        cursor.execute('''
            SELECT telegram_username, full_name, phone_number, registration_date 
            FROM registered_users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()  # Get the first result
        conn.close()                # Close database connection
        return result               # Return the user data (or None if not found)

# Create an instance of the database class - this will be used throughout the bot
db = UserDatabase()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function runs when user sends /start command OR when they first open the bot"""
    # Get the user information from the message
    user = update.effective_user
    
    # Check if user is already registered
    if db.is_user_registered(user.id):
        # If already registered, get their data and show welcome back message
        user_data = db.get_user_data(user.id)
        if user_data:
            # Unpack the user data tuple
            username, full_name, phone_number, reg_date = user_data
            
            # Create keyboard with main menu options for registered users
            keyboard = [
                [InlineKeyboardButton("📱 My Profile", callback_data='profile')],
                [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
                [InlineKeyboardButton("🔄 Re-register", callback_data='start_registration')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send welcome back message with their info and menu
            await update.message.reply_text(
                f"🎉 Welcome back, {full_name}!\n\n"
                f"You're already registered with us.\n"
                f"📱 Phone: {phone_number}\n"
                f"📅 Registered: {reg_date}\n\n"
                f"What would you like to do?",
                reply_markup=reply_markup
            )
        return ConversationHandler.END  # End the conversation since they're already registered
    
    # If not registered, create an inline keyboard with "Begin" button
    keyboard = [
        [InlineKeyboardButton("🚀 Begin Registration", callback_data='start_registration')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)  # Create the keyboard markup
    
    # Send welcome message with the "Begin" button (this appears automatically when user opens bot)
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🤖 Welcome to our registration bot!\n\n"
        f"To get started, I'll need to collect:\n"
        f"• Your full name\n"
        f"• Your phone number\n\n"
        f"This will only take a minute. Ready to begin? 👇",
        reply_markup=reply_markup  # Attach the "Begin" button to the message
    )
    
    return ConversationHandler.END  # End this part of conversation

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function handles ANY message that isn't a command - shows Begin button"""
    # Get the user information
    user = update.effective_user
    
    # Check if user is already registered
    if db.is_user_registered(user.id):
        # If registered, show main menu
        keyboard = [
            [InlineKeyboardButton("📱 My Profile", callback_data='profile')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Hi {user.first_name}! You're already registered.\n"
            f"What can I help you with?",
            reply_markup=reply_markup
        )
    else:
        # If not registered, show Begin button automatically
        keyboard = [
            [InlineKeyboardButton("🚀 Begin Registration", callback_data='start_registration')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 Hi {user.first_name}!\n\n"
            f"I see you're not registered yet. Let's get you started! 🚀",
            reply_markup=reply_markup
        )

async def start_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function runs when user clicks the 'Begin Registration' button"""
    # Get the callback query (button click information)
    query = update.callback_query
    await query.answer()  # Acknowledge the button click (removes loading state)
    
    # Get user information
    user = query.from_user
    
    # Double-check if already registered (safety check)
    if db.is_user_registered(user.id):
        # Edit the message to show they're already registered
        await query.edit_message_text("You're already registered! Use /start to see your info.")
        return ConversationHandler.END
    
    # Edit the original message to ask for their name
    await query.edit_message_text(
        "📝 Perfect! Let's get you registered.\n\n"
        f"Step 1 of 2: What's your full name?\n\n"
        f"Please type your full name below:\n"
        f"(Example: John Smith)"
    )
    
    # Return the next state - waiting for name input
    return WAITING_FOR_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function runs when user sends their name (while in WAITING_FOR_NAME state)"""
    # Get the text message and remove extra spaces
    user_name = update.message.text.strip()
    
    # Validate the name (basic validation)
    if len(user_name) < 2 or len(user_name) > 100:
        # If name is too short or too long, ask again
        await update.message.reply_text(
            "❌ Please enter a valid name (2-100 characters).\n\n"
            "Please try again:"
        )
        return WAITING_FOR_NAME  # Stay in the same state, wait for name again
    
    # Store the name in context.user_data (temporary storage for this conversation)
    context.user_data['full_name'] = user_name
    
    # Create a keyboard with phone sharing button
    keyboard = [
        [KeyboardButton("📱 Share My Phone Number", request_contact=True)],  # This button requests phone number
        [KeyboardButton("❌ Cancel Registration")]  # Cancel option
    ]
    # Create keyboard markup that appears at bottom of screen
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # Ask for phone number with the special keyboard
    await update.message.reply_text(
        f"✅ Great! Thanks {user_name}!\n\n"
        f"Step 2 of 2: Now I need your phone number.\n\n"
        f"You have two options:\n"
        f"🔹 Click the blue button below to share automatically\n"
        f"🔹 Or type it manually (Example: +1234567890)\n\n"
        f"Choose whichever is easier for you! 👇",
        reply_markup=reply_markup  # Show the keyboard with phone share button
    )
    
    # Move to next state - waiting for phone number
    return WAITING_FOR_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function runs when user sends phone number (while in WAITING_FOR_PHONE state)"""
    # Get user information
    user = update.effective_user
    
    # Check if user shared contact using the button
    if update.message.contact:
        # If they used the share button, get phone from contact
        phone_number = update.message.contact.phone_number
        # Add + if it's missing
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
    else:
        # If they typed manually, get the text
        phone_number = update.message.text.strip()
        
        # Check if they want to cancel
        if phone_number.lower() in ['cancel', '❌ cancel registration']:
            # Cancel registration and remove keyboard
            await update.message.reply_text(
                "❌ Registration cancelled.\n\n"
                "No worries! You can start again anytime by sending any message.",
                reply_markup=ReplyKeyboardRemove()  # Remove the keyboard
            )
            return ConversationHandler.END
        
        # Validate phone number format
        phone_clean = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not phone_clean.replace('+', '').isdigit() or len(phone_clean) < 10:
            # If invalid format, ask again
            await update.message.reply_text(
                "❌ Please enter a valid phone number.\n\n"
                "Examples: +1234567890, +44 123 456 7890\n\n"
                "Or use the blue button to share automatically:"
            )
            return WAITING_FOR_PHONE  # Stay in same state, wait for valid phone
    
    # Get the stored name from context
    full_name = context.user_data.get('full_name', 'Unknown')
    
    # Save all user data to database
    db.save_user_data(
        user_id=user.id,                                # Telegram user ID
        telegram_username=user.username or user.first_name,  # Username or first name
        full_name=full_name,                            # Full name they provided
        phone_number=phone_number                       # Phone number they provided
    )
    
    # Create main menu buttons for after registration
    keyboard = [
        [InlineKeyboardButton("📱 View My Profile", callback_data='profile')],
        [InlineKeyboardButton("ℹ️ Help & Commands", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send registration complete message and remove keyboard
    await update.message.reply_text(
        f"🎉 Registration Complete!\n\n"
        f"✅ Name: {full_name}\n"
        f"✅ Phone: {phone_number}\n"
        f"✅ Telegram: @{user.username or user.first_name}\n\n"
        f"🎊 Welcome to our community!\n\n"
        f"You're all set! What would you like to do next?",
        reply_markup=ReplyKeyboardRemove()  # Remove the phone share keyboard
    )
    
    # Send the main menu right after
    await update.message.reply_text(
        "🏠 Main Menu:",
        reply_markup=reply_markup
    )
    
    # End the conversation - registration is complete
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function runs when user wants to cancel registration"""
    # Send cancellation message and remove any keyboards
    await update.message.reply_text(
        "❌ Registration cancelled.\n\n"
        "No problem! Send any message when you're ready to try again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user clicks buttons in the menu"""
    # Get the callback query (button click information)
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    
    # Get user information
    user = query.from_user
    
    # Check which button was clicked based on callback_data
    if query.data == 'profile':
        # Show user profile
        user_data = db.get_user_data(user.id)  # Get user data from database
        if user_data:
            # Unpack user data and create profile message
            username, full_name, phone_number, reg_date = user_data
            
            # Create back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            profile_text = (
                f"👤 Your Profile\n\n"
                f"📛 Name: {full_name}\n"
                f"📱 Phone: {phone_number}\n"
                f"🆔 Telegram: @{username}\n"
                f"📅 Registered: {reg_date}\n\n"
                f"Everything looks good! ✅"
            )
        else:
            # If no data found, show error
            profile_text = "❌ Profile not found. Please register again."
            keyboard = [[InlineKeyboardButton("🚀 Register Again", callback_data='start_registration')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit the message to show profile
        await query.edit_message_text(profile_text, reply_markup=reply_markup)
    
    elif query.data == 'help':
        # Show help information
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        help_text = (
            "ℹ️ Help & Information\n\n"
            "🤖 This bot helps you register with our service.\n\n"
            "📋 What we collect:\n"
            "• Your full name\n"
            "• Your phone number\n\n"
            "🔒 Your information is stored securely and only used for registration purposes.\n\n"
            "❓ Need help? Just send any message and I'll show you the options!"
        )
        await query.edit_message_text(help_text, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        # Go back to main menu
        keyboard = [
            [InlineKeyboardButton("📱 My Profile", callback_data='profile')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏠 Main Menu\n\nWhat would you like to do?",
            reply_markup=reply_markup
        )

async def setup_bot_commands(application):
    """Set up bot commands and menu button"""
    # Define the commands that will appear in the menu
    commands = [
        BotCommand("start", "🏠 Main menu and registration"),
        BotCommand("profile", "👤 View your profile"),  
        BotCommand("help", "ℹ️ Get help and information"),
    ]
    
    # Set the commands for the bot
    await application.bot.set_my_commands(commands)
    
    # Set the menu button to show commands
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    
    logger.info("✅ Bot commands and menu button set up successfully!")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile when they send /profile command"""
    # Get user information
    user = update.effective_user
    
    # Check if user is registered
    if not db.is_user_registered(user.id):
        # If not registered, show Begin button
        keyboard = [[InlineKeyboardButton("🚀 Begin Registration", callback_data='start_registration')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ You need to register first.\n\n"
            "Ready to get started?",
            reply_markup=reply_markup
        )
        return
    
    # Get user data from database
    user_data = db.get_user_data(user.id)
    if user_data:
        # Create profile message with user data
        username, full_name, phone_number, reg_date = user_data
        
        # Create menu buttons
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        profile_text = (
            f"👤 Your Profile\n\n"
            f"📛 Name: {full_name}\n"
            f"📱 Phone: {phone_number}\n"
            f"🆔 Telegram: @{username}\n"
            f"📅 Registered: {reg_date}\n\n"
            f"Everything looks great! ✅"
        )
    else:
        # If no data found, show error
        profile_text = "❌ Profile not found. Please register again."
        keyboard = [[InlineKeyboardButton("🚀 Begin Registration", callback_data='start_registration')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send profile message
    await update.message.reply_text(profile_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message when user sends /help command"""
    # Create help text with all available information
    keyboard = [
        [InlineKeyboardButton("🚀 Begin Registration", callback_data='start_registration')],
        [InlineKeyboardButton("📱 My Profile", callback_data='profile')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = (
        "ℹ️ Welcome to the Registration Bot!\n\n"
        "🤖 I help you register quickly and easily.\n\n"
        "📋 Registration Process:\n"
        "1️⃣ Click 'Begin Registration'\n"
        "2️⃣ Enter your full name\n"
        "3️⃣ Share your phone number\n"
        "4️⃣ You're done! 🎉\n\n"
        "🔒 Your information is kept secure and private.\n\n"
        "💡 Tip: Just send me any message and I'll show you what to do!"
    )
    
    # Send help message
    await update.message.reply_text(help_text, reply_markup=reply_markup)

def main():
    """Main function - this starts the bot"""
    # Check if bot token exists
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Create the bot application with the token
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Set up bot commands and menu (this runs when bot starts)
    application.job_queue.run_once(
        lambda context: setup_bot_commands(application), 
        when=1  # Run 1 second after bot starts
    )
    
    # Create conversation handler for registration process
    registration_handler = ConversationHandler(
        # Entry point - how the conversation starts
        entry_points=[CallbackQueryHandler(start_registration_callback, pattern='start_registration')],
        
        # States - what happens in each step of the conversation
        states={
            # When waiting for name, handle text messages with get_name function
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            # When waiting for phone, handle both contact sharing and text messages
            WAITING_FOR_PHONE: [
                MessageHandler(filters.CONTACT, get_phone),                    # Handle contact sharing
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)    # Handle manual text input
            ],
        },
        # Fallback - how to exit the conversation
        fallbacks=[CommandHandler('cancel', cancel_registration)],
    )
    
    # Add all command handlers to the application
    application.add_handler(CommandHandler("start", start))                      # Handle /start command
    application.add_handler(registration_handler)                               # Handle registration conversation
    application.add_handler(CommandHandler("profile", profile_command))         # Handle /profile command
    application.add_handler(CommandHandler("help", help_command))               # Handle /help command
    application.add_handler(CallbackQueryHandler(handle_menu_callbacks))        # Handle button clicks
    
    # Handle ANY other message (when user sends random text)
    # This will show the Begin button automatically
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,  # Any text that's not a command
        handle_any_message               # Show Begin button
    ))
    
    # Log that the bot is starting
    logger.info("🚀 Starting Telegram registration bot...")
    logger.info("✨ Users will see 'Begin' button automatically when they open the chat!")
    
    # Start the bot - this keeps it running and listening for messages
    application.run_polling(drop_pending_updates=True)

# This runs only if this file is executed directly (not imported)
if __name__ == '__main__':
    main()  # Start the bot