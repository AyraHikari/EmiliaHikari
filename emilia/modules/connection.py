import time
import re
from typing import Optional, List

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Message, Chat, Update, Bot, User, error
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import emilia.modules.sql.connection_sql as sql
from emilia import dispatcher, LOGGER, SUDO_USERS, spamfilters
from emilia.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from emilia.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from emilia.modules.helper_funcs.string_handling import extract_time

from emilia.modules import languages
from emilia.modules.helper_funcs.alternate import send_message


@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if (var == "no" or var == "tidak"):
                sql.set_allow_connect_to_chat(chat.id, False)
                send_message(update.effective_message, languages.tl(update.effective_message, "Sambungan telah dinonaktifkan untuk obrolan ini"))
            elif(var == "yes" or var == "ya"):
                sql.set_allow_connect_to_chat(chat.id, True)
                send_message(update.effective_message, languages.tl(update.effective_message, "Koneksi di aktifkan untuk obrolan ini"))
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Silakan masukkan `ya`/`yes` atau `tidak`/`no`!"), parse_mode=ParseMode.MARKDOWN)
        else:
            get_settings = sql.allow_connect_to_chat(chat.id)
            if get_settings:
                send_message(update.effective_message, languages.tl(update.effective_message, "Koneksi pada grup ini di *Di Izinkan* untuk member!"), parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Koneksi pada grup ini di *Tidak Izinkan* untuk member!"), parse_mode=ParseMode.MARKDOWN)
    else:
        send_message(update.effective_message, languages.tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))

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
    send_message(update.effective_message, teks, parse_mode="markdown")

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
                    send_message(update.effective_message, languages.tl(update.effective_message, "ID Obrolan tidak valid!"))
                    return
            except error.BadRequest:
                send_message(update.effective_message, languages.tl(update.effective_message, "ID Obrolan tidak valid!"))
                return
            isadmin = getstatusadmin.status in ('administrator', 'creator')
            ismember = getstatusadmin.status in ('member')
            isallow = sql.allow_connect_to_chat(connect_chat)
            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    conn_chat = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False))
                    chat_name = conn_chat.title
                    send_message(update.effective_message, languages.tl(update.effective_message, "Berhasil tersambung ke *{}*. Gunakan /connection untuk informasi perintah apa saja yang tersedia.").format(chat_name), parse_mode=ParseMode.MARKDOWN)
                    sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
                    # send_message(update.effective_message, languages.tl(update.effective_message, "supportcmd"), parse_mode="markdown")
                else:
                    send_message(update.effective_message, languages.tl(update.effective_message, "Koneksi gagal!"))
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"))
        else:
            gethistory = sql.get_history_conn(user.id)
            if gethistory:
                buttons = [InlineKeyboardButton(text=languages.tl(update.effective_message, "❎ Close button"), callback_data="connect_close"), InlineKeyboardButton(text=languages.tl(update.effective_message, "🧹 Hapus riwayat"), callback_data="connect_clear")]
            else:
                buttons = []
            conn = connected(bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = languages.tl(update.effective_message, "Anda telah terkoneksi pada *{}* (`{}`)").format(connectedchat.title, conn)
                buttons.append(InlineKeyboardButton(text=languages.tl(update.effective_message, "🔌 Putuskan sambungan"), callback_data="connect_disconnect"))
            else:
                text = languages.tl(update.effective_message, "Tulis ID obrolan atau tagnya untuk terhubung!")
            if gethistory:
                text += languages.tl(update.effective_message, "\n\n*Riwayat koneksi:*\n")
                text += languages.tl(update.effective_message, "╒═══「 *Info* 」\n")
                text += languages.tl(update.effective_message, "│  Sorted: `Newest`\n")
                text += "│\n"
                buttons = [buttons]
                for x in sorted(gethistory.keys(), reverse=True):
                    htime = time.strftime("%d/%m/%Y", time.localtime(x))
                    text += "╞═「 *{}* 」\n│   `{}`\n│   `{}`\n".format(gethistory[x]['chat_name'], gethistory[x]['chat_id'], htime)
                    text += "│\n"
                    buttons.append([InlineKeyboardButton(text=gethistory[x]['chat_name'], callback_data="connect({})".format(gethistory[x]['chat_id']))])
                text += "╘══「 Total {} Chats 」".format(str(len(gethistory)) + " (max)" if len(gethistory) == 5 else str(len(gethistory)))
                conn_hist = InlineKeyboardMarkup(buttons)
            elif buttons:
                conn_hist = InlineKeyboardMarkup([buttons])
            else:
                conn_hist = None
            send_message(update.effective_message, text, parse_mode="markdown", reply_markup=conn_hist)

    else:
        getstatusadmin = bot.get_chat_member(chat.id, update.effective_message.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(update.effective_message.from_user.id, chat.id)
            if connection_status:
                chat_name = dispatcher.bot.getChat(chat.id).title
                send_message(update.effective_message, languages.tl(update.effective_message, "Berhasil tersambung ke *{}*.").format(chat_name), parse_mode=ParseMode.MARKDOWN)
                try:
                    sql.add_history_conn(user.id, str(chat.id), chat_name)
                    bot.send_message(update.effective_message.from_user.id, languages.tl(update.effective_message, "Anda telah terhubung dengan *{}*. Gunakan /connection untuk informasi perintah apa saja yang tersedia.").format(chat_name), parse_mode="markdown")
                except BadRequest:
                    pass
                except error.Unauthorized:
                    pass
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Koneksi gagal!"))
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"))


def disconnect_chat(bot, update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = send_message(update.effective_message, languages.tl(update.effective_message, "Terputus dari obrolan!"))
        else:
           send_message(update.effective_message, languages.tl(update.effective_message, "Anda tidak terkoneksi!"))
    else:
        send_message(update.effective_message, languages.tl(update.effective_message, "Penggunaan terbatas hanya untuk PM"))


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
                    send_message(update.effective_message, languages.tl(update.effective_message, "Anda harus menjadi admin dalam grup yang terhubung!"))
                    raise Exception("Bukan admin!")
            else:
                return conn_id
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Grup mengubah koneksi hak atau Anda bukan admin lagi.\nSaya putuskan koneksi Anda."))
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
        send_message(update.effective_message, languages.tl(update.effective_message, "PM saya dengan command itu untuk mendapatkan bantuan Koneksi"))
        return
    else:
        send_message(update.effective_message, languages.tl(update.effective_message, "supportcmd"), parse_mode="markdown")

@run_async
def connect_button(bot: Bot, update: Update) -> str:
    query = update.callback_query
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    connect_match = re.match(r"connect\((.+?)\)", query.data)
    disconnect_match = query.data == "connect_disconnect"
    clear_match = query.data == "connect_clear"
    connect_close = query.data == "connect_close"

    if connect_match:
        target_chat = connect_match.group(1)
        getstatusadmin = bot.get_chat_member(target_chat, query.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(target_chat)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(query.from_user.id, target_chat)
            if connection_status:
                conn_chat = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False))
                chat_name = conn_chat.title
                query.message.edit_text(languages.tl(update.effective_message, "Berhasil tersambung ke *{}*. Gunakan /connection untuk informasi perintah apa saja yang tersedia.").format(chat_name), parse_mode=ParseMode.MARKDOWN)
                sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
            else:
                query.message.edit_text(languages.tl(update.effective_message, "Koneksi gagal!"))
        else:
            bot.answer_callback_query(query.id, languages.tl(update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"), show_alert=True)
    elif disconnect_match:
        disconnection_status = sql.disconnect(query.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = query.message.edit_text(languages.tl(update.effective_message, "Terputus dari obrolan!"))
        else:
           bot.answer_callback_query(query.id, languages.tl(update.effective_message, "Anda tidak terkoneksi!"), show_alert=True)
    elif clear_match:
        sql.clear_history_conn(query.from_user.id)
        query.message.edit_text(languages.tl(update.effective_message, "Riwayat yang terhubung telah dihapus!"))
    elif connect_close:
        query.message.edit_text(languages.tl(update.effective_message, "Closed.\nTo open again, type /connect"))
    else:
        connect_chat(bot, update, [])


__help__ = "connection_help"

__mod_name__ = "Connection"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, allow_edited=True, pass_args=True)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, allow_edited=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, allow_edited=True, pass_args=True)
HELP_CONNECT_CHAT_HANDLER = CommandHandler("helpconnect", help_connect_chat, allow_edited=True, pass_args=True)
CONNECT_BTN_HANDLER = CallbackQueryHandler(connect_button, pattern=r"connect")

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECTION_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(HELP_CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECT_BTN_HANDLER)
