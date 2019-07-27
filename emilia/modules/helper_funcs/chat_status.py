from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot

from emilia import DEL_CMDS, SUDO_USERS, WHITELIST_USERS
from emilia.modules import languages


def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages


def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in WHITELIST_USERS
        or chat.all_members_are_administrators
        or user_id == 777000
    ):
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ("administrator", "creator")


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or chat.all_members_are_administrators
        or user_id == 777000
    ):
        return True

    try:
        if not member:
            member = chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except:
        return False


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)
    return bot_member.status in ("administrator", "creator")


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        if can_delete(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Saya tidak dapat menghapus pesan di sini! "
                    "Pastikan saya admin dan dapat menghapus pesan pengguna lain.",
                )
            )

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_pin_messages:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Saya tidak bisa menyematkan pesan di sini! "
                    "Pastikan saya admin dan dapat pin pesan.",
                )
            )

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_promote_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Saya tidak dapat mempromosikan/mendemosikan orang di sini! "
                    "Pastikan saya admin dan dapat menunjuk admin baru.",
                )
            )

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_restrict_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Saya tidak bisa membatasi orang di sini! "
                    "Pastikan saya admin dan dapat menunjuk admin baru.",
                )
            )

    return promote_rights


def bot_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        if is_bot_admin(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Saya tidak bisa membatasi orang di sini! "
                    "Pastikan saya admin dan dapat menunjuk admin baru.",
                )
            )

    return is_admin


def user_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

        else:
            update.effective_message.reply_text(
                languages.tl(
                    update.effective_message,
                    "Siapa ini yang bukan admin memberikan perintah kepada saya?",
                )
            )

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

        else:
            bot.answer_callback_query(
                update.callback_query.id,
                languages.tl(update.effective_message, "Anda bukan admin di grup ini!"),
            )

    return is_admin


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

    return is_not_admin
