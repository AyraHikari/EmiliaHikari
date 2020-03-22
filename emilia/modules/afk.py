from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import MessageEntity
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, run_async

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, spamcheck
from emilia.modules.disable import DisableAbleCommandHandler, DisableAbleMessageHandler
from emilia.modules.sql import afk_sql as sql
from emilia.modules.users import get_user_id

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

AFK_GROUP = 7
AFK_REPLY_GROUP = 8


@run_async
@spamcheck
def afk(update, context):
    args = update.effective_message.text.split(None, 1)
    if len(args) >= 2:
        reason = args[1]
    else:
        reason = ""

    sql.set_afk(update.effective_user.id, reason)
    send_message(update.effective_message, tl(update.effective_message, "{} sekarang AFK!").format(update.effective_user.first_name))


@run_async
def no_longer_afk(update, context):
    user = update.effective_user  # type: Optional[User]

    if not user:  # ignore channels
        return

    res = sql.rm_afk(user.id)
    if res:
        send_message(update.effective_message, tl(update.effective_message, "{} sudah tidak AFK!").format(update.effective_user.first_name))


@run_async
def reply_afk(update, context):
    message = update.effective_message  # type: Optional[Message]

    entities = message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION])
    if message.entities and entities:
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name
                
            elif ent.type == MessageEntity.MENTION:
                user_id = get_user_id(message.text[ent.offset:ent.offset + ent.length])
                if not user_id:
                    # Should never happen, since for a user to become AFK they must have spoken. Maybe changed username?
                    return
                try:
                    chat = context.bot.get_chat(user_id)
                except BadRequest:
                    print("Error: Could not fetch userid {} for AFK module".format(user_id))
                    return
                fst_name = chat.first_name
                
            else:   
                return

            if sql.is_afk(user_id):
                valid, reason = sql.check_afk_status(user_id)
                if valid:
                    if not reason:
                        res = tl(update.effective_message, "{} sedang AFK!").format(fst_name)
                    else:
                        res = tl(update.effective_message, "{} sedang AFK!\nKarena : {}").format(fst_name, reason)
                    send_message(update.effective_message, res)


__help__ = "afk_help"

__mod_name__ = "AFK"

AFK_HANDLER = DisableAbleCommandHandler("afk", afk)
AFK_REGEX_HANDLER = DisableAbleMessageHandler(Filters.regex("(?i)brb"), afk, friendly="afk")
NO_AFK_HANDLER = MessageHandler(Filters.all & Filters.group & ~Filters.update.edited_message, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(Filters.all & Filters.group , reply_afk)
# AFK_REPLY_HANDLER = MessageHandler(Filters.entity(MessageEntity.MENTION) | Filters.entity(MessageEntity.TEXT_MENTION),
#                                   reply_afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)
