import os
import pymongo
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)

# Conversation states
FORMAT = 1

# Database setup
mongo_client = pymongo.MongoClient("mongodb+srv://admin:admin@cluster0.iteow9t.mongodb.net/?retryWrites=true&w=majority")  # Replace with your MongoDB connection URI
db = mongo_client["telegram_bot_db"]
users_collection = db["users"]

# Owner ID
OWNER_ID =  5491384523 # Replace with your owner's user ID

# Channels
CHANNEL1_ID =  -1001311495203# Replace with your first channel ID
CHANNEL2_ID = -1001938184227 # Replace with your second channel ID

def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user = users_collection.find_one({"user_id": user_id})
    
    if user is None:
        # New user, prompt to join channels
        keyboard = [
            [InlineKeyboardButton("Join Channel 1", url="https://t.me/OngoingStartAnimeFF"),
             InlineKeyboardButton("Join Channel 2", url="https://t.me/StartAnimeFF")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("To use this bot, please join both channels:", reply_markup=reply_markup)
        return ConversationHandler.END
    
    if user.get('banned'):
        update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END
    
    update.message.reply_text("Send me an image to set as the custom thumbnail or send a document to rename.")
    return FORMAT

def handle_thumbnail(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user = users_collection.find_one({"user_id": user_id})
    
    if not user or user.get('banned'):
        update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END
    
    # Save the received thumbnail image
    thumbnail_file = update.message.photo[-1].get_file()
    thumbnail_file.download('thumbnails/thumbnail.jpg')
    update.message.reply_text("Thumbnail image set successfully. Now send a document to rename.")
    return FORMAT

def handle_delthumb(update: Update, context: CallbackContext) -> int:
    thumbnail_path = 'thumbnails/thumbnail.jpg'
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
        update.message.reply_text("Thumbnail image removed.")
    else:
        update.message.reply_text("No thumbnail image to remove.")
    return FORMAT

def handle_document(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user = users_collection.find_one({"user_id": user_id})
    
    if not user or user.get('banned'):
        update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END
    
    context.user_data['filename'] = update.message.document.file_name
    update.message.reply_text("Please send me the new format for the filename.")
    return FORMAT

def handle_format(update: Update, context: CallbackContext) -> int:
    new_format = update.message.text
    old_filename = context.user_data.get('filename', 'unknown')
    # Download the file
    file_id = update.message.document.file_id
    file = context.bot.get_file(file_id)
    file_path = 'downloads/' + old_filename
    file.download(file_path)
    # Rename the file
    new_filename = new_format.format(original=old_filename)
    new_file_path = 'downloads/' + new_filename
    os.rename(file_path, new_file_path)
    # Set custom thumbnail if available
    thumbnail_path = 'thumbnails/thumbnail.jpg'
    if os.path.exists(thumbnail_path):
        context.bot.send_document(update.message.chat_id,
                                  document=open(new_file_path, 'rb'),
                                  thumb=open(thumbnail_path, 'rb'))
    else:
        context.bot.send_document(update.message.chat_id, document=open(new_file_path, 'rb'))
    os.remove(new_file_path)  # Remove renamed file
    os.remove(file_path)  # Remove original file
    return ConversationHandler.END

def log_activity(update: Update, context: CallbackContext):
    # Log activity to a designated channel
    log_channel_id =-1001929866719   # Replace with your log channel ID
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    message_text = update.message.text
    context.bot.forward_message(chat_id=log_channel_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
    context.bot.send_message(log_channel_id, f"User {user_name} ({user_id}) sent: {message_text}")

def broadcast(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("You are not authorized to use this command.")
        return
    
    users = users_collection.find()
    message = " ".join(context.args)
    for user in users:
        context.bot.send_message(chat_id=user['user_id'], text=message)

##ef join_channel(update: Update, context: CallbackContext):
   # user_id = update.effective_user.id
   # channel_ids = [CHANNEL1_ID, CHANNEL2_ID]  # List of channel IDs
   # for channel_id in channel_ids:
   #     context.bot.send_message(chat_id=channel_id, text=f"User {update.effective_user.mention_html()} has joined the channel.")
    #users_collection.update_one({"user_id": user_id}, {"$set": {"banned": False}}, upsert=True)
  #  update.message.reply_text("You have joined the required channels. You can now use the bot.")

def main():
    # Initialize the Telegram bot
    updater = Updater(token='5909532788:AAG5mnQQ92F4aaRP8YdM-fLqNs5b-G_tscA', use_context=True)
    dispatcher = updater.dispatcher
    
    # Create a conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FORMAT: [MessageHandler(Filters.text & ~Filters.command, handle_format)]
        },
        fallbacks=[],
    )
    
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('delthumb', handle_delthumb))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_thumbnail))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type("image/*"), handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, log_activity))  # Log all user messages
    dispatcher.add_handler(CommandHandler('broadcast', broadcast, pass_args=True))
    dispatcher.add_handler(CommandHandler('join', join_channel))
    
    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    