import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

import emilia.modules.sql.global_bans_sql as sql
from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN, spamfilters
from emilia.modules.helper_funcs.chat_status import user_admin, is_user_admin
from emilia.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.misc import send_to_list
from emilia.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Saya memata-matai, dengan mata kecil saya... perang pengguna sudo! Mengapa kalian saling berpaling? 😱")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH seseorang mencoba untuk memblokir secara global pengguna dukungan! 😄 *mengambil popcorn*")
        return

    if user_id == bot.id:
        message.reply_text("😑 Sangat lucu, mari kita blokir secara global diri saya sendiri? Usaha yang bagus 😒")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Itu bukan pengguna!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Pengguna ini sudah dilarang secara global; Saya akan mengubah alasannya, tetapi Anda belum memberi saya satu...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Pengguna ini sudah gbanned, karena alasan berikut:\n"
                               "<code>{}</code>\n"
                               "Saya telah melakukan dan memperbaruinya dengan alasan baru Anda!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Pengguna ini sudah gbanned, tetapi tidak ada alasan yang ditetapkan; Saya telah melakukan dan memperbaruinya!")

        return

    message.reply_text("*Kristal banned telah mengarah* 😉")

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} melarang secara global pengguna {} "
                 "karena:\n{}".format(mention_html(banner.id, banner.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "Tidak ada alasan yang diberikan"),
                 html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Tidak dapat melarang secara global karena: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Tidak dapat melarang secara global karena: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Melarang secara global selesai!")
    message.reply_text("Orang ini telah dilarang secara global.")


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Itu bukan pengguna!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Pengguna ini tidak dilarang secara global!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Saya akan berikan {} kesempatan kedua, secara global.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} telah menghapus larangan global untuk pengguna {}".format(mention_html(banner.id, banner.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Tidak dapat menghapus larangan secara global karena: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Tidak dapat menghapus larangan secara global karena: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Menghapus larangan global selesai!")

    message.reply_text("Orang ini telah dihapus larangannya.")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Tidak ada pengguna yang dilarang global! Anda lebih baik dari yang saya harapkan...")
        return

    banfile = 'Persetan orang-orang ini.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Alasan: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Berikut adalah daftar pengguna yang saat ini dilarang secara global.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Ini orang jahat, mereka seharusnya tidak ada di sini!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Saya telah mengaktifkan larangan global dalam grup ini. Ini akan membantu melindungi Anda "
                                                "dari spammer, karakter tidak menyenangkan, dan troll terbesar.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Saya telah menonaktifkan larangan global dalam grup ini. Larangan global tidak akan memengaruhi pengguna Anda "
                                                "lagi. Anda akan kurang terlindungi dari troll dan spammer sekalipun")
    else:
        update.effective_message.reply_text("Berikan saya beberapa argumen untuk memilih pengaturan! on/off, yes/no!\n\n"
                                            "Pengaturan Anda saat ini: {}\n"
                                            "Ketika Benar, setiap larangan global yang terjadi juga akan terjadi di grup Anda. "
                                            "Ketika Salah, mereka tidak akan meninggalkan Anda pada belas kasihan yang mungkin dari "
                                            "spammer.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{} pengguna global banned.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Dilarang secara global: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nAlasan: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Obrolan ini memberlakukan *larangan global*: `{}`.".format(sql.does_chat_gban(chat_id))

def __chat_settings_btn__(chat_id, user_id):
    getstatus = sql.does_chat_gban(chat_id)
    if getstatus:
        status = "✅ Aktif"
    else:
        status = "❎ Tidak Aktif"
    button = []
    button.append([InlineKeyboardButton(text=status, callback_data="set_gstats={}".format(chat_id))])
    return button

def GBAN_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button GBAN EDIT".format(user.id))
    chat_id = query.data.split("=")[1]
    isgban = sql.does_chat_gban(chat_id)
    if chat_id:
        button = []
        if isgban:
            sql.disable_gbans(chat_id)
            status = "❎ Tidak Aktif"
        else:
            sql.enable_gbans(chat_id)
            status = "✅ Aktif"
        text = "Obrolan ini memberlakukan *larangan global*: `{}`.".format(status)
        button.append([InlineKeyboardButton(text=status, callback_data="set_gstats={}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)


__help__ = """
*Hanya admin:*
 - /gbanstat <on/off/yes/no>: Akan menonaktifkan efek larangan global pada grup Anda, atau mengembalikan pengaturan Anda saat ini.

Larangan global, juga dikenal sebagai larangan global, digunakan oleh pemilik bot untuk melarang spammer di semua grup. Ini membantu melindungi \
Anda dan grup Anda dengan menghapus spam banjir secepat mungkin. Mereka dapat dinonaktifkan untuk grup Anda dengan memanggil \
/gbanstat
"""

__mod_name__ = "Larangan Global"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)
GBAN_BTNSET_HANDLER = CallbackQueryHandler(GBAN_EDITBTN, pattern=r"set_gstats")

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)
dispatcher.add_handler(GBAN_BTNSET_HANDLER)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
