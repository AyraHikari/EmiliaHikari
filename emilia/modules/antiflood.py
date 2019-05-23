import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_html, escape_markdown

from emilia import dispatcher, spamfilters
from emilia.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from emilia.modules.log_channel import loggable
from emilia.modules.sql import antiflood_sql as sql
from emilia.modules.connection import connected

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text("Saya tidak suka orang yang mengirim pesan beruntun. Tapi kamu hanya membuat "
                       "saya kecewa. Keluar!")

        return "<b>{}:</b>" \
               "\n#BANNED" \
               "\n<b>Pengguna:</b> {}" \
               "\nMembanjiri grup.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("Saya tidak bisa menendang orang di sini, beri saya izin terlebih dahulu! Sampai saat itu, saya akan menonaktifkan antiflood.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\nTidak memiliki izin kick, jadi secara otomatis menonaktifkan antiflood.".format(chat.title)


@run_async
@user_admin
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat_id, 0)
            if conn:
                text = "Antiflood telah dinonaktifkan di *{}*.".format(chat_name)
            else:
                text = "Antiflood telah dinonaktifkan."
            message.reply_text(text, parse_mode="markdown")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = "Antiflood telah dinonaktifkan di *{}*.".format(chat_name)
                else:
                    text = "Antiflood telah dinonaktifkan."
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nNonaktifkan antiflood.".format(html.escape(chat_name), mention_html(user.id, user.first_name))

            elif amount < 3:
                message.reply_text("Antiflood harus baik 0 (dinonaktifkan), atau nomor lebih besar dari 3!")
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = "Antiflood telah diperbarui dan diset menjadi *{}* pada *{}*".format(amount, chat_name)
                else:
                    text = "Antiflood telah diperbarui dan diset menjadi *{}*".format(amount)
                message.reply_text(text, parse_mode="markdown")
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nSetel antiflood ke <code>{}</code>.".format(html.escape(chat_name),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("Argumen tidak dikenal - harap gunakan angka, 'off', atau 'no'.")
    else:
        message.reply_text("Gunakan `/setflood nomor` untuk menyetel anti pesan beruntun.\nAtau gunakan `/setflood off` untuk menonaktifkan anti pesan beruntun.", parse_mode="markdown")
    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = "Saat ini saya tidak memberlakukan pengendalian pesan beruntun pada *{}*!".format(chat_name)
        else:
            text = "Saat ini saya tidak memberlakukan pengendalian pesan beruntun"
        update.effective_message.reply_text(text, parse_mode="markdown")
    else:
        if conn:
            text = "Saat ini saya melarang pengguna jika mereka mengirim lebih dari *{}* pesan berturut-turut pada *{}*.".format(limit, chat_name)
        else:
            text = "Saat ini saya melarang pengguna jika mereka mengirim lebih dari *{}* pesan berturut-turut.".format(limit)
        update.effective_message.reply_text(text, parse_mode="markdown")


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Saat ini *Tidak* menegakkan pengendalian pesan beruntun."
    else:
        return "Anti Pesan Beruntun diatur ke `{}` pesan.".format(limit)

def __chat_settings_btn__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        status = "❎ Tidak Aktif"
    else:
        status = "✅ Aktif"
    button = []
    button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
            InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
            InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
    return button

def FLOOD_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button FLOOD EDIT".format(user.id))
    qdata = query.data.split("=")[1].split("|")[0]
    chat_id = query.data.split("|")[1]
    if qdata == "?":
        bot.answerCallbackQuery(query.id, "Batas dari pesan beruntun. Jika pengguna mengirim pesan lebih dari batas, maka akan langsung di banned.", show_alert=True)
    if qdata == "-":
        button = []
        limit = sql.get_flood_limit(chat_id)
        limit = int(limit)-1
        if limit == 0:
            status = "❎ Tidak Aktif"
        else:
            status = "✅ Aktif"
        if limit <= 2:
            bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 3", show_alert=True)
            return
        sql.set_flood(chat_id, int(limit))
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(limit)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if qdata == "+":
        button = []
        limit = sql.get_flood_limit(chat_id)
        limit = int(limit)+1
        if limit == 0:
            status = "❎ Tidak Aktif"
        else:
            status = "✅ Aktif"
        if limit <= 0:
            bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 0", show_alert=True)
            return
        sql.set_flood(chat_id, int(limit))
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(limit)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if qdata == "exec":
        button = []
        limit = sql.get_flood_limit(chat_id)
        if limit == 0:
            sql.set_flood(chat_id, 3)
            limit = 3
            status = "✅ Aktif ({})".format(limit)
        else:
            sql.set_flood(chat_id, 0)
            limit = 0
            status = "❎ Tidak Aktif"
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Anti Pesan Beruntun*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal pesan beruntun telah di setel menjadi `{}`.".format(status)
        button.append([InlineKeyboardButton(text="➖", callback_data="set_flim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_flim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_flim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format(status), callback_data="set_flim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)


__help__ = """
 - /flood: Dapatkan pengaturan kontrol pesan beruntun saat ini

*Hanya admin:*
 - /setflood <int/'no'/'off'>: mengaktifkan atau menonaktifkan kontrol pesan beruntun
"""

__mod_name__ = "Anti Pesan Beruntun"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True)#, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood)#, filters=Filters.group)
FLOOD_BTNSET_HANDLER = CallbackQueryHandler(FLOOD_EDITBTN, pattern=r"set_flim")

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_BTNSET_HANDLER)
