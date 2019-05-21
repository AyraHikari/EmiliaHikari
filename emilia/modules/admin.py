import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from emilia import dispatcher, updater, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.log_channel import loggable
from emilia.modules.connection import connected


@run_async
#@bot_admin
#@can_promote
#@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("Bagaimana saya ingin menaikan jabatan seseorang yang sudah menjadi admin?")
        return ""

    if user_id == bot.id:
        message.reply_text("Saya tidak bisa menaikan jabatan diri saya sendiri! Hanya admin yang dapat melakukanya untuk saya.")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

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

    message.reply_text("💖 Berhasil dinaikan jabatannya!")
    
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>Admin:</b> {}" \
           "\n<b>Pengguna:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
#@bot_admin
#@can_promote
#@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("Orang ini MENCIPTAKAN obrolan ini, bagaimana saya menurunkannya?")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("Tidak dapat menurunkan jabatan apa yang tidak dipromosikan!")
        return ""

    if user_id == bot.id:
        message.reply_text("Saya tidak bisa menurunkan jabatan diri saya sendiri! Hanya admin yang dapat melakukanya untuk saya.")
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
        message.reply_text("💔 Berhasil diturunkan jabatannya!")
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>Admin:</b> {}" \
               "\n<b>Pengguna:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("Tidak dapat menurunkan jabatannya. Saya mungkin bukan admin, atau status admin ditunjuk oleh "
                           "orang lain, jadi saya tidak bisa bertindak atas hak mereka!")
        return ""


@run_async
#@bot_admin
#@can_pin
#@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        if len(args)  <= 1:
            update.effective_message.reply_text("Gunakan /pin <notify/loud/silent/violent> <link pesan>")
            return ""
        prev_message = args[1]
        if "/" in prev_message:
            prev_message = prev_message.split("/")[-1]
    else:
        if update.effective_message.chat.type == "private":
            update.effective_message.reply_text("Anda bisa lakukan command ini pada grup, bukan pada PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
        prev_message = update.effective_message.reply_to_message.message_id

    is_group = chat.type != "private" and chat.type != "channel"

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'notify' or args[0].lower() == 'loud' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message, disable_notification=is_silent)
            if conn:
                update.effective_message.reply_text("Saya sudah pin pesan dalam grup {}".format(chat_name))
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
#@bot_admin
#@can_pin
#@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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
        bot.unpinChatMessage(chat.id)
        if conn:
            update.effective_message.reply_text("Saya sudah unpin pesan dalam grup {}".format(chat_name))
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
#@bot_admin
#@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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

    if chat.username:
        update.effective_message.reply_text(chat.username)
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text("Saya tidak memiliki akses ke tautan undangan, coba ubah izin saya!")
    else:
        update.effective_message.reply_text("Saya hanya dapat memberi Anda tautan undangan untuk supergroup dan saluran, maaf!")


@run_async
def adminlist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")

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

    administrators = bot.getChatAdministrators(chat_id)
    text = "Admin di *{}*:".format(update.effective_chat.title or "chat ini")
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = "[☠ Akun Terhapus](tg://user?id={})".format(user.id)
        else:
            name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 👑 Creator:"
            text += "\n` • `{} \n\n 🔱 Admin:".format(name)
    for admin in administrators:
        user = admin.user
        status = admin.status
        if user.first_name == '':
            name = "[☠️ Akun Terhapus](tg://user?id={})".format(user.id)
        else:
            name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        #if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "administrator":
            text += "\n` • `{}".format(name)

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __chat_settings__(chat_id, user_id):
    return "Kamu adalah *admin*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
 - /adminlist | /admins: daftar admin dalam obrolan

*Hanya admin:*
 - /pin: diam-diam pin pesan yang dibalas - tambahkan 'loud' atau 'notify' untuk memberikan notif kepada pengguna.
 - /unpin: buka pin pesan yang saat ini disematkan
 - /invitelink: dapatkan tautan undangan
 - /promote: mempromosikan pengguna yang dibalas
 - /demote: demosikan pengguna yang dibalas
"""

__mod_name__ = "Admin"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True)
UNPIN_HANDLER = CommandHandler("unpin", unpin)

INVITE_HANDLER = CommandHandler("invitelink", invite)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True)

ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "admins"], adminlist)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
