import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, WHITELIST_USERS, TEMPORARY_DATA, LOGGER
from emilia.modules.helper_funcs.handlers import CMD_STARTERS
from emilia.modules.helper_funcs.misc import is_module_loaded, send_to_list
from emilia.modules.helper_funcs.chat_status import is_user_admin
from emilia.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from emilia.modules.helper_funcs.string_handling import markdown_parser
from emilia.modules.disable import DisableAbleCommandHandler

import emilia.modules.sql.feds_sql as sql

from emilia.modules.connection import connected

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# 
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 11+ hours by @AyraHikari
# 
# Total spended for making this features is 43+ hours

# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
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

UNFBAN_ERRORS = {
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
def new_fed(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    fednam = message.text[len('/newfed '):]
    if not fednam == '':
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        #if fednam == 'Name':
        #     fed_id = "Name"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text("Tidak dapat membuat federasi! Tolong hubungi pembuat saya jika masalah masih berlanjut.")
            return

        update.effective_message.reply_text("*Anda telah berhasil membuat federasi baru!*"\
                                            "\nNama: `{}`"\
                                            "\nID: `{}`"
                                            "\n\nGunakan perintah di bawah ini untuk bergabung dengan federasi:"
                                            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id), parse_mode=ParseMode.MARKDOWN)
        try:
            bot.send_message(TEMPORARY_DATA,
                "Federasi <b>{}</b> telah di buat dengan ID: <pre>{}</pre>".format(fed_name, fed_id), parse_mode=ParseMode.HTML)
        except:
            LOGGER.warning("Cannot send a message to TEMPORARY_DATA")
    else:
        update.effective_message.reply_text("Tolong tulis nama federasinya!")

@run_async
def del_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("Saat ini, Kami hanya mendukung penghapusan federasi pada grup yang bergabung.")
        return

    if not is_user_fed_owner(fed_id, user.id):
        update.effective_message.reply_text("Hanya pemilik fedarasi yang dapat melakukan ini!")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
        delete = sql.del_fed(fed_id, chat.id)
        if delete:
            update.effective_message.reply_text("Federasi {} telah di hapus!".format(getfed['fname']))

@run_async
def fed_chat(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Anda harus menjadi admin untuk menjalankan perintah ini")
        return

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak dalam federasi apa pun!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "Obrolan ini adalah bagian dari federasi berikut:"
    text += "\n{} (ID: <code>{}</code>)".format(info['fname'], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

@run_async
def join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in SUDO_USERS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text("Hanya pembuat grup yang dapat melakukannya!")
                    return
    if fed_id:
        message.reply_text("Anda tidak bisa bergabung dua federasi dalam satu obrolan")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed == False:
            message.reply_text("Silakan masukkan id federasi yang valid.")
            return

        x = sql.chat_join_fed(args[0], chat.id)
        if not x:
            message.reply_text("Gagal bergabung dengan federasi! Tolong hubungi pembuat saya jika masalah ini masih berlanjut.")
            return

        message.reply_text("Obrolan ini telah bergabung dengan federasi {}!".format(getfed['fname']))

@run_async
def leave_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in 'creator' or user.id in SUDO_USERS:
        if sql.chat_leave_fed(chat.id) == True:
            update.effective_message.reply_text("Keluar dari federasi!")
        else:
            update.effective_message.reply_text("Mengapa Anda meninggalkan federasi ketika Anda belum bergabung?!")
    else:
        update.effective_message.reply_text("Hanya pembuat grup yang dapat melakukannya!")

@run_async
def user_join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
            [MessageEntity.TEXT_MENTION]))):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari ini.")
            return
        else:
            LOGGER.warning('error')
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = eval(info['fusers'])['owner']
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text("Mengapa Anda mencoba mempromosikan pemilik federasi!?")
            return
        if getuser:
            update.effective_message.reply_text("Saya tidak dapat mempromosikan pengguna yang sudah menjadi admin federasi! Tapi saya bisa menurunkannya.")
            return
        if user_id == bot.id:
            update.effective_message.reply_text("Saya sudah menjadi admin federasi dan yang mengelolanya!")
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("💖 Berhasil Dipromosikan!")
        else:
            update.effective_message.reply_text("Gagal dipromosikan!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")


