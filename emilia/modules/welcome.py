import html, time
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, CallbackQuery
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import emilia.modules.sql.welcome_sql as sql
from emilia import dispatcher, OWNER_ID, LOGGER, spamfilters
from emilia.modules.helper_funcs.chat_status import user_admin, is_user_ban_protected
from emilia.modules.helper_funcs.misc import build_keyboard, revert_buttons
from emilia.modules.helper_funcs.msg_types import get_welcome_type
from emilia.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets, extract_time
from emilia.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    # Clean service welcome
    if cleanserv:
        dispatcher.bot.delete_message(chat.id, update.message.message_id)
        reply = False
    try:
        msg = dispatcher.bot.send_message(chat.id, message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard, reply_to_message_id=reply, disable_web_page_preview=True)
    except IndexError:
        msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                  "\nCatatan: pesan saat ini tidak valid "
                                                                  "karena masalah markdown. Bisa jadi "
                                                                  "karena nama pengguna."),
                                                  reply_to_message_id=reply, 
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                  "\nCatatan: pesan saat ini tidak valid "
                                                                  "karena ada masalah dengan beberapa salah tempat. "
                                                                  "Harap perbarui"),
                                                  reply_to_message_id=reply, 
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                      "\nCatatan: pesan saat ini memiliki url yang tidak "
                                                                      "valid di salah satu tombolnya. Harap perbarui."),
                                                      reply_to_message_id=reply, 
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                      "\nCatatan: pesan saat ini memiliki tombol yang "
                                                                      "menggunakan protokol url yang tidak didukung "
                                                                      "oleh telegram. Harap perbarui."),
                                                      reply_to_message_id=reply, 
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                      "\nCatatan: pesan saat ini memiliki beberapa url "
                                                                      "yang buruk. Harap perbarui."),
                                                      reply_to_message_id=reply, 
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            try:
                msg = dispatcher.bot.send_message(chat.id, markdown_parser(backup_message +
                                                                      "\nCatatan: Terjadi kesalahan saat mengirim pesan "
                                                                      "kustom. Harap perbarui."),
                                                      reply_to_message_id=reply, 
                                                      parse_mode=ParseMode.MARKDOWN)
                LOGGER.exception()
            except BadRequest:
                print("Cannot send welcome msg, bot is muted!")
                return ""
    return msg


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == 12345:#OWNER_ID:
                cleanserv = sql.clean_service(chat.id)
                if cleanserv:
                    bot.delete_message(chat.id, update.message.message_id)
                    bot.send_message(chat.id, "Master telah pulang! Mari kita mulai pesta ini! 😆")
                else:
                    update.effective_message.reply_text("Master telah pulang! Mari kita mulai pesta ini! 😆")
                continue

            # Don't welcome yourself
            elif new_mem.id == bot.id:
                continue

            else:
                # If welcome message is media, send with appropriate function
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    reply = update.message.message_id
                    cleanserv = sql.clean_service(chat.id)
                    # Clean service welcome
                    if cleanserv:
                        dispatcher.bot.delete_message(chat.id, update.message.message_id)
                        reply = False
                    # Formatting text
                    first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, first_name)
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention
                    formatted_text = cust_welcome.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    # Build keyboard
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                    getsec, mutetime, custom_text = sql.welcome_security(chat.id)

                    # If user ban protected don't apply security on him
                    if is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id)):
                        pass
                    else:
                        # If mute time is turned on
                        if mutetime:
                            if mutetime[:1] == "0":
                                try:
                                    bot.restrict_chat_member(chat.id, new_mem.id, can_send_messages=False)
                                    canrest = True
                                except BadRequest:
                                    canrest = False
                            else:
                                mutetime = extract_time(update.effective_message, mutetime)
                                try:
                                    bot.restrict_chat_member(chat.id, new_mem.id, until_date=mutetime, can_send_messages=False)
                                    canrest = True
                                except BadRequest:
                                    canrest = False
                        # If security welcome is turned on
                        if getsec and canrest:
                            sql.add_to_userlist(chat.id, new_mem.id)
                            keyb.append([InlineKeyboardButton(text=str(custom_text), callback_data="check_bot_({})".format(new_mem.id))])
                    keyboard = InlineKeyboardMarkup(keyb)
                    # Send message
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_content, caption=formatted_text, reply_markup=keyboard, parse_mode="markdown", reply_to_message_id=reply)
                    return
                # else, move on
                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, first_name)
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)
                    keyb = []

                getsec, mutetime, custom_text = sql.welcome_security(chat.id)
                
                # If user ban protected don't apply security on him
                if is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id)):
                    pass
                else:
                    if mutetime:
                        if mutetime[:1] == "0":
                            try:
                                bot.restrict_chat_member(chat.id, new_mem.id, can_send_messages=False)
                                canrest = True
                            except BadRequest:
                                canrest = False
                        else:
                            mutetime = extract_time(update.effective_message, mutetime)
                            try:
                                bot.restrict_chat_member(chat.id, new_mem.id, until_date=mutetime, can_send_messages=False)
                                canrest = True
                            except BadRequest:
                                canrest = False
                    if getsec and canrest:
                        sql.add_to_userlist(chat.id, new_mem.id)
                        keyb.append([InlineKeyboardButton(text=str(custom_text), callback_data="check_bot_({})".format(new_mem.id))])
                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]

                
            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest as excp:
                   pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)


