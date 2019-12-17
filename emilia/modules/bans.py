import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from emilia import dispatcher, BAN_STICKER, LOGGER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat
from emilia.modules.helper_funcs.extraction import extract_user_and_text
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.log_channel import loggable
from emilia.modules.connection import connected

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message


@run_async
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    currentchat = update.effective_chat  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

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
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""

    if not user_id:
        send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna."))
        return ""

    try:
        if conn:
            member = bot.getChatMember(chat_id, user_id)
        else:
            member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            if conn:
                text = tl(update.effective_message, "Saya tidak dapat menemukan pengguna ini pada *{}* 😣").format(chat_name)
            else:
                text = tl(update.effective_message, "Saya tidak dapat menemukan pengguna ini 😣")
            send_message(update.effective_message, text, parse_mode="markdown")
            return ""
        else:
            raise

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak akan BAN diri saya sendiri, apakah kamu gila? 😠"))
        return ""

    if is_user_ban_protected(chat, user_id, member):
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa banned orang ini karena dia adalah admin 😒"))
        return ""

    if member['can_restrict_members'] == False:
        if conn:
            text = tl(update.effective_message, "Anda tidak punya hak untuk membatasi seseorang pada *{}*.").format(chat_name)
        else:
            text = tl(update.effective_message, "Anda tidak punya hak untuk membatasi seseorang.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        if conn:
            bot.kickChatMember(chat_id, user_id)
            bot.send_sticker(currentchat.id, BAN_STICKER)  # banhammer marie sticker
            send_message(update.effective_message, tl(update.effective_message, "Terbanned pada *{}*! 😝").format(chat_name), parse_mode="markdown")
        else:
            chat.kick_member(user_id)
            if message.text.split(None, 1)[0][1:] == "sban":
                update.effective_message.delete()
            else:
                bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
                send_message(update.effective_message, tl(update.effective_message, "Terbanned! 😝"))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            send_message(update.effective_message, tl(update.effective_message, "Terbanned! 😝"), quote=False)
            return log
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR membanned pengguna %s di obrolan %s (%s) disebabkan oleh %s", user_id, chat.title, chat.id,
                             excp.message)
            send_message(update.effective_message, tl(update.effective_message, "Yah sial, aku tidak bisa banned pengguna itu 😒"))

    return ""