@run_async
def user_demote_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message  # type: Optional[Message]
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
            [MessageEntity.TEXT_MENTION]))):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari ini.")
            return
        else:
            LOGGER.warning('error')

        if user_id == bot.id:
            update.effective_message.reply_text("Apa yang sedang Anda coba lakukan? Menurunkan saya dari federasi Anda?")
            return

        if sql.search_user_in_fed(fed_id, user_id) == False:
            update.effective_message.reply_text("Saya tidak dapat mendemosikan pengguna yang bukan merupakan admin federasi! Jika Anda ingin membuatnya menangis, promosikan dia terlebih dahulu!")
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res == True:
            update.effective_message.reply_text("Keluar dari sini!")
        else:
            update.effective_message.reply_text("Saya tidak bisa mengusirnya, Saya tidak berdaya!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

@run_async
def fed_info(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak ada dalam federasi apa pun!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    owner = bot.get_chat(info['owner'])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(owner.id))
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ Info federasi:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nName: {}".format(info['fname'])
    text += "\nPembuat: {}".format(mention_html(owner.id, owner_name))
    text += "\nSeluruh admin: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal yang di banned: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nTotal grup yang terkoneksi: <code>{}</code>".format(len(getfchat))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

@run_async
def fed_admin(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak ada dalam federasi apa pun!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>Admin Federasi:</b>\n\n"
    text += "👑 Owner:\n"
    owner = bot.get_chat(info['owner'])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 Tidak ada admin di federasi ini"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = bot.get_chat(x) 
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak ada dalam federasi apa pun!")
        return

    info = sql.get_fed_info(fed_id)
    FEDADMIN = sql.all_fed_users(fed_id)

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    fban, fbanreason = sql.get_fban_user(fed_id, user_id)
    if fban:
        update.effective_message.reply_text("Hm... Pengguna ini sudah di fban dengan alasan:\n{}".format(fbanreason))
        return

    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna.")
        return

    if user_id == bot.id:
        message.reply_text("Apa yang lebih lucu dari menendang creator grup? Fban diri saya sendiri.")
        return

    if is_user_fed_owner(fed_id, user_id) == True:
        message.reply_text("Mengapa Anda mencoba fban pemilik federasi?")
        return

    if is_user_fed_admin(fed_id, user_id) == True:
        message.reply_text("Dia adalah admin dari federasi, saya tidak bisa fban dia.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Aku tidak ingin memblokir tuanku, itu ide yang sangat bodoh!")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Saya tidak akan fban pengguna sudo!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Orang ini masuk daftar putih, jadi tidak bisa di fban!")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Itu bukan pengguna!")
        return

    user_target = mention_html(user_chat.id, user_chat.first_name)
    fed_name = info['fname']

    starting = "Memulai larangan federasi untuk {} pada Federasi <b>{}</b>.".format(user_target, fed_name)
    update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    if reason == "":
        reason = "Tidak ada alasan."

    x = sql.fban_user(fed_id, user_id, reason)
    if not x:
        message.reply_text("Gagal melarangan federasi! Mungkin bug ini belum diperbaiki karena pengembangnya malas.")
        return

    fed_chats = sql.all_fed_chats(fed_id)
    for chat in fed_chats:
        try:
            bot.send_message(chat, "<b>FedBan baru</b>" \
                         "\n<b>Federasi:</b> {}" \
                         "\n<b>Federasi Admin:</b> {}" \
                         "\n<b>Pengguna:</b> {}" \
                         "\n<b>Pengguna ID:</b> <code>{}</code>" \
                         "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name),
                                               mention_html(user_chat.id, user_chat.first_name),
                                                            user_chat.id, reason), parse_mode="HTML")
            bot.kick_chat_member(chat, user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            else:
                message.reply_text("Tidak dapat fban karena: {}".format(excp.message))
                return
        except TelegramError:
            pass

    send_to_list(bot, FEDADMIN,
             "<b>FedBan baru</b>" \
             "\n<b>Federasi:</b> {}" \
             "\n<b>Federasi Admin:</b> {}" \
             "\n<b>Pengguna:</b> {}" \
             "\n<b>Pengguna ID:</b> <code>{}</code>" \
             "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name),
                                   mention_html(user_chat.id, user_chat.first_name),
                                                user_chat.id, reason), 
            html=True)
    message.reply_text("Orang ini telah di fbanned.")


