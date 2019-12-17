from typing import Union, List, Optional

from future.utils import string_types
from telegram import ParseMode, Update, Bot, Chat, User
from telegram.ext import CommandHandler, RegexHandler, Filters
from telegram.utils.helpers import escape_markdown

from emilia import dispatcher, spamfilters, OWNER_ID
from emilia.modules.helper_funcs.handlers import CMD_STARTERS
from emilia.modules.helper_funcs.misc import is_module_loaded
from emilia.modules.connection import connected

from emilia.modules import languages
from emilia.modules.helper_funcs.alternate import send_message

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from emilia.modules.helper_funcs.chat_status import user_admin, is_user_admin
    from telegram.ext.dispatcher import run_async

    from emilia.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, admin_ok=False, **kwargs):
            super().__init__(command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)
            sql.disableable_cache(command)

        def check_update(self, update):
            chat = update.effective_chat  # type: Optional[Chat]
            user = update.effective_user  # type: Optional[User]
            if super().check_update(update):
                # Should be safe since check_update passed.
                command = update.effective_message.text_html.split(None, 1)[0][1:].split('@')[0]
                
                # disabled, admincmd, user admin
                if sql.is_command_disabled(chat.id, command.lower()):
                    is_disabled = command in ADMIN_CMDS and is_user_admin(chat, user.id)
                    if not is_disabled and sql.is_disable_del(chat.id):
                        update.effective_message.delete()
                    return is_disabled

                # not disabled
                else:
                    return True

            return False


    class DisableAbleRegexHandler(RegexHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(pattern, callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            sql.disableable_cache(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            chat = update.effective_chat
            return super().check_update(update) and not sql.is_command_disabled(chat.id, self.friendly)


    @run_async
    @user_admin
    def disable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
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
                send_message(update.effective_message, languages.tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith(CMD_STARTERS):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                if conn:
                    text = languages.tl(update.effective_message, "Menonaktifkan penggunaan `{}` pada *{}*").format(disable_cmd, chat_name)
                else:
                    text = languages.tl(update.effective_message, "Menonaktifkan penggunaan `{}`").format(disable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Perintah itu tidak bisa dinonaktifkan"))

        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Apa yang harus saya nonaktifkan?"))


    @run_async
    @user_admin
    def enable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
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
                send_message(update.effective_message, languages.tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith(CMD_STARTERS):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                if conn:
                    text = languages.tl(update.effective_message, "Diaktifkan penggunaan `{}` pada *{}*").format(enable_cmd, chat_name)
                else:
                    text = languages.tl(update.effective_message, "Diaktifkan penggunaan `{}`").format(enable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Apakah itu bahkan dinonaktifkan?"))

        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Apa yang harus saya aktifkan?"))


    @run_async
    @user_admin
    def list_cmds(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += " - `{}`\n".format(escape_markdown(cmd))
            send_message(update.effective_message, languages.tl(update.effective_message, "Perintah berikut dapat diubah:\n{}").format(result),
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Tidak ada perintah yang dapat dinonaktifkan."))

    @run_async
    @user_admin
    def disable_del(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        msg = update.effective_message
        chat = update.effective_chat

        if len(msg.text.split()) >= 2:
            args = msg.text.split(None, 1)[1]
            if args == "yes" or args == "on" or args == "ya":
                sql.disabledel_set(chat.id, True)
                send_message(update.effective_message, languages.tl(update.effective_message, "Ketika command di nonaktifkan, maka saya *akan menghapus* pesan command tsb."), parse_mode="markdown")
                return
            elif args == "no" or args == "off":
                sql.disabledel_set(chat.id, False)
                send_message(update.effective_message, languages.tl(update.effective_message, "Saya *tidak akan menghapus* pesan dari command yang di nonaktifkan."), parse_mode="markdown")
                return
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Argumen tidak dikenal - harap gunakan 'yes', atau 'no'."))
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Opsi disable del saat ini: *{}*").format("Enabled" if sql.is_disable_del(chat.id) else "Disabled"), parse_mode="markdown")


    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return languages.tl(update.effective_message, "Tidak ada perintah yang dinonaktifkan!")

        result = ""
        for cmd in disabled:
            result += " - `{}`\n".format(escape_markdown(cmd))
        return languages.tl(chat_id, "Perintah-perintah berikut saat ini dibatasi:\n{}").format(result)


    @run_async
    def commands(bot: Bot, update: Update):
        chat = update.effective_chat
        user = update.effective_user
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
                send_message(update.effective_message, languages.tl(update.effective_message, "Anda bisa lakukan command ini pada grup, bukan pada PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        text = build_curr_disabled(chat.id)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return languages.tl(OWNER_ID, "{} item yang dinonaktifkan, pada {} obrolan.").format(sql.num_disabled(), sql.num_chats())


    def __import_data__(chat_id, data):
        disabled = data.get('disabled', {})
        for disable_cmd in disabled:
            sql.disable_command(chat_id, disable_cmd)


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)


    __mod_name__ = "Command disabling"

    __help__ = "disable_help"

    DISABLE_HANDLER = CommandHandler("disable", disable, pass_args=True)#, filters=Filters.group)
    ENABLE_HANDLER = CommandHandler("enable", enable, pass_args=True)#, filters=Filters.group)
    COMMANDS_HANDLER = CommandHandler(["cmds", "disabled"], commands)#, filters=Filters.group)
    TOGGLE_HANDLER = CommandHandler("listcmds", list_cmds)#, filters=Filters.group)
    DISABLEDEL_HANDLER = CommandHandler("disabledel", disable_del)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)
    dispatcher.add_handler(DISABLEDEL_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleRegexHandler = RegexHandler
