import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from emilia import dispatcher, BAN_STICKER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, \
    can_restrict, is_user_ban_protected
from emilia.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.misc import split_message
from emilia.modules.helper_funcs.string_handling import split_quotes
from emilia.modules.log_channel import loggable
from emilia.modules.sql import warns_sql as sql
from emilia.modules.connection import connected

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Filter peringatan saat ini dalam obrolan ini:</b>\n"


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        message.reply_text("Sayangnya admin tidak bisa di warn 😔")
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Filter peringatan otomatis."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # kick
            chat.unban_member(user.id)
            reply = "{} peringatan, {} telah ditendang!".format(limit, mention_html(user.id, user.first_name))

        else:  # ban
            chat.kick_member(user.id)
            reply = "{} peringatan, {} telah diblokir!".format(limit, mention_html(user.id, user.first_name))
            
        for warn_reason in reasons:
            reply += "\n - {}".format(html.escape(warn_reason))

        message.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        log_reason = "<b>{}:</b>" \
                     "\n#WARN_BAN" \
                     "\n<b>Admin:</b> {}" \
                     "\n<b>Pengguna:</b> {} (<code>{}</code>)" \
                     "\n<b>Alasan:</b> {}"\
                     "\n<b>Jumlah:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Hapus peringatan", callback_data="rm_warn({})".format(user.id))]])

        reply = "{} punya {}/{} peringatan... Hati-hati!".format(mention_html(user.id, user.first_name), num_warns,
                                                             limit)
        if reason:
            reply += "\nAlasan pada peringatan terakhir:\n{}".format(html.escape(reason))

        log_reason = "<b>{}:</b>" \
                     "\n#WARN" \
                     "\n<b>Admin:</b> {}" \
                     "\n<b>Pengguna:</b> {} (<code>{}</code>)" \
                     "\n<b>Alasan:</b> {}"\
                     "\n<b>Jumlah:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    try:
        message.bot.sendMessage(chat.id, reply, reply_to_message_id=message.message_id, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        #message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.bot.sendMessage(chat.id, reply, reply_to_message_id=message.message_id, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
            #message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat  # type: Optional[Chat]
        res = sql.remove_warn(user_id, chat.id)
        if res:
            update.effective_message.edit_text(
                "Peringatkan dihapus oleh {}.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return "<b>{}:</b>" \
                   "\n#UNWARN" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>Pengguna:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                mention_html(user.id, user.first_name),
                                                                mention_html(user_member.user.id, user_member.user.first_name),
                                                                user_member.user.id)
        else:
            update.effective_message.edit_text(
            "User has already has no warns.".format(mention_html(user.id, user.first_name)),
            parse_mode=ParseMode.HTML)
            
    return ""


@run_async
@user_admin
#@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]
    user = update.effective_user

    user_id, reason = extract_user_and_text(message, args)

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    check = bot.getChatMember(chat_id, bot.id)
    if check.status == 'member' or check['can_restrict_members'] == False:
        if conn:
            text = "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.".format(chat_name)
        else:
            text = "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru."
        message.reply_text(text, parse_mode="markdown")
        return ""

    if user_id:
        if conn:
            warning = warn(chat.get_member(user_id).user, chat, reason, message, warner)
            update.effective_message.reply_text("Saya sudah memperingatinya pada grup *{}*".format(chat_name), parse_mode="markdown")
            return warning
        else:
            if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
                return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
            else:
                return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("Tidak ada pengguna yang ditunjuk!")
    return ""


@run_async
@user_admin
#@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    check = bot.getChatMember(chat_id, bot.id)
    if check.status == 'member' or check['can_restrict_members'] == False:
        if conn:
            text = "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.".format(chat_name)
        else:
            text = "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru."
        message.reply_text(text, parse_mode="markdown")
        return ""
    
    if user_id:
        sql.reset_warns(user_id, chat.id)
        if conn:
            message.reply_text("Peringatan telah disetel ulang pada *{}*!".format(chat_name), parse_mode="markdown")
        else:
            message.reply_text("Peringatan telah disetel ulang!")
        warned = chat.get_member(user_id).user
        return "<b>{}:</b>" \
               "\n#RESETWARNS" \
               "\n<b>Admin:</b> {}" \
               "\n<b>Pengguna:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name),
                                                            mention_html(warned.id, warned.first_name),
                                                            warned.id)
    else:
        message.reply_text("Tidak ada pengguna yang ditunjuk!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            if conn:
                text = "Pengguna ini memiliki {}/{} peringatan pada *{}*, untuk alasan berikut:".format(num_warns, limit, chat_name)
            else:
                text = "Pengguna ini memiliki {}/{} peringatan, untuk alasan berikut:".format(num_warns, limit)
            for reason in reasons:
                text += "\n - {}".format(reason)

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg, parse_mode="markdown")
        else:
            if conn:
                update.effective_message.reply_text(
                    "Pengguna ini memiliki {}/{} peringatan pada *{}*, tetapi tidak ada alasan untuk itu.".format(num_warns, limit, chat_name), parse_mode="markdown")
            else:
                update.effective_message.reply_text(
                    "Pengguna ini memiliki {}/{} peringatan, tetapi tidak ada alasan untuk itu.".format(num_warns, limit))
    else:
        if conn:
            update.effective_message.reply_text("Pengguna ini belum mendapatkan peringatan apa pun pada *{}*!".format(chat_name), parse_mode="markdown")
        else:
            update.effective_message.reply_text("Pengguna ini belum mendapatkan peringatan apa pun!")


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    if conn:
        text = "Peringatkan handler yang ditambahkan untuk '{}' pada *{}*!".format(keyword, chat_name)
    else:
        text = "Peringatkan handler yang ditambahkan untuk '{}'!".format(keyword)
    update.effective_message.reply_text(text, parse_mode="markdown")
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    args = msg.text.split(None, 1)  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    chat_filters = sql.get_chat_warn_triggers(chat.id)
    if not chat_filters:
        if conn:
            text = "Tidak ada filter peringatan aktif di *{}*!".format(chat_name)
        else:
            text = "Tidak ada filter peringatan aktif di sini!"
        msg.reply_text(text)
        return

    nowarn = 0
    inwarn = 0
    success = ""
    fail = ""
    teks = args[1].split(" ")
    for x in range(len(teks)):
        to_remove = teks[x]
        if to_remove not in chat_filters:
            fail += "`{}` ".format(to_remove)
            nowarn += 1
        for filt in chat_filters:
            if filt == to_remove:
                sql.remove_warn_filter(chat.id, to_remove)
                success += "`{}` ".format(to_remove)
                inwarn += 1
    if nowarn == 0:
        if conn:
            text = "Ya, saya akan berhenti memperingatkan orang-orang untuk {} pada *{}*.".format(success, chat_name)
        else:
            text = "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.".format(success)
        msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop
    elif inwarn == 0:
        if conn:
            text = "Gagal menghapus filter warn untuk {} pada *{}*.".format(fail, chat_name)
        else:
            text = "Gagal menghapus filter warn untuk {}.".format(fail)
        msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop
    else:
        if conn:
            text = "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.\nDan gagal menghapus filter warn untuk {}.\nPada *{}*".format(success, fail, chat_name)
        else:
            text = "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.\nDan gagal menghapus filter warn untuk {}.".format(success, fail)
        msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop

    """
    if not chat_filters:
        msg.reply_text("Tidak ada filter peringatan aktif di sini!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
                msg.reply_text("Ya, saya akan berhenti memperingatkan orang-orang untuk {}.".format(to_remove))
                raise DispatcherHandlerStop
    """

    if conn:
        text = "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif pada *{}*."
    else:
        text = "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif."
    msg.reply_text(text, parse_mode="markdown")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        if conn:
            text = "Tidak ada filter peringatan aktif di *{}*!".format(chat_name)
        else:
            text = "Tidak ada filter peringatan aktif di sini!"
        update.effective_message.reply_text(text, parse_mode="markdown")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    if conn:
        filter_list = filter_list.replace('obrolan ini', 'obrolan *{}*'.format(chat_name))
    for keyword in all_handlers:
        entry = " - {}\n".format(html.escape(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user = update.effective_user  # type: Optional[User]
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("Batas peringatan minimum adalah 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                if conn:
                    text = "Diperbarui batas untuk diperingatkan {} pada *{}*".format(args[0], chat_name)
                else:
                    text = "Diperbarui batas untuk diperingatkan {}".format(args[0])
                msg.reply_text(text, parse_mode="markdown")
                return "<b>{}:</b>" \
                       "\n#SET_WARN_LIMIT" \
                       "\n<b>Admin:</b> {}" \
                       "\nSetel batas peringatan ke <code>{}</code>".format(html.escape(chat.title),
                                                                        mention_html(user.id, user.first_name), args[0])
        else:
            msg.reply_text("Beri aku angkanya!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if conn:
            text = "Batas peringatan saat ini adalah {} pada *{}*".format(limit, chat_name)
        else:
            text = "Batas peringatan saat ini adalah {}".format(limit)
        msg.reply_text(text, parse_mode="markdown")
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            if conn:
                text = "Terlalu banyak peringatan sekarang akan menghasilkan blokir pada *{}*!".format(chat_name)
            else:
                text = "Terlalu banyak peringatan sekarang akan menghasilkan blokir!"
            msg.reply_text(text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Telah mengaktifkan peringatan yang kuat. Pengguna akan diblokir.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            if conn:
                text = "Terlalu banyak peringatan akan menghasilkan tendangan pada *{}*! Pengguna akan dapat bergabung lagi.".format(chat_name)
            else:
                text = "Terlalu banyak peringatan akan menghasilkan tendangan! Pengguna akan dapat bergabung lagi."
            msg.reply_text(text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Telah menonaktifkan peringatan kuat. Pengguna hanya akan ditendang.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            msg.reply_text("Saya hanya mengerti on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            if conn:
                text = "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas pada *{}*.".format(chat_name)
            else:
                text = "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas."
            msg.reply_text(text,
                           parse_mode=ParseMode.MARKDOWN)
        else:
            if conn:
                text = "Peringatan saat ini disetel untuk *diblokir* pengguna saat melampaui batas pada *{}*.".format(chat_name)
            else:
                text = "Peringatan saat ini disetel untuk *diblokir* pengguna saat melampaui batas."
            msg.reply_text(text,
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return "{} seluruh peringatan, pada {} obrolan.\n" \
           "{} menyaring peringatkan, pada {} obrolan.".format(sql.num_warns(), sql.num_warn_chats(),
                                                      sql.num_warn_filters(), sql.num_warn_filter_chats())


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return "Obrolan ini mempunyai `{}` saringan peringatkan. Dibutuhkan `{}` peringatan " \
           "sebelum pengguna akan mendapatkan *{}*.".format(num_warn_filters, limit, "tendangan" if soft_warn else "pemblokiran")


__help__ = """
 - /warns <userhandle>: dapatkan nomor, dan alasan pengguna peringatan.
 - /warnlist: daftar semua filter peringatan saat ini

*Hanya admin:*
 - /warn <userhandle>: memperingatkan pengguna. Setelah 3 peringatan, pengguna akan dicekal dari grup. Bisa juga digunakan \
sebagai balasan.
 - /resetwarn <userhandle>: mengatur ulang peringatan untuk pengguna. Bisa juga digunakan sebagai balasan.
 - /addwarn <kata kunci> <pesan balasan>: mengatur filter peringatan pada kata kunci tertentu. Jika Anda ingin kata kunci Anda \
menjadi kalimat, mencakup dengan tanda kutip, seperti: `/addwarn "sangat marah" Ini adalah pengguna yang marah`. 
 - /nowarn <keyword>: hentikan filter peringatan
 - /warnlimit <num>: mengatur batas peringatan
 - /strongwarn <on/yes/off/no>: Jika diatur ke on, maka melebihi batas peringatan akan menghasilkan pemblokiran. \
Sedangkan off, hanya akan menendang.
"""

__mod_name__ = "Peringatan"

WARN_HANDLER = CommandHandler("warn", warn_user, pass_args=True)#, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(["resetwarn", "resetwarns", "rmwarn"], reset_warns, pass_args=True)#, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, pass_args=True)#, filters=Filters.group)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter)#, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(["nowarn", "stopwarn"], remove_warn_filter)#, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(["warnlist", "warnfilters"], list_warn_filters)#, filters=Filters.group, admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, pass_args=True)#, filters=Filters.group)
WARN_STRENGTH_HANDLER = CommandHandler("strongwarn", set_warn_strength, pass_args=True)#, filters=Filters.group)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