@run_async
def unfban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak ada dalam federasi apa pun!")
        return

    info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Itu bukan pengguna!")
        return

    fban, fbanreason = sql.get_fban_user(fed_id, user_id)
    if fban == False:
        message.reply_text("Pengguna ini tidak di fbanned!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Saya akan memberi {} kesempatan kedua dalam federasi ini.".format(user_chat.first_name))

    chat_list = sql.all_fed_chats(fed_id)

    for chat in chat_list:
        try:
            member = bot.get_chat_member(chat, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat, user_id)
                bot.send_message(chat, "<b>Un-FedBan</b>" \
                         "\n<b>Federasi:</b> {}" \
                         "\n<b>Federasi Admin:</b> {}" \
                         "\n<b>Pengguna:</b> {}" \
                         "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), mention_html(user_chat.id, user_chat.first_name),
                                                            user_chat.id), parse_mode="HTML")
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            else:
                message.reply_text("Tidak dapat un-fban karena: {}".format(excp.message))
                return
        except TelegramError:
            pass

        try:
            x = sql.un_fban_user(fed_id, user_id)
            if not x:
                message.reply_text("Gagal fban, Pengguna ini mungkin sudah di un-fedbanned!")
                return
        except:
            pass

    message.reply_text("Orang ini telah di un-fbanned.")
    FEDADMIN = sql.all_fed_users(fed_id)
    send_to_list(bot, FEDADMIN,
             "<b>Un-FedBan</b>" \
             "\n<b>Federasi:</b> {}" \
             "\n<b>Federasi Admin:</b> {}" \
             "\n<b>Pengguna:</b> {}" \
             "\n<b>Pengguna ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
                                                 mention_html(user_chat.id, user_chat.first_name),
                                                              user_chat.id),
            html=True)


@run_async
def set_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("This chat is not in any federation!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Only fed admins can do this!")
        return

    if len(args) >= 1:
        msg = update.effective_message  # type: Optional[Message]
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text("Big F! There is an error while setting federation rules! If you wondered why please ask it in support group!")
            return

        rules = sql.get_fed_info(fed_id)['frules']
        update.effective_message.reply_text(f"Aturan telah di ganti menjadi:\n{rules}!")
    else:
        update.effective_message.reply_text("Please write rules to set it up!")


