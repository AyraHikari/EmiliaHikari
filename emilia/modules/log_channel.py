from functools import wraps
from typing import Optional

from emilia import spamfilters, OWNER_ID
from emilia.modules.helper_funcs.misc import is_module_loaded

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async
    from telegram.utils.helpers import escape_markdown

    from emilia import dispatcher, LOGGER
    from emilia.modules.helper_funcs.chat_status import user_admin
    from emilia.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(bot: Bot, update: Update, *args, **kwargs):
            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>Link:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">klik disini</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    try:
                        send_log(bot, log_chat, chat.id, result)
                    except Unauthorized:
                        sql.stop_chat_logging(chat.id)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s was set as loggable, but had no return statement.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, tl(update.effective_message, "Saluran log ini telah dihapus - tidak bisa dibuka."))
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(log_chat_id, result + tl(update.effective_message, "\n\nMemformat telah dinonaktifkan karena kesalahan tak terduga."))


    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            send_message(update.effective_message, 
                tl(update.effective_message, "Grup ini memiliki semua log yang dikirim ke: {} (`{}`)").format(escape_markdown(log_channel_info.title),
                                                                         log_channel),
                parse_mode=ParseMode.MARKDOWN)

        else:
            send_message(update.effective_message, tl(update.effective_message, "Tidak ada saluran log yang telah ditetapkan untuk grup ini!"))


    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == chat.CHANNEL:
            send_message(update.effective_message, tl(update.effective_message, "Sekarang, teruskan /setlog ke grup yang Anda ingin ikat saluran ini!"))

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error deleting message in log channel. Should work anyway though.")
                    
            try:
                bot.send_message(message.forward_from_chat.id,
                             tl(update.effective_message, "Saluran ini telah ditetapkan sebagai saluran log untuk {}.").format(
                                 chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    bot.send_message(chat.id, tl(update.effective_message, "Gagal menyetel saluran log!\nSaya mungkin bukan admin di channel tersebut."))
                    sql.stop_chat_logging(chat.id)
                    return
                else:
                    LOGGER.exception("ERROR in setting the log channel.")
                    
            bot.send_message(chat.id, tl(update.effective_message, "Berhasil mengatur saluran log!"))

        else:
            send_message(update.effective_message, tl(update.effective_message, "Langkah-langkah untuk mengatur saluran log adalah:\n"
                               " - tambahkan bot ke saluran yang diinginkan\n"
                               " - Kirimkan /setlog ke saluran\n"
                               " - Teruskan /setlog ke grup\n"))


    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, tl(update.effective_message, "Channel telah dibatalkan tautannya {}").format(chat.title))
            send_message(update.effective_message, tl(update.effective_message, "Log saluran telah dinonaktifkan."))

        else:
            send_message(update.effective_message, tl(update.effective_message, "Belum ada saluran log yang ditetapkan!"))


    def __stats__():
        return tl(OWNER_ID, "{} saluran log ditetapkan.").format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return tl(user_id, "Grup ini memiliki semua log yang dikirim ke: {} (`{}`)").format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return tl(user_id, "Tidak ada saluran masuk yang ditetapkan untuk grup ini!")


    __help__ = "logchannel_help"

    __mod_name__ = "Channel Log"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
