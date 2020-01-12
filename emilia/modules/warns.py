import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html, escape_markdown

from emilia import dispatcher, BAN_STICKER, spamfilters, OWNER_ID
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

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

WARN_HANDLER_GROUP = 9


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None, conn=False) -> str:
    if is_user_admin(chat, user.id):
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = tl(chat.id, "Filter peringatan otomatis.")

    limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if not soft_warn:
            if not warn_mode:
                chat.unban_member(user.id)
                reply = tl(chat.id, "{} peringatan, {} telah ditendang!").format(limit, mention_html(user.id, user.first_name))
            elif warn_mode == 1:
                chat.unban_member(user.id)
                reply = tl(chat.id, "{} peringatan, {} telah ditendang!").format(limit, mention_html(user.id, user.first_name))
            elif warn_mode == 2:
                chat.kick_member(user.id)
                reply = tl(chat.id, "{} peringatan, {} telah diblokir!").format(limit, mention_html(user.id, user.first_name))
            elif warn_mode == 3:
                message.bot.restrict_chat_member(chat.id, user.id, can_send_messages=False)
                reply = tl(chat.id, "{} peringatan, {} telah dibisukan!").format(limit, mention_html(user.id, user.first_name))
        else:
            chat.kick_member(user.id)
            reply = tl(chat.id, "{} peringatan, {} telah diblokir!").format(limit, mention_html(user.id, user.first_name))
            
        for warn_reason in reasons:
            reply += "\n - {}".format(html.escape(warn_reason))

        message.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        log_reason = "<b>{}:</b>" \
                     "\n#WARN_BAN" \
                     "\n<b>Admin:</b> {}" \
                     "\n<b>User:</b> {} (<code>{}</code>)" \
                     "\n<b>Reason:</b> {}"\
                     "\n<b>Counts:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(tl(chat.id, "Hapus peringatan"), callback_data="rm_warn({})".format(user.id)), InlineKeyboardButton(tl(chat.id, "Peraturan"), url="t.me/{}?start={}".format(dispatcher.bot.username, chat.id))]])

        if num_warns+1 == limit:
            if not warn_mode:
                action_mode = tl(chat.id, "tendang")
            elif warn_mode == 1:
                action_mode = tl(chat.id, "tendang")
            elif warn_mode == 2:
                action_mode = tl(chat.id, "blokir")
            elif warn_mode == 3:
                action_mode = tl(chat.id, "bisukan")
            reply = tl(chat.id, "{} punya {}/{} peringatan... Jika anda di peringati lagi maka kamu akan di {}!").format(mention_html(user.id, user.first_name), num_warns, limit, action_mode)
        else:
            reply = tl(chat.id, "{} punya {}/{} peringatan... Hati-hati!").format(mention_html(user.id, user.first_name), num_warns, limit)
        if reason:
            reply += tl(chat.id, "\nAlasan pada peringatan terakhir:\n{}").format(html.escape(reason))

        log_reason = "<b>{}:</b>" \
                     "\n#WARN" \
                     "\n<b>Admin:</b> {}" \
                     "\n<b>User:</b> {} (<code>{}</code>)" \
                     "\n<b>Reason:</b> {}"\
                     "\n<b>Counts:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name),
                                                                  user.id, reason, num_warns, limit)

    try:
        if conn:
            message.bot.sendMessage(chat.id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            message.bot.sendMessage(chat.id, reply, reply_to_message_id=message.message_id, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        #send_message(update.effective_message, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            if conn:
                message.bot.sendMessage(chat.id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            else:
                try:
                    message.bot.sendMessage(chat.id, reply, reply_to_message_id=message.message_id, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
                except BadRequest:
                    message.bot.sendMessage(chat.id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
            #send_message(update.effective_message, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
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
                tl(update.effective_message, "Peringatkan dihapus oleh {}.").format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return "<b>{}:</b>" \
                   "\n#UNWARN" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                mention_html(user.id, user.first_name),
                                                                mention_html(user_member.user.id, user_member.user.first_name),
                                                                user_member.user.id)
        else:
            update.effective_message.edit_text(
            tl(update.effective_message, "Pengguna sudah tidak memiliki peringatan.").format(mention_html(user.id, user.first_name)),
            parse_mode=ParseMode.HTML)
            
    return ""


@run_async
@user_admin
#@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    check = bot.getChatMember(chat_id, bot.id)
    if check.status == 'member' or check['can_restrict_members'] == False:
        if conn:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya sudah menjadi admin.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya sudah menjadi admin.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""

    if user_id:
        if conn:
            warning = warn(chat.get_member(user_id).user, chat, reason, message, warner, conn=True)
            send_message(update.effective_message, tl(update.effective_message, "Saya sudah memperingatinya pada grup *{}*").format(chat_name), parse_mode="markdown")
            return warning
        else:
            if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
                return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
            else:
                return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        send_message(update.effective_message, tl(update.effective_message, "Tidak ada pengguna yang ditunjuk!"))
    return ""


@run_async
@user_admin
#@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    check = bot.getChatMember(chat_id, bot.id)
    if check.status == 'member' or check['can_restrict_members'] == False:
        if conn:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya sudah menjadi admin.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya sudah menjadi admin.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""
    
    if user_id:
        sql.reset_warns(user_id, chat.id)
        if conn:
            send_message(update.effective_message, tl(update.effective_message, "Peringatan telah disetel ulang pada *{}*!").format(chat_name), parse_mode="markdown")
        else:
            send_message(update.effective_message, tl(update.effective_message, "Peringatan telah disetel ulang!"))
        warned = chat.get_member(user_id).user
        return "<b>{}:</b>" \
               "\n#RESETWARNS" \
               "\n<b>Admin:</b> {}" \
               "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name),
                                                            mention_html(warned.id, warned.first_name),
                                                            warned.id)
    else:
        send_message(update.effective_message, tl(update.effective_message, "Tidak ada pengguna yang ditunjuk!"))
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)

        if reasons:
            if conn:
                text = tl(update.effective_message, "Pengguna ini memiliki {}/{} peringatan pada *{}*, untuk alasan berikut:").format(num_warns, limit, chat_name)
            else:
                text = tl(update.effective_message, "Pengguna ini memiliki {}/{} peringatan, untuk alasan berikut:").format(num_warns, limit)
            for reason in reasons:
                text += "\n - {}".format(reason)

            msgs = split_message(text)
            for msg in msgs:
                send_message(update.effective_message, msg, parse_mode="markdown")
        else:
            if conn:
                send_message(update.effective_message, 
                    tl(update.effective_message, "Pengguna ini memiliki {}/{} peringatan pada *{}*, tetapi tidak ada alasan untuk itu.").format(num_warns, limit, chat_name), parse_mode="markdown")
            else:
                send_message(update.effective_message, 
                    tl(update.effective_message, "Pengguna ini memiliki {}/{} peringatan, tetapi tidak ada alasan untuk itu.").format(num_warns, limit))
    else:
        if conn:
            send_message(update.effective_message, tl(update.effective_message, "Pengguna ini belum mendapatkan peringatan apa pun pada *{}*!").format(chat_name), parse_mode="markdown")
        else:
            send_message(update.effective_message, tl(update.effective_message, "Pengguna ini belum mendapatkan peringatan apa pun!"))


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
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
        text = tl(update.effective_message, "Peringatkan handler yang ditambahkan untuk '{}' pada *{}*!").format(keyword, chat_name)
    else:
        text = tl(update.effective_message, "Peringatkan handler yang ditambahkan untuk '{}'!").format(keyword)
    send_message(update.effective_message, text, parse_mode="markdown")
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
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
            text = tl(update.effective_message, "Tidak ada filter peringatan aktif di *{}*!").format(chat_name)
        else:
            text = tl(update.effective_message, "Tidak ada filter peringatan aktif di sini!")
        send_message(update.effective_message, text)
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
            text = tl(update.effective_message, "Ya, saya akan berhenti memperingatkan orang-orang untuk {} pada *{}*.").format(success, chat_name)
        else:
            text = tl(update.effective_message, "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.").format(success)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop
    elif inwarn == 0:
        if conn:
            text = tl(update.effective_message, "Gagal menghapus filter warn untuk {} pada *{}*.").format(fail, chat_name)
        else:
            text = tl(update.effective_message, "Gagal menghapus filter warn untuk {}.").format(fail)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop
    else:
        if conn:
            text = tl(update.effective_message, "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.\nDan gagal menghapus filter warn untuk {}.\nPada *{}*").format(success, fail, chat_name)
        else:
            text = tl(update.effective_message, "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.\nDan gagal menghapus filter warn untuk {}.").format(success, fail)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
        raise DispatcherHandlerStop

    """
    if not chat_filters:
        send_message(update.effective_message, "Tidak ada filter peringatan aktif di sini!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
                send_message(update.effective_message, "Ya, saya akan berhenti memperingatkan orang-orang untuk {}.".format(to_remove))
                raise DispatcherHandlerStop
    """

    if conn:
        text = tl(update.effective_message, "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif pada *{}*.")
    else:
        text = tl(update.effective_message, "Itu bukan filter peringatan saat ini - jalankan /warnlist untuk semua filter peringatan aktif.")
    send_message(update.effective_message, text, parse_mode="markdown")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        if conn:
            text = tl(update.effective_message, "Tidak ada filter peringatan aktif di *{}*!").format(chat_name)
        else:
            text = tl(update.effective_message, "Tidak ada filter peringatan aktif di sini!")
        send_message(update.effective_message, text, parse_mode="markdown")
        return

    filter_list = tl(update.effective_message, "CURRENT_WARNING_FILTER_STRING")
    if conn:
        filter_list = filter_list.replace(tl(update.effective_message, 'obrolan ini'), tl(update.effective_message, 'obrolan *{}*').format(chat_name))
    for keyword in all_handlers:
        entry = " - {}\n".format(html.escape(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            send_message(update.effective_message, filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == tl(update.effective_message, "CURRENT_WARNING_FILTER_STRING"):
        send_message(update.effective_message, filter_list, parse_mode=ParseMode.HTML)


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
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                send_message(update.effective_message, tl(update.effective_message, "Batas peringatan minimum adalah 3!"))
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                if conn:
                    text = tl(update.effective_message, "Diperbarui batas untuk diperingatkan {} pada *{}*").format(args[0], chat_name)
                else:
                    text = tl(update.effective_message, "Diperbarui batas untuk diperingatkan {}").format(args[0])
                send_message(update.effective_message, text, parse_mode="markdown")
                return "<b>{}:</b>" \
                       "\n#SET_WARN_LIMIT" \
                       "\n<b>Admin:</b> {}" \
                       "\nSet the warn limit to <code>{}</code>".format(html.escape(chat.title),
                                                                        mention_html(user.id, user.first_name), args[0])
        else:
            send_message(update.effective_message, tl(update.effective_message, "Beri aku angkanya!"))
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
        if conn:
            text = tl(update.effective_message, "Batas peringatan saat ini adalah {} pada *{}*").format(limit, chat_name)
        else:
            text = tl(update.effective_message, "Batas peringatan saat ini adalah {}").format(limit)
        send_message(update.effective_message, text, parse_mode="markdown")
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
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
            send_message(update.effective_message, text, parse_mode="markdown")
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
            send_message(update.effective_message, text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Telah menonaktifkan peringatan kuat. Pengguna hanya akan ditendang.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            send_message(update.effective_message, "Saya hanya mengerti on/yes/no/off!")
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
        if soft_warn:
            if conn:
                text = "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas pada *{}*.".format(chat_name)
            else:
                text = "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas."
            send_message(update.effective_message, text,
                           parse_mode=ParseMode.MARKDOWN)
        else:
            if conn:
                text = "Peringatan saat ini disetel untuk *diblokir* pengguna saat melampaui batas pada *{}*.".format(chat_name)
            else:
                text = "Peringatan saat ini disetel untuk *diblokir* pengguna saat melampaui batas."
            send_message(update.effective_message, text,
                           parse_mode=ParseMode.MARKDOWN)
    return ""


@run_async
@user_admin
def set_warn_mode(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
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
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() in ("kick", "soft"):
            sql.set_warn_mode(chat.id, 1)
            if conn:
                text = tl(update.effective_message, "Terlalu banyak peringatan sekarang akan menghasilkan tendangan pada *{}*! Pengguna akan dapat bergabung lagi.").format(chat_name)
            else:
                text = tl(update.effective_message, "Terlalu banyak peringatan sekarang akan menghasilkan tendangan! Pengguna akan dapat bergabung lagi.")
            send_message(update.effective_message, text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Has changed the final warning to kick.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[0].lower() in ("ban", "banned", "hard"):
            sql.set_warn_mode(chat.id, 2)
            if conn:
                text = tl(update.effective_message, "Terlalu banyak peringatan akan menghasilkan blokir pada *{}*!").format(chat_name)
            else:
                text = tl(update.effective_message, "Terlalu banyak peringatan akan menghasilkan blokir!")
            send_message(update.effective_message, text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Has changed the final warning to banned.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        elif args[0].lower() in ("mute"):
            sql.set_warn_mode(chat.id, 3)
            if conn:
                text = tl(update.effective_message, "Terlalu banyak peringatan akan menghasilkan bisukan pada *{}*!").format(chat_name)
            else:
                text = tl(update.effective_message, "Terlalu banyak peringatan akan menghasilkan bisukan!")
            send_message(update.effective_message, text, parse_mode="markdown")
            return "<b>{}:</b>\n" \
                   "<b>Admin:</b> {}\n" \
                   "Has changed the final warning to mute.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            send_message(update.effective_message, tl(update.effective_message, "Saya hanya mengerti kick/ban/mute!"))
    else:
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat.id)
        if not soft_warn:
            if not warn_mode:
                if conn:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas pada *{}*.").format(chat_name)
                else:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas.")
            elif warn_mode == 1:
                if conn:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas pada *{}*.").format(chat_name)
                else:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *tendangan* pengguna saat melampaui batas.")
            elif warn_mode == 2:
                if conn:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *blokir* pengguna saat melampaui batas pada *{}*.").format(chat_name)
                else:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *blokir* pengguna saat melampaui batas.")
            elif warn_mode == 3:
                if conn:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *bisukan* pengguna saat melampaui batas pada *{}*.").format(chat_name)
                else:
                    text = tl(update.effective_message, "Peringatan saat ini disetel ke *bisukan* pengguna saat melampaui batas.")
            send_message(update.effective_message, text,
                           parse_mode=ParseMode.MARKDOWN)
        else:
            if conn:
                text = tl(update.effective_message, "Peringatan saat ini disetel untuk *blokir* pengguna saat melampaui batas pada *{}*.").format(chat_name)
            else:
                text = tl(update.effective_message, "Peringatan saat ini disetel untuk *blokir* pengguna saat melampaui batas.")
            send_message(update.effective_message, text,
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return tl(OWNER_ID, "{} seluruh peringatan, pada {} obrolan.\n" \
           "{} menyaring peringatkan, pada {} obrolan.").format(sql.num_warns(), sql.num_warn_chats(),
                                                      sql.num_warn_filters(), sql.num_warn_filter_chats())


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
    return tl(user_id, "Obrolan ini mempunyai `{}` saringan peringatkan. Dibutuhkan `{}` peringatan " \
           "sebelum pengguna akan mendapatkan *{}*.").format(num_warn_filters, limit, "tendangan" if soft_warn else "pemblokiran")

"""
def __chat_settings_btn__(chat_id, user_id):
    limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
    button = []
    button.append([InlineKeyboardButton(text="➖", callback_data="set_wlim=-|{}".format(chat_id)),
            InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
            InlineKeyboardButton(text="➕", callback_data="set_wlim=+|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="{}".format("❎ Tendang" if soft_warn else "⛔️ Blokir"), callback_data="set_wlim=exec|{}".format(chat_id))])
    return button

def WARN_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button WARN EDIT".format(user.id))
    qdata = query.data.split("=")[1].split("|")[0]
    chat_id = query.data.split("|")[1]
    if qdata == "?":
        bot.answerCallbackQuery(query.id, "Batas dari peringatan. Jika peringatan melewati batas maka akan di eksekusi.", show_alert=True)
    if qdata == "-":
        button = []
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
        limit = int(limit)-1
        if limit <= 2:
            bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 3", show_alert=True)
            return
        sql.set_warn_limit(chat_id, int(limit))
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Peringatan*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal peringatan telah di setel menjadi `{}`. Dibutuhkan `{}` peringatan " \
           "sebelum pengguna akan mendapatkan *{}*.".format(limit, limit, "tendangan" if soft_warn else "pemblokiran")
        button.append([InlineKeyboardButton(text="➖", callback_data="set_wlim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_wlim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format("❎ Tendang" if soft_warn else "⛔️ Blokir"), callback_data="set_wlim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if qdata == "+":
        button = []
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
        limit = int(limit)+1
        if limit <= 0:
            bot.answerCallbackQuery(query.id, "Batas limit Tidak boleh kurang dari 0", show_alert=True)
            return
        sql.set_warn_limit(chat_id, int(limit))
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Peringatan*:\n\n".format(escape_markdown(chat.title))
        text += "Batas maksimal peringatan telah di setel menjadi `{}`. Dibutuhkan `{}` peringatan " \
           "sebelum pengguna akan mendapatkan *{}*.".format(limit, limit, "tendangan" if soft_warn else "pemblokiran")
        button.append([InlineKeyboardButton(text="➖", callback_data="set_wlim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_wlim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format("❎ Tendang" if soft_warn else "⛔️ Blokir"), callback_data="set_wlim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if qdata == "exec":
        button = []
        limit, soft_warn, warn_mode = sql.get_warn_setting(chat_id)
        if soft_warn:
            exc = "Blokir"
            sql.set_warn_strength(chat_id, False)
            soft_warn = False
        else:
            exc = "Tendang"
            sql.set_warn_strength(chat_id, True)
            soft_warn = True
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Peringatan*:\n\n".format(escape_markdown(chat.title))
        text += "Pengguna akan di `{}` jika sudah diluar batas peringatan. Dibutuhkan `{}` peringatan " \
           "sebelum pengguna akan mendapatkan *{}*.".format(exc, limit, "tendangan" if soft_warn else "pemblokiran")
        button.append([InlineKeyboardButton(text="➖", callback_data="set_wlim=-|{}".format(chat_id)),
                InlineKeyboardButton(text="Limit {}".format(limit), callback_data="set_wlim=?|{}".format(chat_id)),
                InlineKeyboardButton(text="➕", callback_data="set_wlim=+|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="{}".format("❎ Tendang" if soft_warn else "⛔️ Blokir"), callback_data="set_wlim=exec|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
"""


__help__ = "warns_help"

__mod_name__ = "Warnings"

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
WARN_MODE_HANDLER = CommandHandler("warnmode", set_warn_mode, pass_args=True)
# WARN_BTNSET_HANDLER = CallbackQueryHandler(WARN_EDITBTN, pattern=r"set_wlim")

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_MODE_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
# dispatcher.add_handler(WARN_BTNSET_HANDLER)
