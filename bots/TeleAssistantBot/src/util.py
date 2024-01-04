import html
import json
import traceback
from typing import Any, Optional, final
import logging
from datetime import datetime

import telegram
from telegram import (
    Update,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)

from telegram.constants import ParseMode
from telegram.ext import CallbackContext
import config as cfg
from gpt.assistant import AssistantGPT
from gpt.openai_file import OpenAiFile
from gpt.guardrail import AssistantGuardRail

from database.user_collection import UserCollection
# from database.assistant_collection import AssistantCollection
from database.dialog_collection import DialogCollection

logging.basicConfig(
    filename="/data/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def post_processing(thread_id, messages, guardrail=AssistantGuardRail) -> list[str]:
    new_messages = []
    old_messages = DialogCollection.get(thread_id)

    n = len(messages) - len(old_messages)
    _messages = messages[:n]
    for msg in reversed(_messages):
        print(f"role: {msg.role}")

        for content in msg.content:
            new_message = dict()
            new_message["role"] = msg.role
            new_message["type"] = content.type

            if content.type == "text":
                new_message["data"] = content.text.value
            elif content.type == "image_file":
                file_id = content.image_file.file_id
                _path = f"image-{msg.role}-{file_id}.jpg"
                new_message["data"] = _path
                OpenAiFile.load_file(file_id, _path)
            else:
                raise TypeError(f"Unsupported content type: {content.type}")

            new_messages.append(new_message)
    # scan the new generated responses
    is_not_appropriate = not all(map(lambda msg: guardrail.check(msg['data']), new_messages))
    if is_not_appropriate:
        print("Assistant had been compromised")
        return None
    return new_messages


async def middleware_function(update: Update, context: CallbackContext):
    """
    Intercept and log every incoming request.
    """
    print("\n\nBegin middleware function")
    user = update.message.from_user
    chat_id = update.message.chat_id
    if not UserCollection.exists(user.id):
        default_assistant: final = cfg.assistant[cfg.default_assistant_name]
        user_thread = AssistantGPT.new_thread()
        UserCollection.create(
            {
                "telegram_id": user.id,
                "chat_id": chat_id,
                "username": user.username,
                "assistant_id": default_assistant["id"],
                "assistant_name": default_assistant["name"],
                "thread_id": user_thread.id,
            }
        )
    print("End middleware function")


async def message_handler(update: Update, context: CallbackContext):
    user = update.message.from_user
    prompt = update.message.text
    prompt = prompt.strip()
    print(f"\nUser Prompt: {prompt}\n")
    try:
        assistant = UserCollection.get_attribute(user.id, "current_assistant")
        thread_id, is_new_thread = __get_active_thread(user.id)

        if is_new_thread:
            print("\nNew Thread")
            # get current file ids from MongoDB
            file_ids = UserCollection.get_attribute(user.id, "current_file_ids")
            __release_old_files(file_ids)
        # Pre-Processing
        
        print("Instruct")
        status, messages = await AssistantGPT.instruct(assistant["id"], thread_id, prompt, [])
        if status['msg'] != 'completed':
            return await update.message.reply_text(f"Failed   : {status['msg']}")
            await start_new_session(update, context)
            
        print("Post Processing")
        output_messages = post_processing(thread_id, messages, AssistantGuardRail)
        for msg in output_messages:
            DialogCollection.add(thread_id, msg)
            if msg["role"] == "user":
                continue

            if msg["type"] == "text":
                await update.message.reply_text(msg["data"])
            elif msg["type"] == "image_file":
                await update.message.reply_photo(
                    open(msg["data"], "rb"), caption="system generated"
                )
        print("== END ==")
    except Exception as e:
        await update.message.reply_text(f"Failed   : {str(e)}")


def __str2datetime(inp):
    dt = datetime.strptime(inp, "%Y-%m-%d %H:%M:%S")
    return datetime.combine(dt.date(), dt.time())


def __get_active_thread(user_id: int):
    print("__get_active_thread")
    open_new_thread = False
    last_interaction = UserCollection.get_attribute(user_id, "last_interaction")
    last_interaction = __str2datetime(last_interaction)
    delta = (datetime.now() - last_interaction).total_seconds()

    thread_id = UserCollection.get_attribute(user_id, "current_thread_id")
    if delta > cfg.idle_timeout:
        thread_id = AssistantGPT.new_thread().id
        UserCollection.update_attribute(user_id, "current_thread_id", thread_id)
        open_new_thread = True
    
    UserCollection.tick(user_id)
    return thread_id, open_new_thread


def __release_old_files(file_ids: list):
    while len(file_ids) != 0:
        file_id = file_ids.pop(0)
        OpenAiFile.delete_file(file_id)


async def attachment_handler(update: Update, context: CallbackContext):
    print("\nIn attachment_handler\n")
    user = update.message.from_user
    caption = update.message.caption  # this does not retrieve the text portion
    try:
        assistant = UserCollection.get_attribute(user.id, "current_assistant")
        assistant_metadata = cfg.assistant[assistant["name"]]
        if (
            assistant_metadata["tools"]["code_interpreter"] == "disabled"
            and assistant_metadata["tools"]["retrieval"] == "disabled"
        ):
            return await update.message.reply_text(
                f"{assistant['name']} does not support file operations."
            )

        thread_id, is_new_thread = __get_active_thread(user.id)

        doc = update.message.document

        filename = doc["file_name"]
        telegram_fileId = doc["file_id"]

        export_path = f"/data/" + filename
        # get current file ids from MongoDB
        file_ids = UserCollection.get_attribute(user.id, "current_file_ids")

        if is_new_thread:
            __release_old_files(file_ids)
            file_ids = []
        print("Load file from Telegram")
        # load file from Telegram
        doc_file = await context.bot.get_file(telegram_fileId)
        # Store file to Local Drive
        await doc_file.download_to_drive(
            export_path, read_timeout=3000, write_timeout=3000, connect_timeout=3000
        )
        print("Store file to OpenAI")
        # Store file to OpenAI
        file_id = OpenAiFile.store_file(export_path)

        print("File Management - FIFO")
        # File Management - FIFO
        while len(file_ids) >= cfg.max_file_count_per_thread:
            file_id = file_ids.pop(0)
            OpenAiFile.delete_file(file_id)  # delete oldest at OpenAI
        file_ids.append(file_id)
        UserCollection.update_attribute(
            user.id, "current_file_ids", file_ids
        )  # write back to MongoDB
        print("Instruct")
        prompt = f"File: {filename}\n----------------\nCaption: {caption}"
        status, messages = await AssistantGPT.instruct(
            assistant["id"], thread_id, prompt, file_ids
        )
        if status['msg'] != 'completed':
            return await update.message.reply_text(f"Failed   : {status['msg']}")
            await start_new_session(update, context)
        
        print("Post Processing")
        output_messages = post_processing(thread_id, messages)
        for msg in output_messages:
            DialogCollection.add(thread_id, msg)
            if msg["role"] == "user":
                continue

            if msg["type"] == "text":
                await update.message.reply_text(msg["data"])
            elif msg["type"] == "image_file":
                await update.message.reply_photo(
                    open(msg["data"], "rb"), caption="system generated"
                )
        print("== END ==")
    except Exception as e:
        await update.message.reply_text(f"Failed   : {str(e)}")


async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    try:
        # collect error message
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except:
        await context.bot.send_message(
            update.effective_chat.id, "Some error in error handler"
        )


async def start_new_session(update: Update, context: CallbackContext):
    print("Start new session")
    user = update.message.from_user

    current_thread_id = UserCollection.get_attribute(user.id, "current_thread_id")

    try:
        # delete dialogs
        DialogCollection.drop(current_thread_id)

        # delete files
        current_file_ids = UserCollection.get_attribute(user.id, "current_file_ids")

        for file_id in current_file_ids:
            OpenAiFile.delete_file(file_id)

        UserCollection.update_attribute(user.id, "current_file_ids", [])

        await update.message.reply_text("Old session deleted.")

        # new thread
        new_thread_id = AssistantGPT.new_thread().id
        UserCollection.update_attribute(user.id, "current_thread_id", new_thread_id)
        UserCollection.tick(user.id)
        
        await update.message.reply_text("New session started.", parse_mode=ParseMode.HTML)

        assistant_greeting = cfg.assistant[cfg.default_assistant_name]["greeting"]
        assistant_parse_mode = cfg.assistant[cfg.default_assistant_name]["parse_mode"]

        await update.message.reply_text(
            assistant_greeting,
            parse_mode=ParseMode.HTML
            if assistant_parse_mode == "html"
            else ParseMode.MARKDOWN,
        )
    except Exception as e:
        print(str(e), flush=True)
        await update.message.reply_text(
            str(e),
            parse_mode=ParseMode.HTML
        )
