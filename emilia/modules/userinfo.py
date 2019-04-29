import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import emilia.modules.sql.userinfo_sql as sql
from emilia import dispatcher, SUDO_USERS
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " belum mengatur pesan info tentang diri mereka!")
    else:
        update.effective_message.reply_text("Anda belum mengatur pesan info tentang diri Anda!")


@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            message.reply_text("Info Anda Diperbarui!")
        else:
            message.reply_text(
                "Info Anda harus di bawah {} karakter! Kamu punya {}.".format(MAX_MESSAGE_LENGTH // 4, len(info[1])))


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text("{} belum memiliki pesan tentang dirinya sendiri!".format(username))
    else:
        update.effective_message.reply_text("Anda belum memiliki bio set tentang diri Anda!")


@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    sender = update.effective_user  # type: Optional[User]
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            message.reply_text("Ha, Anda tidak dapat mengatur bio Anda sendiri! Anda berada di bawah belas kasihan orang lain di sini...")
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            message.reply_text("Umm ... yah, saya hanya mempercayai pengguna sudo untuk mengatur bio saya.")
            return

        text = message.text
        bio = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text("Bio {} diperbarui!".format(repl_message.from_user.first_name))
            else:
                message.reply_text(
                    "Biografi harus di bawah {} karakter! Anda mencoba mengatur {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
    else:
        message.reply_text("Balas pesan seseorang untuk mengatur bio mereka!")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return "<b>Tentang pengguna:</b>\n{me}\n<b>Apa yang orang lain katakan:</b>\n{bio}".format(me=me, bio=bio)
    elif bio:
        return "<b>Apa yang orang lain katakan:</b>\n{bio}\n".format(me=me, bio=bio)
    elif me:
        return "<b>Tentang pengguna:</b>\n{me}""".format(me=me, bio=bio)
    else:
        return ""


__help__ = """
 - /setbio <text>: saat membalas, akan menyimpan bio pengguna lain
 - /bio: akan mendapatkan biodata Anda atau pengguna lain. Ini tidak dapat diatur sendiri.
 - /setme <text>: akan mengatur info Anda
 - /me: akan mendapatkan info Anda atau pengguna lain
"""

__mod_name__ = "Biografi dan Tentang"

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)
