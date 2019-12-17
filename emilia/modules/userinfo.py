import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import emilia.modules.sql.userinfo_sql as sql
from emilia import dispatcher, SUDO_USERS, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    message = update.effective_message  # type: Optional[Message]
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        send_message(update.effective_message, "*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        send_message(update.effective_message, username + tl(update.effective_message, " belum mengatur pesan info tentang diri mereka!"))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Anda belum mengatur pesan info tentang diri Anda!"))


@run_async
def set_about_me(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            send_message(update.effective_message, tl(update.effective_message, "Info Anda Diperbarui!"))
        else:
            send_message(update.effective_message, 
                tl(update.effective_message, "Info Anda harus di bawah {} karakter! Kamu punya {}.").format(MAX_MESSAGE_LENGTH // 4, len(info[1])))


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        send_message(update.effective_message, "*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        send_message(update.effective_message, tl(update.effective_message, "{} belum memiliki pesan tentang dirinya sendiri!").format(username))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Anda belum memiliki bio set tentang diri Anda!"))


@run_async
def set_about_bio(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    message = update.effective_message  # type: Optional[Message]
    sender = update.effective_user  # type: Optional[User]
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            send_message(update.effective_message, tl(update.effective_message, "Ha, Anda tidak dapat mengatur bio Anda sendiri! Anda berada di bawah belas kasihan orang lain di sini..."))
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            send_message(update.effective_message, tl(update.effective_message, "Umm ... yah, saya hanya mempercayai pengguna sudo untuk mengatur bio saya."))
            return

        text = message.text
        bio = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                send_message(update.effective_message, tl(update.effective_message, "Bio {} diperbarui!").format(repl_message.from_user.first_name))
            else:
                send_message(update.effective_message, 
                    tl(update.effective_message, "Biografi harus di bawah {} karakter! Anda mencoba mengatur {}.").format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Balas pesan seseorang untuk mengatur bio mereka!"))


def __user_info__(user_id, chat_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return tl(chat_id, "<b>Tentang pengguna:</b>\n{me}\n<b>Apa yang orang lain katakan:</b>\n{bio}").format(me=me, bio=bio)
    elif bio:
        return tl(chat_id, "<b>Apa yang orang lain katakan:</b>\n{bio}\n").format(me=me, bio=bio)
    elif me:
        return tl(chat_id, "<b>Tentang pengguna:</b>\n{me}").format(me=me, bio=bio)
    else:
        return ""


__help__ = "userinfo_help"

__mod_name__ = "Bios and Abouts"

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)
