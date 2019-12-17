import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from emilia import dispatcher, LOGGER, spamfilters
from emilia.modules.helper_funcs.chat_status import user_admin, can_delete
from emilia.modules.log_channel import loggable

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    msg = update.effective_message  # type: Optional[Message]
    if msg.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            message_id = msg.reply_to_message.message_id
            if args and args[0].isdigit():
                delete_to = message_id + int(args[0])
            else:
                delete_to = msg.message_id - 1
            for m_id in range(delete_to, message_id - 1, -1):  # Reverse iteration over message ids
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "Message can't be deleted":
                        send_message(update.effective_message, tl(update.effective_message, "Tidak dapat menghapus semua pesan. Pesannya mungkin terlalu lama, saya mungkin "
                                                  "tidak memiliki hak menghapus, atau ini mungkin bukan supergrup."))

                    elif err.message != "Message to delete not found":
                        LOGGER.exception("Error while purging chat messages.")

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "Message can't be deleted":
                    send_message(update.effective_message, tl(update.effective_message, "Tidak dapat menghapus semua pesan. Pesannya mungkin terlalu lama, saya mungkin "
                                              "tidak memiliki hak menghapus, atau ini mungkin bukan supergrup."))

                elif err.message != "Message to delete not found":
                    LOGGER.exception("Error while purging chat messages.")

            send_message(update.effective_message, tl(update.effective_message, "Pembersihan selesai."))
            return "<b>{}:</b>" \
                   "\n#PURGE" \
                   "\n<b>Admin:</b> {}" \
                   "\nPurged <code>{}</code> messages.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

    else:
        send_message(update.effective_message, tl(update.effective_message, "Balas pesan untuk memilih tempat mulai membersihkan."))

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if update.effective_message.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return "<b>{}:</b>" \
                   "\n#DEL" \
                   "\n<b>Admin:</b> {}" \
                   "\nMessage deleted.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))
    else:
        send_message(update.effective_message, tl(update.effective_message, "Apa yang ingin di hapus?"))

    return ""


__help__ = "msgdel_help"

__mod_name__ = "Purges"

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