@run_async
def check_bot_button(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    query = update.callback_query  # type: Optional[CallbackQuery]
    match = re.match(r"check_bot_\((.+?)\)", query.data)
    user_id = int(match.group(1))
    message = update.effective_message  # type: Optional[Message]
    getalluser = sql.get_chat_userlist(chat.id)
    if user.id in getalluser:
        query.answer(text="Kamu telah disuarakan!")
        # Unmute user
        bot.restrict_chat_member(chat.id, user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        sql.rm_from_userlist(chat.id, user.id)
    else:
        query.answer(text="Kamu bukan pengguna baru!")
    #TODO need kick users after 2 hours and remove message 


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, cust_content, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("Selamat jalan master 😢")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                reply = update.message.message_id
                cleanserv = sql.clean_service(chat.id)
                # Clean service welcome
                if cleanserv:
                    dispatcher.bot.delete_message(chat.id, update.message.message_id)
                    reply = False
                # Formatting text
                first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention
                formatted_text = cust_goodbye.format(first=escape_markdown(first_name),
                                              last=escape_markdown(left_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                # Build keyboard
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                # Send message
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_content, caption=cust_goodbye, reply_markup=keyboard, parse_mode="markdown", reply_to_message_id=reply)
                return

            first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, sql.DEFAULT_GOODBYE)


@run_async
@user_admin
def security(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    getcur, cur_value, cust_text = sql.welcome_security(chat.id)
    if len(args) >= 1:
        var = args[0].lower()
        if (var == "yes" or var == "ya" or var == "on"):
            check = bot.getChatMember(chat.id, bot.id)
            if check.status == 'member' or check['can_restrict_members'] == False:
                text = "Saya tidak bisa membatasi orang di sini! Pastikan saya admin agar bisa membisukan seseorang!"
                update.effective_message.reply_text(text, parse_mode="markdown")
                return ""
            sql.set_welcome_security(chat.id, True, str(cur_value), cust_text)
            update.effective_message.reply_text("Keamanan untuk member baru di aktifkan!")
        elif (var == "no" or var == "ga" or var == "off"):
            sql.set_welcome_security(chat.id, False, str(cur_value), cust_text)
            update.effective_message.reply_text("Di nonaktifkan, saya tidak akan membisukan member masuk lagi")
        else:
            update.effective_message.reply_text("Silakan tulis `on`/`ya`/`off`/`ga`!", parse_mode=ParseMode.MARKDOWN)
    else:
        getcur, cur_value, cust_text = sql.welcome_security(chat.id)
        if getcur:
            getcur = "Aktif"
        else:
            getcur = "Tidak Aktif"
        if cur_value[:1] == "0":
            cur_value = "Selamanya"
        text = "Pengaturan saat ini adalah:\nWelcome security: `{}`\nMember akan di mute selama: `{}`\nTombol unmute custom: `{}`".format(getcur, cur_value, cust_text)
        update.effective_message.reply_text(text, parse_mode="markdown")


@run_async
@user_admin
def security_mute(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    getcur, cur_value, cust_text = sql.welcome_security(chat.id)
    if len(args) >= 1:
        var = args[0]
        if var[:1] == "0":
            mutetime = "0"
            sql.set_welcome_security(chat.id, getcur, "0", cust_text)
            text = "Setiap member baru akan di bisukan selamanya sampai dia menekan tombol selamat datang!"
        else:
            mutetime = extract_time(message, var)
            if mutetime == "":
                return
            sql.set_welcome_security(chat.id, getcur, str(var), cust_text)
            text = "Setiap member baru akan di bisukan selama {} sampai dia menekan tombol selamat datang!".format(var)
        update.effective_message.reply_text(text)
    else:
        if str(cur_value) == "0":
            update.effective_message.reply_text("Pengaturans saat ini: member baru akan di bisukan selamanya sampai dia menekan tombol selamat datang!")
        else:
            update.effective_message.reply_text("Pengaturans saat ini: member baru akan di bisukan selama {} sampai dia menekan tombol selamat datang!".format(cur_value))


@run_async
@user_admin
def security_text(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    getcur, cur_value, cust_text = sql.welcome_security(chat.id)
    if len(args) >= 1:
        text = " ".join(args)
        sql.set_welcome_security(chat.id, getcur, cur_value, text)
        text = "Tombol custom teks telah di ubah menjadi: `{}`".format(text)
        update.effective_message.reply_text(text, parse_mode="markdown")
    else:
        update.effective_message.reply_text("Tombol teks security saat ini adalah: `{}`".format(cust_text), parse_mode="markdown")


@run_async
@user_admin
def security_text_reset(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    getcur, cur_value, cust_text = sql.welcome_security(chat.id)
    sql.set_welcome_security(chat.id, getcur, cur_value, "Klik disini untuk mensuarakan")
    update.effective_message.reply_text("Tombol custom teks security telah di reset menjadi: `Klik disini untuk mensuarakan`", parse_mode="markdown")


@run_async
@user_admin
def cleanservice(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0].lower()
            if (var == "no" or var == "off" or var == "tidak"):
                sql.set_clean_service(chat.id, False)
                update.effective_message.reply_text("Saya meninggalkan pesan layanan")
            elif(var == "yes" or var == "ya" or var == "on"):
                sql.set_clean_service(chat.id, True)
                update.effective_message.reply_text("Saya akan membersihkan pesan layanan")
            else:
                update.effective_message.reply_text("Silakan masukkan yes/ya atau no/tidak!", parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("Silakan masukkan yes/ya atau no/tidak!", parse_mode=ParseMode.MARKDOWN)
    else:
        curr = sql.clean_service(chat.id)
        if curr:
            update.effective_message.reply_text("Saat ini saya akan membersihkan `x joined the group` ketika ada member baru.", parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text("Saat ini saya tidak akan membersihkan `x joined the group` ketika ada member baru.", parse_mode=ParseMode.MARKDOWN)



@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        prev_welc = sql.get_clean_pref(chat.id)
        if prev_welc:
            prev_welc = True
        else:
            prev_welc = False
        cleanserv = sql.clean_service(chat.id)
        getcur, cur_value, cust_text = sql.welcome_security(chat.id)
        if getcur:
            welcsec = "Aktif "
        else:
            welcsec = "Tidak aktif "
        if cur_value[:1] == "0":
            welcsec += "(di bisukan selamanya sampai menekan tombol unmute)"
        else:
            welcsec += "(di bisukan selama {})".format(cur_value)
        text = "Obrolan ini diatur dengan setelan selamat datang: `{}`\n".format(pref)
        text += "Saat ini Saya menghapus pesan selamat datang lama: `{}`\n".format(prev_welc)
        text += "Saat ini Saya menghapus layanan pesan: `{}`\n".format(cleanserv)
        text += "Saat ini saya membisukan pengguna ketika mereka bergabung: `{}`\n".format(welcsec)
        text += "Tombol welcomemute akan mengatakan: `{}`\n".format(cust_text)
        text += "\n*Pesan selamat datang (tidak mengisi {{}}) adalah:*"
        update.effective_message.reply_text(text,
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT or welcome_type == sql.Types.TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](chat.id, cust_content, caption=welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP[welcome_type](chat.id, cust_content, caption=welcome_m, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("Saya akan sopan 😁")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("Aku ngambek, tidak menyapa lagi. 😣")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Saya hanya mengerti 'on/yes' atau 'off/no' saja!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, goodbye_m, cust_content, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "Obrolan ini memiliki setelan selamat tinggal yang disetel ke: `{}`.\n*Pesan selamat tinggal "
            "(tidak mengisi {{}}) adalah:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_content, caption=goodbye_m)
                
            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_content, caption=goodbye_m, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Aku akan menyesal jika orang-orang pergi!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Mereka pergi, mereka sudah mati bagi saya.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Saya hanya mengerti 'on/yes' atau 'off/no' saja!")


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan apa yang harus dibalas!")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text("Berhasil mengatur pesan sambutan kustom!")

    return "<b>{}:</b>" \
           "\n#SET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nSetel pesan selamat datang.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("Berhasil menyetel ulang pesan sambutan ke default!")
    return "<b>{}:</b>" \
           "\n#RESET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nSetel ulang pesan sambutan ke default.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan apa yang harus dibalas!")
        return ""

    sql.set_custom_gdbye(chat.id, content, text, data_type, buttons)
    msg.reply_text("Berhasil mengatur pesan selamat tinggal kustom!")
    return "<b>{}:</b>" \
           "\n#SET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nSetel pesan selamat tinggal.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Berhasil me-reset pesan selamat tinggal ke default!")
    return "<b>{}:</b>" \
           "\n#RESET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nSetel ulang pesan selamat tinggal.".format(html.escape(chat.title),
                                                 mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("Saya harus menghapus pesan selamat datang hingga dua hari.")
        else:
            update.effective_message.reply_text("Saat ini saya tidak menghapus pesan selamat datang yang lama!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Saya akan mencoba menghapus pesan selamat datang yang lama!")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nTelah mengatur penghapusan pesan sambutan menjadi <code>ON</code>.".format(html.escape(chat.title),
                                                                                             mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("Saya tidak akan menghapus pesan selamat datang yang lama.")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nTelah mengatur penghapusan pesan sambutan menjadi <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("Saya hanya mengerti 'on/yes' or 'off/no' saja!")
        return ""


WELC_HELP_TXT = "Pesan selamat datang/selamat tinggal grup Anda dapat dipersonalisasi dengan berbagai cara. Jika Anda menginginkan pesan" \
                " untuk dihasilkan secara individual, seperti pesan selamat datang default, Anda dapat menggunakan * variabel * ini:\n" \
                " - `{{first}}`: ini mewakili nama *pertama* pengguna\n" \
                " - `{{last}}`: ini mewakili nama *terakhir* pengguna. Default ke nama *depan* jika pengguna tidak memiliki " \
                "nama terakhir.\n" \
                " - `{{fullname}}`: ini mewakili nama *penuh* pengguna. Default ke *nama depan* jika pengguna tidak memiliki " \
                "nama terakhir.\n" \
                " - `{{username}}`: ini mewakili *nama pengguna* pengguna. Default ke *sebutan* jika pengguna" \
                "jika tidak memiliki nama pengguna.\n" \
                " - `{{mention}}`: ini hanya *menyebutkan* seorang pengguna - menandai mereka dengan nama depan mereka.\n" \
                " - `{{id}}`: ini mewakili *id* pengguna\n" \
                " - `{{count}}`: ini mewakili *nomor anggota* pengguna.\n" \
                " - `{{chatname}}`: ini mewakili *nama obrolan saat ini*.\n" \
                "\nSetiap variabel HARUS dikelilingi oleh `{{}}` untuk diganti.\n" \
                "Pesan sambutan juga mendukung markdown, sehingga Anda dapat membuat elemen apa pun teba/miring/kode/tautan." \
                "Tombol juga didukung, sehingga Anda dapat membuat sambutan Anda terlihat mengagumkan dengan beberapa " \
                "tombol pengantar yang bagus.\n" \
                "Untuk membuat tombol yang menautkan ke aturan Anda, gunakan ini: `[Peraturan](buttonurl:t.me/{}?start=group_id)`. " \
                "Cukup ganti `group_id` dengan id grup Anda, yang dapat diperoleh melalui /id, dan Anda siap untuk " \
                "pergi. Perhatikan bahwa id grup biasanya didahului oleh tanda `-`; ini diperlukan, jadi tolong jangan " \
                "hapus itu.\n" \
                "Jika Anda merasa senang, Anda bahkan dapat mengatur gambar/gif/video/pesan suara sebagai pesan selamat datang dengan " \
                "membalas media yang diinginkan, dan memanggil /setwelcome.".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _, _ = sql.get_gdbye_pref(chat_id)
    cleanserv = sql.clean_service(chat_id)
    if welcome_pref:
        welc = "✅ Aktif"
    else:
        welc = "❎ Tidak Aktif"
    if goodbye_pref:
        gdby = "✅ Aktif"
    else:
        gdby = "❎ Tidak Aktif"
    if cleanserv:
        clserv = "✅ Aktif"
    else:
        clserv = "❎ Tidak Aktif"
    return "Obrolan ini memiliki preferensi `{}` untuk pesan sambutan.\n" \
           "Untuk preferensi pesan selamat tinggal `{}`." \
           "Bot `{}` menghapus notifikasi member masuk/keluar secara otomatis".format(welc, gdby, clserv)

def __chat_settings_btn__(chat_id, user_id):
    welcome_pref, _, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _, _ = sql.get_gdbye_pref(chat_id)
    cleanserv = sql.clean_service(chat_id)
    if welcome_pref:
        welc = "✅ Aktif"
    else:
        welc = "❎ Tidak Aktif"
    if goodbye_pref:
        gdby = "✅ Aktif"
    else:
        gdby = "❎ Tidak Aktif"
    if cleanserv:
        clserv = "✅ Aktif"
    else:
        clserv = "❎ Tidak Aktif"
    button = []
    button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
        InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
        InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="Clean Service", callback_data="set_welc=s?|{}".format(chat_id)),
        InlineKeyboardButton(text=clserv, callback_data="set_welc=s|{}".format(chat_id))])
    return button

def WELC_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button WELC EDIT".format(user.id))
    chat_id = query.data.split("|")[1]
    data = query.data.split("=")[1].split("|")[0]
    if data == "w?":
        bot.answerCallbackQuery(query.id, "Bot akan mengirim pesan setiap ada member baru masuk jika di aktifkan.", show_alert=True)
    if data == "g?":
        bot.answerCallbackQuery(query.id, "Bot akan mengirim pesan setiap ada member yang keluar jika di aktifkan. Akan aktif hanya untuk grup dibawah 100 member.", show_alert=True)
    if data == "s?":
        bot.answerCallbackQuery(query.id, "Bot akan menghapus notifikasi member masuk atau member keluar secara otomatis jika di aktifkan.", show_alert=True)
    if data == "w":
        welcome_pref, _, _, _ = sql.get_welc_pref(chat_id)
        goodbye_pref, _, _, _ = sql.get_gdbye_pref(chat_id)
        cleanserv = sql.clean_service(chat_id)
        if welcome_pref:
            welc = "❎ Tidak Aktif"
            sql.set_welc_preference(str(chat_id), False)
        else:
            welc = "✅ Aktif"
            sql.set_welc_preference(str(chat_id), True)
        if goodbye_pref:
            gdby = "✅ Aktif"
        else:
            gdby = "❎ Tidak Aktif"
        if cleanserv:
            clserv = "✅ Aktif"
        else:
            clserv = "❎ Tidak Aktif"
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Obrolan ini preferensi pesan sambutannya telah diganti menjadi `{}`.\n".format(welc)
        text += "Untuk preferensi pesan selamat tinggal `{}`.\n".format(gdby)
        text += "Bot `{}` menghapus notifikasi member masuk/keluar secara otomatis".format(clserv)
        button = []
        button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
            InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
            InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Clean Service", callback_data="set_welc=s?|{}".format(chat_id)),
            InlineKeyboardButton(text=clserv, callback_data="set_welc=s|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if data == "g":
        welcome_pref, _, _, _ = sql.get_welc_pref(chat_id)
        goodbye_pref, _, _, _ = sql.get_gdbye_pref(chat_id)
        cleanserv = sql.clean_service(chat_id)
        if welcome_pref:
            welc = "✅ Aktif"
        else:
            welc = "❎ Tidak Aktif"
        if goodbye_pref:
            gdby = "❎ Tidak Aktif"
            sql.set_gdbye_preference(str(chat_id), False)
        else:
            gdby = "✅ Aktif"
            sql.set_gdbye_preference(str(chat_id), True)
        if cleanserv:
            clserv = "✅ Aktif"
        else:
            clserv = "❎ Tidak Aktif"
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Obrolan ini preferensi pesan selamat tinggal telah diganti menjadi `{}`.\n".format(gdby)
        text += "Untuk preferensi pesan sambutan `{}`.\n".format(welc)
        text += "Bot `{}` menghapus notifikasi member masuk/keluar secara otomatis".format(clserv)
        button = []
        button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
            InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
            InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Clean Service", callback_data="set_welc=s?|{}".format(chat_id)),
            InlineKeyboardButton(text=clserv, callback_data="set_welc=s|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if data == "s":
        welcome_pref, _, _, _ = sql.get_welc_pref(chat_id)
        goodbye_pref, _, _, _ = sql.get_gdbye_pref(chat_id)
        cleanserv = sql.clean_service(chat_id)
        if welcome_pref:
            welc = "✅ Aktif"
        else:
            welc = "❎ Tidak Aktif"
        if goodbye_pref:
            gdby = "✅ Aktif"
        else:
            gdby = "❎ Tidak Aktif"
        if cleanserv:
            clserv = "❎ Tidak Aktif"
            sql.set_clean_service(chat_id, False)
        else:
            clserv = "✅ Aktif"
            sql.set_clean_service(chat_id, True)
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Pengaturan clean service telah di ubah. Bot `{}` menghapus notifikasi member masuk/keluar.\n".format(clserv)
        text += "Untuk preferensi pesan sambutan `{}`.\n".format(welc)
        text += "Untuk preferensi pesan selamat tinggal `{}`.".format(gdby)
        button = []
        button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
            InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
            InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Clean Service", callback_data="set_welc=s?|{}".format(chat_id)),
            InlineKeyboardButton(text=clserv, callback_data="set_welc=s|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)



__help__ = """
{}

*Hanya admin:*
 - /welcome <on/off>: mengaktifkan/menonaktifkan pesan selamat datang.
 - /goodbye <on/off>: mengaktifkan/menonaktifkan pesan selamat tinggal.
 - /welcome: menunjukkan pengaturan selamat datang saat ini, tanpa pemformatan - berguna untuk mendaur ulang pesan selamat datang Anda!
 - /goodbye: penggunaan yang sama dan sama seperti /welcome.
 - /setwelcome <beberapa teks>: mengatur pesan sambutan khusus. Jika digunakan untuk membalas media, gunakan media itu.
 - /setgoodbye <beberapa teks>: mengatur pesan selamat tinggal khusus. Jika digunakan untuk membalas media, gunakan media itu.
 - /resetwelcome: reset ulang ke pesan selamat datang default.
 - /resetgoodbye: reset ulang ke pesan selamat tinggal default.
 - /cleanwelcome <on/off>: Pada anggota baru, coba hapus pesan sambutan sebelumnya untuk menghindari spamming obrolan.
 - /cleanservice <on/off/yes/no>: menghapus semua pesan layanan; itu adalah "x bergabung kedalam grup" yang Anda lihat ketika orang-orang bergabung.
 - /welcomemute <on/ya/off/ga>: semua pengguna yang bergabung akan di bisukan; sebuah tombol ditambahkan ke pesan selamat datang bagi mereka untuk mensuarakan diri mereka sendiri. Ini membuktikan bahwa mereka bukan bot!
 - /welcomemutetime <Xw/d/h/m>: jika pengguna belum menekan tombol "unmute" di pesan sambutan setelah beberapa waktu ini, mereka akan dibunyikan secara otomatis setelah periode waktu ini.
   Catatan: jika Anda ingin mengatur ulang waktu bisu menjadi selamanya, gunakan `/welcomemutetime 0m`. 0 == abadi!
 - /setmutetext <teks tombol>: Ubahsuaikan untuk tombol "Klik disini untuk mensuarakan" yang diperoleh dari mengaktifkan welcomemute.
 - /resetmutetext: Reset teks tombol unmute menjadi default.

Baca /welcomehelp untuk mempelajari tentang memformat teks Anda dan menyebutkan pengguna baru saat bergabung!

Anda dapat mengaktifkan/menonaktifkan pesan sambutan:
`/welcome off` atau `/welcome on`

Jika Anda ingin menyimpan gambar, gif, atau stiker, atau data lain, lakukan hal berikut:
Balas pesan stiker atau data apa pun yang Anda inginkan dengan teks `/setwelcome`. Data ini sekarang akan dikirim untuk menyambut pengguna baru.

Tip: gunakan /welcome noformat untuk mengambil pesan sambutan yang belum diformat.
Ini akan mengambil pesan selamat datang dan mengirimkannya tanpa memformatnya; memberi Anda markdown mentah, memungkinkan Anda untuk mengedit dengan mudah.
Ini juga berfungsi dengan /goodbye.
""".format(WELC_HELP_TXT)

__mod_name__ = "Welcomes/Goodbyes"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)
SECURITY_HANDLER = CommandHandler("welcomemute", security, pass_args=True, filters=Filters.group)
SECURITY_MUTE_HANDLER = CommandHandler("welcomemutetime", security_mute, pass_args=True, filters=Filters.group)
SECURITY_BUTTONTXT_HANDLER = CommandHandler("setmutetext", security_text, pass_args=True, filters=Filters.group)
SECURITY_BUTTONRESET_HANDLER = CommandHandler("resetmutetext", security_text_reset, filters=Filters.group)
CLEAN_SERVICE_HANDLER = CommandHandler("cleanservice", cleanservice, pass_args=True, filters=Filters.group)

help_callback_handler = CallbackQueryHandler(check_bot_button, pattern=r"check_bot_")
WELC_BTNSET_HANDLER = CallbackQueryHandler(WELC_EDITBTN, pattern=r"set_welc")

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(SECURITY_HANDLER)
dispatcher.add_handler(SECURITY_MUTE_HANDLER)
dispatcher.add_handler(SECURITY_BUTTONTXT_HANDLER)
dispatcher.add_handler(SECURITY_BUTTONRESET_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(WELC_BTNSET_HANDLER)

dispatcher.add_handler(help_callback_handler)
