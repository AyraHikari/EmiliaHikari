import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import emilia.modules.sql.blacklist_sql as sql
from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import user_admin, user_not_admin
from emilia.modules.helper_funcs.extraction import extract_text
from emilia.modules.helper_funcs.misc import split_message

from emilia.modules.connection import connected

BLACKLIST_GROUP = 11


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
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
        if chat.type == "private":
            return
        else:
            chat_id = update.effective_chat.id
            chat_name = chat.title
    
    filter_list = "<b>Kata daftar hitam saat ini di {}:</b>\n".format(chat_name)

    all_blacklisted = sql.get_chat_blacklist(chat_id)

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    # for trigger in all_blacklisted:
    #     filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if filter_list == "<b>Kata daftar hitam saat ini di {}:</b>\n".format(chat_name):
            msg.reply_text("Tidak ada pesan daftar hitam di <b>{}</b>!".format(chat_name), parse_mode=ParseMode.HTML)
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    words = msg.text.split(None, 1)

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat_id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("<code>{}</code> ditambahkan ke daftar hitam di <b>{}</b>!".format(html.escape(to_blacklist[0]), chat_name),
                parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                    "<code>{}</code> Pemicu ditambahkan ke daftar hitam di <b>{}</b>!".format(len(to_blacklist)), chat_name, parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("Beri tahu saya kata-kata apa yang ingin Anda hapus dari daftar hitam.")


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    words = msg.text.split(None, 1)

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title


    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("<code>{}</code> dihapus dari daftar hitam di <b>{}</b>!".format(html.escape(to_unblacklist[0]), chat_name),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("Ini bukan pemicu daftar hitam...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "Pemicu <code>{}</code> dihapus dari daftar hitam di <b>{}</b>!".format(
                    successful, chat_name), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "Tidak satu pun pemicu ini ada, sehingga tidak dapat dihapus.".format(
                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Pemicu <code>{}</code> dihapus dari daftar hitam. {} Tidak ada, "
                "jadi tidak dihapus.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Beri tahu saya kata-kata apa yang ingin Anda hapus dari daftar hitam.")


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error while deleting blacklist message.")
            break


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get('blacklist', {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted)


def __stats__():
    return "{} pemicu daftar hitam, di seluruh {} obrolan.".format(sql.num_blacklist_filters(),
                                                            sql.num_blacklist_filter_chats())


__mod_name__ = "Word Blacklists"

__help__ = """
Blacklist digunakan untuk menghentikan pemicu tertentu dari yang dikatakan dalam kelompok. Kapan pun pemicu disebutkan, \
pesan akan segera dihapus. Sebuah kombo yang bagus terkadang memasangkan ini dengan filter peringatan!

*CATATAN:* daftar hitam tidak mempengaruhi admin grup.

 - /blacklist: Lihat kata-kata daftar hitam saat ini.

*Hanya admin:*
 - /addblacklist <pemicu>: Tambahkan pemicu ke daftar hitam. Setiap baris dianggap sebagai pemicu, jadi gunakan garis yang \
berbeda akan memungkinkan Anda menambahkan beberapa pemicu.
 - /unblacklist <pemicu>: Hapus pemicu dari daftar hitam. Logika newline yang sama berlaku di sini, sehingga Anda dapat \
menghapus beberapa pemicu sekaligus.
 - /rmblacklist <pemicu>: Sama seperti di atas.
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, pass_args=True,
                                              admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist, edited_updates=True)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