@run_async
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    currentchat = update.effective_chat  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

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
    if check.status == 'member':
        if conn:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di *{}*! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""
    else:
        if check['can_restrict_members'] == False:
            if conn:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di *{}*! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
            else:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
            send_message(update.effective_message, text, parse_mode="markdown")
            return ""

    if not user_id:
        send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna."))
        return ""

    try:
        if conn:
            member = bot.getChatMember(chat_id, user_id)
        else:
            member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat menemukan pengguna ini 😣"))
            return ""
        else:
            raise

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak akan BAN diri saya sendiri, apakah kamu gila? 😠"))
        return ""

    if is_user_ban_protected(chat, user_id, member):
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa banned orang ini karena dia adalah admin 😒"))
        return ""

    if member['can_restrict_members'] == False:
        send_message(update.effective_message, tl(update.effective_message, "Anda tidak punya hak untuk membatasi seseorang."))
        return ""

    if not reason:
        send_message(update.effective_message, tl(update.effective_message, "Anda belum menetapkan waktu untuk banned pengguna ini!"))
        return ""
    
    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""
        
        bantime = extract_time(message, time_val)
        
        if not bantime:
            return ""

    log = "<b>{}:</b>" \
          "\n#TEMPBAN" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name),
                                     member.user.id,
                                     time_val)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        if conn:
            bot.kickChatMember(chat_id, user_id, until_date=bantime)
            bot.send_sticker(currentchat.id, BAN_STICKER)  # banhammer marie sticker
            send_message(update.effective_message, tl(update.effective_message, "Banned! Pengguna diblokir untuk *{}* pada *{}*.").format(time_val, chat_name), parse_mode="markdown")
        else:
            chat.kick_member(user_id, until_date=bantime)
            bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
            send_message(update.effective_message, tl(update.effective_message, "Banned! Pengguna diblokir untuk {}.").format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            send_message(update.effective_message, tl(update.effective_message, "Banned! Pengguna diblokir untuk {}.").format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            send_message(update.effective_message, tl(update.effective_message, "Yah sial, aku tidak bisa menendang pengguna itu 😒"))

    return ""


@run_async
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    currentchat = update.effective_chat  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna."))
        return ""

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
    if check.status == 'member':
        if conn:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""
    else:
        if check['can_restrict_members'] == False:
            if conn:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di *{}*! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
            else:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
            send_message(update.effective_message, text, parse_mode="markdown")
            return ""

    if not user_id:
        return ""

    try:
        if conn:
            member = bot.getChatMember(chat_id, user_id)
        else:
            member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat menemukan pengguna ini 😣"))
            return ""
        else:
            raise

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak akan menendang diri saya sendiri, apakah kamu gila? 😠"))
        return ""

    if is_user_ban_protected(chat, user_id):
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa menendang orang ini karena dia adalah admin 😒"))
        return ""

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Yahhh aku tidak akan melakukan itu 😝"))
        return ""

    check = bot.getChatMember(chat.id, user.id)
    if check['can_restrict_members'] == False:
        send_message(update.effective_message, tl(update.effective_message, "Anda tidak punya hak untuk membatasi seseorang."))
        return ""

    if conn:
        res = bot.unbanChatMember(chat_id, user_id)  # unban on current user = kick
    else:
        res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        if conn:
            bot.send_sticker(currentchat.id, BAN_STICKER)  # banhammer marie sticker
            text = tl(update.effective_message, "Tertendang pada *{}*! 😝").format(chat_name)
            send_message(update.effective_message, text, parse_mode="markdown")
        else:
            if message.text.split(None, 1)[0][1:] == "skick":
                update.effective_message.delete()
            else:
                bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
                text = tl(update.effective_message, "Tertendang! 😝")
                send_message(update.effective_message, text, parse_mode="markdown")
        log = "<b>{}:</b>" \
              "\n#KICKED" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name),
                                                           member.user.id)
        log += "\n<b>Reason:</b> {}".format(reason)

        return log

    else:
        send_message(update.effective_message, tl(update.effective_message, "Yah sial, aku tidak bisa menendang pengguna itu 😒"))

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        send_message(update.effective_message, tl(update.effective_message, "Saya berharap saya bisa... tetapi Anda seorang admin 😒"))
        return

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        send_message(update.effective_message, tl(update.effective_message, "Tidak masalah 😊"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Hah? Aku tidak bisa 🙄"))


@run_async
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

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

    if not user_id:
        return ""

    check = bot.getChatMember(chat_id, bot.id)
    if check.status == 'member':
        if conn:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
        else:
            text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
        send_message(update.effective_message, text, parse_mode="markdown")
        return ""
    else:
        if check['can_restrict_members'] == False:
            if conn:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di {}! Pastikan saya admin dan dapat menunjuk admin baru.").format(chat_name)
            else:
                text = tl(update.effective_message, "Saya tidak bisa membatasi orang di sini! Pastikan saya admin dan dapat menunjuk admin baru.")
            send_message(update.effective_message, text, parse_mode="markdown")
            return ""

    try:
        if conn:
            member = bot.getChatMember(chat_id, user_id)
        else:
            member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat menemukan pengguna ini"))
            return ""
        else:
            raise

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Bagaimana saya akan unban diri saya sendiri jika saya tidak ada di sini...? 🤔"))
        return ""

    if is_user_in_chat(chat, user_id):
        send_message(update.effective_message, tl(update.effective_message, "Mengapa Anda mencoba unban seseorang yang sudah ada di obrolan? 😑"))
        return ""

    check = bot.getChatMember(chat.id, user.id)
    if check['can_restrict_members'] == False:
        send_message(update.effective_message, tl(update.effective_message, "Anda tidak punya hak untuk membatasi seseorang."))
        return ""

    if conn:
        bot.unbanChatMember(chat_id, user_id)
        send_message(update.effective_message, tl(update.effective_message, "Ya, pengguna ini dapat bergabung pada {}! 😁").format(chat_name))
    else:
        chat.unban_member(user_id)
        send_message(update.effective_message, tl(update.effective_message, "Ya, pengguna ini dapat bergabung! 😁"))

    log = "<b>{}:</b>" \
          "\n#UNBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    return log


__help__ = "bans_help"

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler(["ban", "sban"], ban, pass_args=True)#, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True)#, filters=Filters.group)
KICK_HANDLER = CommandHandler(["kick", "skick"], kick, pass_args=True)#, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True)#, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
