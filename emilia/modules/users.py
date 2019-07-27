from io import BytesIO
from time import sleep
from typing import Optional

from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async

import emilia.modules.sql.feds_sql as fedsql
import emilia.modules.sql.users_sql as sql
from emilia import dispatcher, OWNER_ID, LOGGER
from emilia.modules import languages
from emilia.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4


def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith("@"):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    elif len(users) == 1:
        return users[0].user_id

    else:
        for user_obj in users:
            try:
                userdat = dispatcher.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id

            except BadRequest as excp:
                if excp.message == "Chat not found":
                    pass
                else:
                    LOGGER.exception("Error extracting user ID")

    return None


@run_async
def broadcast(bot: Bot, update: Update):
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) >= 2:
        chats = sql.get_all_chats() or []
        failed = 0
        for chat in chats:
            try:
                bot.sendMessage(int(chat.chat_id), to_send[1])
                sleep(0.1)
            except TelegramError:
                failed += 1
                LOGGER.warning(
                    "Couldn't send broadcast to %s, group name %s",
                    str(chat.chat_id),
                    str(chat.chat_name),
                )

        update.effective_message.reply_text(
            "Siaran selesai. {} grup gagal menerima pesan, mungkin "
            "karena ditendang.".format(failed)
        )


@run_async
def log_user(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    fed_id = fedsql.get_fed_id(chat.id)
    if fed_id:
        user = update.effective_user
        if user:
            fban, fbanreason, fbantime = fedsql.get_fban_user(fed_id, user.id)
            if fban:
                update.effective_message.reply_text(
                    languages.tl(
                        update.effective_message,
                        "Pengguna ini dilarang di federasi saat ini!\nAlasan: `{}`",
                    ).format(fbanreason),
                    parse_mode="markdown",
                )
                try:
                    bot.kick_chat_member(chat.id, user.id)
                except:
                    print("Fban: cannot banned this user")

    sql.update_user(msg.from_user.id, msg.from_user.username, chat.id, chat.title)

    if msg.reply_to_message:
        sql.update_user(
            msg.reply_to_message.from_user.id,
            msg.reply_to_message.from_user.username,
            chat.id,
            chat.title,
        )

    if msg.forward_from:
        sql.update_user(msg.forward_from.id, msg.forward_from.username)


@run_async
def chats(bot: Bot, update: Update):
    all_chats = sql.get_all_chats() or []
    chatfile = "Daftar obrolan.\n"
    for chat in all_chats:
        chatfile += "{} - ({})\n".format(chat.chat_name, chat.chat_id)

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="chatlist.txt",
            caption="Berikut ini daftar obrolan dalam database saya.",
        )


def __user_info__(user_id, chat_id):
    if user_id == dispatcher.bot.id:
        return languages.tl(
            chat_id,
            """Saya telah melihatnya... Wow. Apakah mereka menguntit saya? Mereka ada di semua tempat yang sama dengan saya... oh. Ini aku.""",
        )
    num_chats = sql.get_user_num_chats(user_id)
    return languages.tl(
        chat_id, """Saya telah melihatnya <code>{}</code> obrolan total."""
    ).format(num_chats)


def __stats__():
    return languages.tl(OWNER_ID, "{} pengguna, pada {} obrolan").format(
        sql.num_users(), sql.num_chats()
    )


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string

__mod_name__ = "Users"

BROADCAST_HANDLER = CommandHandler(
    "broadcast", broadcast, filters=Filters.user(OWNER_ID)
)
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHATLIST_HANDLER = CommandHandler("chatlist", chats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
