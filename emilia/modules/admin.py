import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, InlineKeyboardMarkup
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, updater, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.msg_types import get_message_type
from emilia.modules.helper_funcs.misc import build_keyboard_alternate
from emilia.modules.log_channel import loggable
from emilia.modules.connection import connected
from emilia.modules.sql import admin_sql as sql

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

ENUM_FUNC_MAP = {
    'Types.TEXT': dispatcher.bot.send_message,
    'Types.BUTTON_TEXT': dispatcher.bot.send_message,
    'Types.STICKER': dispatcher.bot.send_sticker,
    'Types.DOCUMENT': dispatcher.bot.send_document,
    'Types.PHOTO': dispatcher.bot.send_photo,
    'Types.AUDIO': dispatcher.bot.send_audio,
    'Types.VOICE': dispatcher.bot.send_voice,
    'Types.VIDEO': dispatcher.bot.send_video
}


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
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
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    user_id = extract_user(message, args)
    if not user_id:
        send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna."))
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        send_message(update.effective_message, tl(update.effective_message, "Bagaimana saya ingin menaikan jabatan seseorang yang sudah menjadi admin?"))
        return ""

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa menaikan jabatan diri saya sendiri! Hanya admin yang dapat melakukanya untuk saya."))
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(chat_id, user_id,
                              # can_change_info=bot_member.can_change_info,
                              can_post_messages=bot_member.can_post_messages,
                              can_edit_messages=bot_member.can_edit_messages,
                              can_delete_messages=bot_member.can_delete_messages,
                              can_invite_users=bot_member.can_invite_users,
                              can_restrict_members=bot_member.can_restrict_members,
                              can_pin_messages=bot_member.can_pin_messages,
                              # can_promote_members=bot_member.can_promote_members
                             )
    except BadRequest:
        send_message(update.effective_message, tl(update.effective_message, "Tidak dapat mempromosikan pengguna, mungkin saya bukan admin atau tidak punya izin untuk mempromosikan pengguna."))
        return

    send_message(update.effective_message, tl(update.effective_message, "💖 Berhasil dinaikan jabatannya!"))
    
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>Admin:</b> {}" \
           "\n<b>User:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
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
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    user_id = extract_user(message, args)
    if not user_id:
        send_message(update.effective_message, tl(update.effective_message, "Anda sepertinya tidak mengacu pada pengguna."))
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        send_message(update.effective_message, tl(update.effective_message, "Orang ini MENCIPTAKAN obrolan ini, bagaimana saya menurunkannya?"))
        return ""

    if not user_member.status == 'administrator':
        send_message(update.effective_message, tl(update.effective_message, "Tidak dapat menurunkan jabatan apa yang belum dipromosikan!"))
        return ""

    if user_id == bot.id:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak bisa menurunkan jabatan diri saya sendiri! Hanya admin yang dapat melakukanya untuk saya."))
        return ""

    try:
        bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        send_message(update.effective_message, tl(update.effective_message, "💔 Berhasil diturunkan jabatannya!"))
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>Admin:</b> {}" \
               "\n<b>User:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        send_message(update.effective_message, tl(update.effective_message, "Tidak dapat menurunkan jabatannya. Saya mungkin bukan admin, atau status admin ditunjuk oleh "
                           "orang lain, jadi saya tidak bisa bertindak atas hak mereka!"))
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        if len(args)  <= 1:
            send_message(update.effective_message, tl(update.effective_message, "Gunakan /pin <notify/loud/silent/violent> <link pesan>"))
            return ""
        prev_message = args[1]
        if "/" in prev_message:
            prev_message = prev_message.split("/")[-1]
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
        if update.effective_message.reply_to_message:
            prev_message = update.effective_message.reply_to_message.message_id
        else:
            send_message(update.effective_message, tl(update.effective_message, "Balas pesan untuk pin pesan tersebut pada grup ini"))
            return ""

    is_group = chat.type != "private" and chat.type != "channel"

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'notify' or args[0].lower() == 'loud' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message, disable_notification=is_silent)
            if conn:
                send_message(update.effective_message, tl(update.effective_message, "Saya sudah pin pesan dalam grup {}").format(chat_name))
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        return "<b>{}:</b>" \
               "\n#PINNED" \
               "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
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
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    try:
        bot.unpinChatMessage(chat.id)
        if conn:
            send_message(update.effective_message, tl(update.effective_message, "Saya sudah unpin pesan dalam grup {}").format(chat_name))
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#UNPINNED" \
           "\n<b>Admin:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
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
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if chat.username:
        send_message(update.effective_message, chat.username)
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            send_message(update.effective_message, invitelink)
        else:
            send_message(update.effective_message, tl(update.effective_message, "Saya tidak memiliki akses ke tautan undangan, coba ubah izin saya!"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Saya hanya dapat memberi Anda tautan undangan untuk supergroup dan saluran, maaf!"))


@run_async
def adminlist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

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

    administrators = bot.getChatAdministrators(chat_id)
    text = tl(update.effective_message, "Admin di *{}*:").format(update.effective_chat.title or tl(update.effective_message, "chat ini"))
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = tl(update.effective_message, "☠ Akun Terhapus")
        else:
            name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 👑 Creator:"
            text += "\n` • `{} \n\n 🔱 Admins:".format(name)
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = tl(update.effective_message, "☠ Akun Terhapus")
        else:
            name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "administrator":
            text += "\n` • `{}".format(name)

    try:
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN, quote=False)


@can_pin
@user_admin
@run_async
def permapin(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

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

    text, data_type, content, buttons = get_message_type(message)
    tombol = build_keyboard_alternate(buttons)
    try:
        message.delete()
    except BadRequest:
        pass
    if str(data_type) in ('Types.BUTTON_TEXT', 'Types.TEXT'):
        try:
            sendingmsg = bot.send_message(chat_id, text, parse_mode="markdown",
                                 disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
        except BadRequest:
            bot.send_message(chat_id, tl(update.effective_message, "Teks markdown salah!\nJika anda tidak tahu apa itu markdown, silahkan ketik `/markdownhelp` pada PM."), parse_mode="markdown")
            return
    else:
        sendingmsg = ENUM_FUNC_MAP[str(data_type)](chat_id, content, caption=text, parse_mode="markdown", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
    try:
        bot.pinChatMessage(chat_id, sendingmsg.message_id)
    except BadRequest:
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak punya akses untuk pin pesan!"))


@can_pin
@user_admin
@run_async
def permanent_pin_set(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        if not args:
            get_permapin = sql.get_permapin(chat_id)
            text_maker = tl(update.effective_message, "Permanen pin saat ini di atur: `{}`").format(bool(int(get_permapin)))
            if get_permapin:
                if chat.username:
                    old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
                else:
                    old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
                text_maker += tl(update.effective_message, "\nUntuk menonaktifkan permanen pin: `/permanentpin off`")
                text_maker += tl(update.effective_message, "\n\n[Pesan permanen pin ada disini]({})").format(old_pin)
            send_message(update.effective_message, tl(update.effective_message, text_maker), parse_mode="markdown")
            return ""
        prev_message = args[0]
        if prev_message == "off":
            sql.set_permapin(chat_id, 0)
            send_message(update.effective_message, tl(update.effective_message, "Permanen pin telah di nonaktifkan!"))
            return
        if "/" in prev_message:
            prev_message = prev_message.split("/")[-1]
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
        if update.effective_message.reply_to_message:
            prev_message = update.effective_message.reply_to_message.message_id
        elif len(args) >= 1 and args[0] == "off":
            sql.set_permapin(chat.id, 0)
            send_message(update.effective_message, tl(update.effective_message, "Permanen pin telah di nonaktifkan!"))
            return
        else:
            get_permapin = sql.get_permapin(chat_id)
            text_maker = tl(update.effective_message, "Permanen pin saat ini di atur: `{}`").format(bool(int(get_permapin)))
            if get_permapin:
                if chat.username:
                    old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
                else:
                    old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
                text_maker += tl(update.effective_message, "\nUntuk menonaktifkan permanen pin: `/permanentpin off`")
                text_maker += tl(update.effective_message, "\n\n[Pesan permanen pin ada disini]({})").format(old_pin)
            send_message(update.effective_message, text_maker, parse_mode="markdown")
            return ""

    is_group = chat.type != "private" and chat.type != "channel"

    if prev_message and is_group:
        sql.set_permapin(chat.id, prev_message)
        send_message(update.effective_message, tl(update.effective_message, "Permanent pin berhasil di atur!"))
        return "<b>{}:</b>" \
               "\n#PERMANENT_PIN" \
               "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
def permanent_pin(bot: Bot, update: Update):
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message

    get_permapin = sql.get_permapin(chat.id)
    if get_permapin and not user.id == bot.id:
        try:
            to_del = bot.pinChatMessage(chat.id, get_permapin, disable_notification=True)
        except BadRequest:
            sql.set_permapin(chat.id, 0)
            if chat.username:
                old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
            else:
                old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
            send_message(update.effective_message, tl(update.effective_message, "*Permanen pin error:*\nSaya tidak bisa menyematkan pesan di sini!\nPastikan saya admin dan dapat pin pesan.\n\nPermanen pin di nonaktifkan, [pesan permanen pin lama ada disini]({})").format(old_pin), parse_mode="markdown")
            return

        if to_del:
            try:
                bot.deleteMessage(chat.id, message.message_id+1)
            except BadRequest:
                print("Permanent pin error: cannot delete pin msg")
    


def __chat_settings__(chat_id, user_id):
    administrators = dispatcher.bot.getChatAdministrators(chat_id)
    chat = dispatcher.bot.getChat(chat_id)
    text = "Admin di *{}*:".format(chat.title or "chat ini")
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = tl(user_id, "☠ Akun Terhapus")
        else:
            name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 👑 Creator:"
            text += "\n` • `{} \n\n 🔱 Admin:".format(name)
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = tl(user_id, "☠ Akun Terhapus")
        else:
            name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "administrator":
            text += "\n` • `{}".format(name)
    text += tl(user_id, "\n\nKamu adalah *{}*").format(dispatcher.bot.get_chat_member(chat_id, user_id).status)
    return text


__help__ = "admin_help"

__mod_name__ = "Admin"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)
PERMAPIN_HANDLER = CommandHandler("permapin", permapin, filters=Filters.group)

INVITE_HANDLER = CommandHandler("invitelink", invite, filters=Filters.group)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)

PERMANENT_PIN_SET_HANDLER = CommandHandler("permanentpin", permanent_pin_set, pass_args=True, filters=Filters.group)
PERMANENT_PIN_HANDLER = MessageHandler(Filters.status_update.pinned_message | Filters.user(777000), permanent_pin)

ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "admins"], adminlist)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(PERMAPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(PERMANENT_PIN_SET_HANDLER)
dispatcher.add_handler(PERMANENT_PIN_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
