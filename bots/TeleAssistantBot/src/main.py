import telegram
from telegram import (
    Update,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters,
)

from telegram.constants import ParseMode
import config as cfg
import util

def run():
    application = (
        ApplicationBuilder()
        .token(cfg.telegram_token)
        .read_timeout(30)
        .write_timeout(30)
        .concurrent_updates(True)
        .rate_limiter(
            AIORateLimiter(overall_max_rate=10, overall_time_period=1, max_retries=5)
        )
        .build()
    )
    
    application.add_handler(MessageHandler(filters.ALL, util.middleware_function), group=0)
    application.add_handler(MessageHandler(filters.TEXT, util.message_handler), group=1)
    application.add_handler(MessageHandler(filters.ATTACHMENT, util.attachment_handler), group=1)
    
    application.run_polling(poll_interval=0.01)
    

if __name__ == "__main__":
    run()
