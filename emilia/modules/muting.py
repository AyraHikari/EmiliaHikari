import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from emilia.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from emilia.modules.helper_funcs.string_handling import extract_time
from emilia.modules.log_channel import loggable
from emilia.modules.connection import connected


@run_async
@bot_admin
#@can_restrict
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda harus memberi saya nama pengguna untuk membungkam, atau membalas seseorang untuk dibisukan.")
        return ""

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        text = "Dia telah dibisukan pada *{}*! 😆".format(chat_name)
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
        text = "Dia telah dibisukan! 😆"

    if user_id == bot.id:
        message.reply_text("Saya tidak akan membungkam diri saya sendiri!")
        return ""

    check = bot.getChatMember(chat.id, user.id)
    if check['can_restrict_members'] == False:
        message.reply_text("Anda tidak punya hak untuk membatasi seseorang.")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Saya tidak bisa menghentikan seorang admin berbicara!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text(text, parse_mode="markdown")
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>Pengguna:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("Pengguna ini sudah dibungkam!")
    else:
        message.reply_text("Pengguna ini tidak ada dalam obrolan!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda harus memberi saya nama pengguna untuk menyuarakan, atau membalas seseorang untuk disuarakan.")
        return ""

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        text = "Pengguna ini sudah bisa untuk berbicara pada *{}*.".format(chat_name)
        text2 = "Dia telah disuarakan pada *{}*.".format(chat_name)
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
        text = "Pengguna ini sudah bisa untuk berbicara."
        text2 = "Dia telah disuarakan."

    check = bot.getChatMember(chat.id, user.id)
    if check['can_restrict_members'] == False:
        message.reply_text("Anda tidak punya hak untuk membatasi seseorang.")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Ini adalah admin, apa yang Anda harapkan kepada saya?")
            return ""

        elif member.status != 'kicked' and member.status != 'left':
            if member.can_send_messages and member.can_send_media_messages \
                    and member.can_send_other_messages and member.can_add_web_page_previews:
                message.reply_text(text, parse_mode="markdown")
                return ""
            else:
                bot.restrict_chat_member(chat.id, int(user_id),
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_send_other_messages=True,
                                         can_add_web_page_previews=True)
                message.reply_text(text2, parse_mode="markdown")
                return "<b>{}:</b>" \
                       "\n#UNMUTE" \
                       "\n<b>Admin:</b> {}" \
                       "\n<b>Pengguna:</b> {}".format(html.escape(chat.title),
                                                  mention_html(user.id, user.first_name),
                                                  mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("Pengguna ini bahkan tidak dalam obrolan, menyuarakannya tidak akan membuat mereka berbicara lebih dari "
                           "yang sudah mereka lakukan!")

    return ""


@run_async
@bot_admin
#@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return ""

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

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Saya tidak dapat menemukan pengguna ini")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("Saya benar-benar berharap dapat membisukan admin...")
        return ""

    if user_id == bot.id:
        message.reply_text("Saya tidak akan membisukan diri saya sendiri, apakah kamu gila?")
        return ""

    check = bot.getChatMember(chat.id, user.id)
    if check['can_restrict_members'] == False:
        message.reply_text("Anda tidak punya hak untuk membatasi seseorang.")
        return ""

    if not reason:
        message.reply_text("Anda belum menetapkan waktu untuk menonaktifkan pengguna ini!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#BISU SEMENTARA" \
          "\n<b>Admin:</b> {}" \
          "\n<b>Pengguna:</b> {}" \
          "\n<b>Waktu:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Alasan:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            if conn:
                text = "Dibisukan untuk *{}* pada *{}*!".format(time_val, chat_name)
            else:
                text = "Dibisukan untuk *{}*!".format(time_val)
            message.reply_text(text, parse_mode="markdown")
            return log
        else:
            message.reply_text("Pengguna ini sudah dibungkam.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Dibisukan untuk {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Yah sial, aku tidak bisa membisukan pengguna itu.")

    return ""


__help__ = """
*Hanya admin:*
 - /mute <userhandle>: membungkam seorang pengguna. Bisa juga digunakan sebagai balasan, mematikan balasan kepada pengguna.
 - /tmute <userhandle> x(m/h/d): membisukan pengguna untuk x waktu. (via handle, atau membalas). m = menit, h = jam, d = hari.
 - /unmute <userhandle>: batalkan membungkam pengguna. Bisa juga digunakan sebagai balasan, mematikan balasan kepada pengguna.
"""

__mod_name__ = "Mendiamkan"

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True)#, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True)#, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True)#, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
