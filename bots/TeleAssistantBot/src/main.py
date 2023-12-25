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
    user_filter = filters.ALL
    if len(cfg.allowed_user_ids) > 0:
        user_filter = filters.User(user_id=cfg.allowed_user_ids)
    
    sysadmin_filter = filters.ALL
    if len(cfg.system_admin_ids) > 0:
        sysadmin_filter = filters.User(user_id=cfg.system_admin_ids)
    
    application.add_handler(MessageHandler(filters.ALL & user_filter, util.middleware_function), group=0)
    application.add_handler(MessageHandler(filters.TEXT & user_filter, util.message_handler), group=1)
    application.add_handler(MessageHandler(filters.ATTACHMENT & user_filter, util.attachment_handler), group=1)
    
    application.run_polling(poll_interval=0.01)
    

if __name__ == "__main__":
    run()
