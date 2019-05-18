import re
from typing import Optional

import telegram
from telegram import ParseMode, InlineKeyboardMarkup, Message, Chat
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown

from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import user_admin
from emilia.modules.helper_funcs.extraction import extract_text
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.misc import build_keyboard
from emilia.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser
from emilia.modules.sql import cust_filters_sql as sql

from emilia.modules.connection import connected

HANDLER_GROUP = 10


@run_async
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        filter_list = "*Filter di {}:*\n"
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "filter lokal"
            filter_list = "*filter lokal:*\n"
        else:
            chat_name = chat.title
            filter_list = "*Filter di {}*:\n"

    all_handlers = sql.get_chat_triggers(chat_id)


    if not all_handlers:
        update.effective_message.reply_text("Tidak ada filter di {}!".format(chat_name))
        return

    for keyword in all_handlers:
        entry = " - {}\n".format(escape_markdown(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list.format(chat_name), parse_mode=telegram.ParseMode.MARKDOWN)
            filter_list = entry
        else:
            filter_list += entry

    update.effective_message.reply_text(filter_list.format(chat_name), parse_mode=telegram.ParseMode.MARKDOWN)


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "catatan lokal"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    # set trigger -> lower, so as to avoid adding duplicate filters with different cases
    keyword = extracted[0].lower()

    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    buttons = []

    # determine what the contents of the filter are - text, image, sticker, etc
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)  # set correct offset relative to command + notename
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()
        if not content:
            msg.reply_text("Tidak ada pesan catatan - Anda tidak bisa HANYA menekan tombol, Anda perlu pesan untuk melakukannya!")
            return

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        is_document = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        is_image = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        is_audio = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        is_voice = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        is_video = True

    else:
        msg.reply_text("Anda tidak menentukan apa yang harus dibalas!")
        return

    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat_id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(chat_id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons)

    msg.reply_text("Handler '{}' ditambahkan di *{}*!".format(keyword, chat_name), parse_mode=telegram.ParseMode.MARKDOWN)
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = update.effective_message.text.split(None, 1)

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "local notes"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat_id)

    if not chat_filters:
        update.effective_message.reply_text("Tidak ada filter aktif di sini!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat_id, args[1])
            update.effective_message.reply_text("Ya, saya akan berhenti menjawabnya di *{}*.".format(chat_name), parse_mode=telegram.ParseMode.MARKDOWN)
            raise DispatcherHandlerStop

    update.effective_message.reply_text("Itu bukan filter aktif - jalankan /filter untuk semua filter aktif.")


@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            if filt.is_sticker:
                message.reply_sticker(filt.reply)
            elif filt.is_document:
                message.reply_document(filt.reply)
            elif filt.is_image:
                message.reply_photo(filt.reply)
            elif filt.is_audio:
                message.reply_audio(filt.reply)
            elif filt.is_voice:
                message.reply_voice(filt.reply)
            elif filt.is_video:
                message.reply_video(filt.reply)
            elif filt.has_markdown:
                buttons = sql.get_buttons(chat.id, filt.keyword)
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                try:
                    message.reply_text(filt.reply, parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True,
                                       reply_markup=keyboard)
                except BadRequest as excp:
                    if excp.message == "Unsupported url protocol":
                        try:
                            message.reply_text("Anda tampaknya mencoba menggunakan protokol url yang tidak didukung. Telegram "
                                               "tidak mendukung tombol untuk beberapa protokol, seperti tg://. Silakan coba "
                                               "lagi.")
                        except BadRequest as excp:
                            LOGGER.exception("Gagal mengirim pesan: " + excp.message)
                            pass
                    elif excp.message == "Reply message not found":
                        try:
                            bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                             disable_web_page_preview=True,
                                             reply_markup=keyboard)
                        except BadRequest as excp:
                            LOGGER.exception("Gagal mengirim pesan: " + excp.message)
                            pass
                    else:
                        try:
                            message.reply_text("Catatan ini tidak dapat dikirim karena formatnya salah.")
                        except BadRequest as excp:
                            LOGGER.exception("Gagal mengirim pesan: " + excp.message)
                            pass
                        LOGGER.warning("Message %s could not be parsed", str(filt.reply))
                        LOGGER.exception("Could not parse filter %s in chat %s", str(filt.keyword), str(chat.id))

            else:
                # LEGACY - all new filters will have has_markdown set to True.
                try:
                    message.reply_text(filt.reply)
                except BadRequest as excp:
                    LOGGER.exception("Gagal mengirim pesan: " + excp.message)
                    pass
            break


def __stats__():
    return "{} filter, pada {} obrolan.".format(sql.num_filters(), sql.num_chats())


def __import_data__(chat_id, data):
    # set chat filters
    filters = data.get('filters', {})
    for trigger in filters:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "Ada `{}` filter khusus di sini.".format(len(cust_filters))


__help__ = """
 - /filters: daftar semua filter aktif dalam obrolan ini.

*Hanya admin:*
 - /filter <kata kunci> <pesan balasan>: tambahkan filter ke obrolan ini. Bot sekarang akan membalas pesan itu jika 'kata kunci'\
disebutkan. Jika Anda membalas stiker dengan kata kunci, bot akan membalas dengan stiker itu. CATATAN: semua filter \
kata kunci dalam huruf kecil. Jika Anda ingin kata kunci Anda menjadi kalimat, gunakan tanda kutip. seperti: /filter "hei di sana" Bagaimana Anda \
doin?
 - /stop <kata kunci filter>: hentikan filter itu.
"""

__mod_name__ = "Filter"

FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter)
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)