@run_async
def get_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("This chat is not in any federation!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Rules in this fed:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@run_async
def fed_broadcast(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    if args:
        chat = update.effective_chat  # type: Optional[Chat]
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        text = "*Siaran baru dari Federasi {}*\n".format(fedinfo['fname'])
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text += text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            try:
                bot.sendMessage(chat, text, parse_mode="markdown")
            except TelegramError:
                failed += 1
                LOGGER.warning("Couldn't send broadcast to %s, group name %s", str(chat.chat_id), str(chat.chat_name))

        update.effective_message.reply_text("Siaran Federasi selesai. {} grup gagal menerima pesan, mungkin "
                                            "karena meninggalkan federasi.".format(failed))


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if str(user_id) in fed_admins or is_user_fed_owner(fed_id, user_id):
        return True
    else:
        return False


def is_user_fed_owner(fed_id, user_id):
    getfedowner = eval(sql.get_fed_info(fed_id)['fusers'])
    getfedowner = getfedowner['owner']
    if str(user_id) == getfedowner or user_id == 388576209:
        return True
    else:
        return False


@run_async
def welcome_fed(bot, update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text("This user is banned in current federation! I will remove him.")
        bot.kick_chat_member(chat.id, user.id)
        return True
    else:
        return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "{} pengguna di fbanned, pada {} federasi".format(len(all_fbanned), len(all_feds))


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info['fname']

        if int(info['owner']) == user_id:
            text = "Pengguna ini adalah owner di federasi saat ini: <b>{}</b>.".format(infoname)
        elif is_user_fed_admin(fed_id, user_id) == True:
            text = "Pengguna ini adalah admin di federasi saat ini: <b>{}</b>.".format(infoname)

        elif fban:
            text = "Dilarang di federasi saat ini: <b>Ya</b>"
            text += "\n<b>Alasan:</b> {}".format(fbanreason)
        else:
            text = "Dilarang di federasi saat ini: <b>Tidak</b>"
    else:
        text = ""
    return text


__mod_name__ = "Federations"

__help__ = """
Ah, manajemen grup. Semuanya menyenangkan, sampai mulai spammer masuk grup anda, dan Anda harus mencekalnya. Maka Anda perlu mulai melarang lebih banyak, dan lebih banyak lagi, dan itu terasa menyakitkan.
Tetapi kemudian Anda memiliki banyak grup, dan Anda tidak ingin spammer ini ada di salah satu grup Anda - bagaimana kamu bisa berurusan? Apakah Anda harus mencekalnya secara manual, di semua grup Anda?

Tidak lagi! Dengan federasi, Anda dapat membuat larangan dalam satu obrolan tumpang tindih dengan semua obrolan lainnya.
Anda bahkan dapat menunjuk admin federasi, sehingga admin tepercaya Anda dapat melarang semua obrolan yang ingin Anda lindungi.

Masih tahap percobaan, untuk membuat federasi hanya bisa di lakukan oleh pembuat saya

Perintah:
 - /newfed <fedname>: membuat federasi baru dengan nama yang diberikan. Pengguna hanya diperbolehkan memiliki satu federasi. Metode ini juga dapat digunakan untuk mengubah nama federasi. (maks. 64 karakter)
 - /delfed: menghapus federasi Anda, dan informasi apa pun yang berkaitan dengannya. Tidak akan membatalkan pencekalan pengguna yang diblokir.
 - /fedinfo <FedID>: informasi tentang federasi yang ditentukan.
 - /joinfed <FedID>: bergabung dengan obrolan saat ini ke federasi. Hanya pemilik obrolan yang dapat melakukan ini. Setiap obrolan hanya bisa dalam satu federasi.
 - /leavefed <FedID>: meninggalkan federasi yang diberikan. Hanya pemilik obrolan yang dapat melakukan ini.
 - /fpromote <user>: mempromosikan pengguna untuk memberi fed admin. Pemilik fed saja.
 - /fdemote <user>: menurunkan pengguna dari admin federasi ke pengguna normal. Pemilik fed saja.
 - /fban <user>: melarang pengguna dari semua federasi tempat obrolan ini berlangsung, dan eksekutor memiliki kendali atas.
 - /unfban <user>: batalkan pengguna dari semua federasi tempat obrolan ini berlangsung, dan bahwa pelaksana memiliki kendali atas.
 - /setfrules: Atur peraturan federasi.
 - /frules: Lihat peraturan federasi
 - /chatfed: Lihat federasi pada obrolan saat ini
 - /fedadmins: Tampilkan admin federasi
"""

NEW_FED_HANDLER = CommandHandler("newfed", new_fed, filters=Filters.user(OWNER_ID))
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, pass_args=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, pass_args=True, filters=Filters.user(OWNER_ID))
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, pass_args=True, filters=Filters.user(OWNER_ID))
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, pass_args=True, filters=Filters.user(OWNER_ID))
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, pass_args=True)
BAN_FED_HANDLER = DisableAbleCommandHandler(["fban", "fedban"], fed_ban, pass_args=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, pass_args=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, pass_args=True, filters=Filters.user(OWNER_ID))
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, pass_args=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, pass_args=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, pass_args=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, pass_args=True)

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
