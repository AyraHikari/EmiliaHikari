from typing import Optional, List

from telegram import ParseMode
from telegram import Message, Chat, Update, Bot, User, error
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import emilia.modules.sql.connection_sql as sql
from emilia import dispatcher, LOGGER, SUDO_USERS, spamfilters
from emilia.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from emilia.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from emilia.modules.helper_funcs.string_handling import extract_time

from emilia.modules import languages


@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if (var == "no" or var == "tidak"):
                sql.set_allow_connect_to_chat(chat.id, False)
                update.effective_message.reply_text(languages.tl(update.effective_message, "Sambungan telah dinonaktifkan untuk obrolan ini"))
            elif(var == "yes" or var == "ya"):
                sql.set_allow_connect_to_chat(chat.id, True)
                update.effective_message.reply_text(languages.tl(update.effective_message, "Koneksi di aktifkan untuk obrolan ini"))
            else:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Silakan masukkan `ya`/`yes` atau `tidak`/`no`!"), parse_mode=ParseMode.MARKDOWN)
        else:
            get_settings = sql.allow_connect_to_chat(chat.id)
            if get_settings:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Koneksi pada grup ini di *Di Izinkan* untuk member!"), parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Koneksi pada grup ini di *Tidak Izinkan* untuk member!"), parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text(languages.tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))

@run_async
def connection_chat(bot, update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type != "private":
            return
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if conn:
        teks = languages.tl(update.effective_message, "Saat ini Anda terhubung dengan {}.\n").format(chat_name)
    else:
        teks = languages.tl(update.effective_message, "Saat ini Anda tidak terhubung dengan grup.\n")
    teks += languages.tl(update.effective_message, "supportcmd")
    update.effective_message.reply_text(teks, parse_mode="markdown")

@run_async
def connect_chat(bot, update, args):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    if update.effective_chat.type == 'private':
        if len(args) >= 1:
            try:
                connect_chat = int(args[0])
                getstatusadmin = bot.get_chat_member(connect_chat, update.effective_message.from_user.id)
            except ValueError:
                try:
                    connect_chat = str(args[0])
                    get_chat = bot.getChat(connect_chat)
                    connect_chat = get_chat.id
                    getstatusadmin = bot.get_chat_member(connect_chat, update.effective_message.from_user.id)
                except error.BadRequest:
                    update.effective_message.reply_text(languages.tl(update.effective_message, "ID Obrolan tidak valid!"))
                    return
            isadmin = getstatusadmin.status in ('administrator', 'creator')
            ismember = getstatusadmin.status in ('member')
            isallow = sql.allow_connect_to_chat(connect_chat)
            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    chat_name = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False)).title
                    update.effective_message.reply_text(languages.tl(update.effective_message, "Berhasil tersambung ke *{}*").format(chat_name), parse_mode=ParseMode.MARKDOWN)
                    update.effective_message.reply_text(languages.tl(update.effective_message, "supportcmd"), parse_mode="markdown")
                else:
                    update.effective_message.reply_text(languages.tl(update.effective_message, "Koneksi gagal!"))
            else:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"))
        else:
            conn = connected(bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = languages.tl(update.effective_message, "Anda telah terkoneksi pada *{}* (`{}`)").format(connectedchat.title, conn)
                update.effective_message.reply_text(text, parse_mode="markdown")
            else:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Tulis ID obrolan atau tagnya untuk terhubung!"))

    else:
        getstatusadmin = bot.get_chat_member(chat.id, update.effective_message.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(update.effective_message.from_user.id, chat.id)
            if connection_status:
                chat_name = dispatcher.bot.getChat(chat.id).title
                update.effective_message.reply_text(languages.tl(update.effective_message, "Berhasil tersambung ke *{}*").format(chat_name), parse_mode=ParseMode.MARKDOWN)
                try:
                    bot.send_message(update.effective_message.from_user.id, languages.tl(update.effective_message, "Anda telah terhubung dengan *{}*. Gunakan /connection untuk informasi perintah apa saja yang tersedia.").format(chat_name), parse_mode="markdown")
                except BadRequest:
                    pass
                except error.Unauthorized:
                    pass
            else:
                update.effective_message.reply_text(languages.tl(update.effective_message, "Koneksi gagal!"))
        else:
            update.effective_message.reply_text(languages.tl(update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"))


def disconnect_chat(bot, update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = update.effective_message.reply_text(languages.tl(update.effective_message, "Terputus dari obrolan!"))
        else:
           update.effective_message.reply_text(languages.tl(update.effective_message, "Memutus sambungan tidak berhasil!"))
    else:
        update.effective_message.reply_text(languages.tl(update.effective_message, "Penggunaan terbatas hanya untuk PM"))


def connected(bot, update, chat, user_id, need_admin=True):
    user = update.effective_user  # type: Optional[User]
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
        
    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):
        conn_id = sql.get_connected_chat(user_id).chat_id
        getstatusadmin = bot.get_chat_member(conn_id, update.effective_message.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(conn_id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            if need_admin == True:
                if getstatusadmin.status in ('administrator', 'creator') or user_id in SUDO_USERS:
                    return conn_id
                else:
                    update.effective_message.reply_text(languages.tl(update.effective_message, "Anda harus menjadi admin dalam grup yang terhubung!"))
                    raise Exception("Bukan admin!")
            else:
                return conn_id
        else:
            update.effective_message.reply_text(languages.tl(update.effective_message, "Grup mengubah koneksi hak atau Anda bukan admin lagi.\nSaya putuskan koneksi Anda."))
            disconnect_chat(bot, update)
            raise Exception("Bukan admin!")
    else:
        return False

@run_async
def help_connect_chat(bot, update, args):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if update.effective_message.chat.type != "private":
        update.effective_message.reply_text(languages.tl(update.effective_message, "PM saya dengan command itu untuk mendapatkan bantuan Koneksi"))
        return
    else:
        update.effective_message.reply_text(languages.tl(update.effective_message, "supportcmd"), parse_mode="markdown")


__help__ = "connection_help"

__mod_name__ = "Connection"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, allow_edited=True, pass_args=True)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, allow_edited=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, allow_edited=True, pass_args=True)
HELP_CONNECT_CHAT_HANDLER = CommandHandler("helpconnect", help_connect_chat, allow_edited=True, pass_args=True)

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECTION_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(HELP_CONNECT_CHAT_HANDLER)
