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

supportcmd = """
*Command yang support saat ini*

*「 Untuk Member Biasa 」*
*Admin*
-> `/adminlist` | `/admins`

*Anti Flood*
-> `/flood`

*Blacklist*
-> `/blacklist`

*Blacklist Sticker*
-> `/blsticker`

*Filter*
-> `/filters`

*Notes*
-> `/get`
-> `/notes` | `/saved`

*Peraturan*
-> `/rules`

*Peringatan*
-> `/warns`
-> `/warnlist` | `/warnfilters`

*「 Hanya Untuk Admin 」*
*Admin*
-> `/pin <loud/silent> <message link>`
-> `/unpin`
-> `/adminlist`
-> `/promote @user`
-> `/demote @user`

*Anti Flood*
-> `/setflood`
-> `/flood`

*Banned*
-> `/ban`
-> `/tban` | `/tempban`
-> `/kick`
-> `/unban`

*Blacklist*
-> `/blacklist`
-> `/addblacklist`
-> `/unblacklist` | `/rmblacklist`

*Blacklist Sticker*
-> `/blsticker`
-> `/addblsticker`
-> `/unblsticker` | `/rmblsticker`

*Bisukan Pengguna*
-> `/mute`
-> `/unmute`
-> `/tmute`

*Disabler*
-> `/enable`
-> `/disable`
-> `/cmds`

*Filter*
-> `/filter`
-> `/stop`
-> `/filters`

*Notes*
-> `/get`
-> `/save`
-> `/clear`
-> `/notes` | `/saved`

*Penguncian*
-> `/lock`
-> `/unlock`
-> `/locks`

*Peraturan*
-> `/rules`
-> `/setrules`
-> `/clearrules`

*Pencadangan*
-> `/import`
-> `/export`

*Peringatan*
-> `/warn`
-> `/resetwarn` | `/resetwarns`
-> `/warns`
-> `/addwarn`
-> `/nowarn` | `/stopwarn`
-> `/warnlist` | `/warnfilters`
-> `/warnlimit`
-> `/strongwarn`
"""

@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if (var == "no" or var == "tidak"):
                sql.set_allow_connect_to_chat(chat.id, False)
                update.effective_message.reply_text("Sambungan telah dinonaktifkan untuk obrolan ini")
            elif(var == "yes" or var == "ya"):
                sql.set_allow_connect_to_chat(chat.id, True)
                update.effective_message.reply_text("Koneksi di aktifkan untuk obrolan ini")
            else:
                update.effective_message.reply_text("Silakan masukkan `ya`/`yes` atau `tidak`/`no`!", parse_mode=ParseMode.MARKDOWN)
        else:
            get_settings = sql.allow_connect_to_chat(chat.id)
            if get_settings:
                update.effective_message.reply_text("Koneksi pada grup ini di *Di Izinkan* untuk member!", parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text("Koneksi pada grup ini di *Tidak Izinkan* untuk member!", parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")


@run_async
def connect_chat(bot, update, args):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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
                    update.effective_message.reply_text("ID Obrolan tidak valid!")
                    return
            isadmin = getstatusadmin.status in ('administrator', 'creator')
            ismember = getstatusadmin.status in ('member')
            isallow = sql.allow_connect_to_chat(connect_chat)
            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    chat_name = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False)).title
                    update.effective_message.reply_text("Berhasil tersambung ke *{}*".format(chat_name), parse_mode=ParseMode.MARKDOWN)
                    update.effective_message.reply_text(supportcmd, parse_mode="markdown")
                else:
                    update.effective_message.reply_text("Koneksi gagal!")
            else:
                update.effective_message.reply_text("Sambungan ke obrolan ini tidak diizinkan!")
        else:
            conn = connected(bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = "Anda telah terkoneksi pada *{}* (`{}`)".format(connectedchat.title, conn)
                update.effective_message.reply_text(text, parse_mode="markdown")
            else:
                update.effective_message.reply_text("Tulis ID obrolan untuk terhubung!")

    else:
        update.effective_message.reply_text("Penggunaan terbatas hanya untuk PM!")


def disconnect_chat(bot, update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = update.effective_message.reply_text("Terputus dari obrolan!")
        else:
           update.effective_message.reply_text("Memutus sambungan tidak berhasil!")
    else:
        update.effective_message.reply_text("Penggunaan terbatas hanya untuk PM")


def connected(bot, update, chat, user_id, need_admin=True):
    user = update.effective_user  # type: Optional[User]
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
        
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
                    update.effective_message.reply_text("Anda harus menjadi admin dalam grup yang terhubung!")
                    raise Exception("Bukan admin!")
            else:
                return conn_id
        else:
            update.effective_message.reply_text("Grup mengubah koneksi hak atau Anda bukan admin lagi.\nSaya putuskan koneksi Anda.")
            disconnect_chat(bot, update)
            raise Exception("Bukan admin!")
    else:
        return False

@run_async
def help_connect_chat(bot, update, args):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    if update.effective_message.chat.type != "private":
        update.effective_message.reply_text("PM saya dengan command itu untuk mendapatkan bantuan Koneksi")
        return
    else:
        update.effective_message.reply_text(supportcmd, parse_mode="markdown")

__help__ = """
Atur grup anda via PM dengan mudah.

 - /connect <chatid>: Hubungkan ke obrolan jarak jauh
 - /disconnect: Putuskan sambungan dari obrolan
 - /allowconnect on/yes/off/no: Izinkan menghubungkan pengguna ke grup
 - /helpconnect: Dapatkan bantuan command untuk koneksi
"""

__mod_name__ = "Koneksi"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, allow_edited=True, pass_args=True)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, allow_edited=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, allow_edited=True, pass_args=True)
HELP_CONNECT_CHAT_HANDLER = CommandHandler("helpconnect", help_connect_chat, allow_edited=True, pass_args=True)

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(HELP_CONNECT_CHAT_HANDLER)
