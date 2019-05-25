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
    escape_invalid_curly_brackets
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

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
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
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
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

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]

                # If user ban protected don't apply security on him
                if is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id)):
                    continue

                # Security soft mode
                if sql.welcome_security(chat.id) == "soft":
                    try:
                        bot.restrict_chat_member(chat.id, new_mem.id, can_send_messages=True, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False, until_date=(int(time.time() + 24 * 60 * 60)))
                    except:
                        pass

                # Add "I'm not bot button if enabled hard security"
                if sql.welcome_security(chat.id) == "hard":
                    try:
                        update.effective_message.reply_text("Hai {}, klik tombol di bawah ini untuk disuarakan.".format(new_mem.first_name), 
                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Klik di sini untuk meyakinkan Anda manusia!", 
                         callback_data="check_bot_({})".format(new_mem.id)) ]]))
                        bot.restrict_chat_member(chat.id, new_mem.id, can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False)
                    except:
                        pass

                
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
    #bot.restrict_chat_member(chat.id, new_mem.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)))
    match = re.match(r"check_bot_\((.+?)\)", query.data)
    user_id = int(match.group(1))
    message = update.effective_message  # type: Optional[Message]
    if user_id == user.id:
        query.answer(text="Disuarakan!")
        #Unmute user
        bot.restrict_chat_member(chat.id, user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        bot.deleteMessage(chat.id, message.message_id)
    else:
        query.answer(text="Anda bukan pengguna baru!")
    #TODO need kick users after 2 hours and remove message 


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
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
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
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
    if len(args) >= 1:
        var = args[0]
        print(var)
        if (var == "no" or var == "off"):
            sql.set_welcome_security(chat.id, False)
            update.effective_message.reply_text("Keamanan selamat datang yang dinonaktifkan")
        elif(var == "soft"):
            sql.set_welcome_security(chat.id, "soft")
            update.effective_message.reply_text("Saya akan membatasi pengguna untuk mengirim media selama 24 jam")
        elif(var == "hard"):
            sql.set_welcome_security(chat.id, "hard")
            update.effective_message.reply_text("Saya akan mematikan pengguna saat dia tidak mengklik tombol")
        else:
            update.effective_message.reply_text("Silakan tulis `off`/`no`/`soft`/`hard`!", parse_mode=ParseMode.MARKDOWN)
    else:
        status = sql.welcome_security(chat.id)
        update.effective_message.reply_text(status)


@run_async
@user_admin
def cleanservice(bot: Bot, update: Update, args: List[str]) -> str:
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
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
        update.effective_message.reply_text("Silakan masukkan yes/ya atau no/tidak di grup Anda!", parse_mode=ParseMode.MARKDOWN)



@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "Obrolan ini diatur dengan setelan selamat datang: `{}`.\n*Pesan selamat datang "
            "(tidak mengisi {{}}) adalah:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

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
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
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
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)
                
            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

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

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
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
    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
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

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
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
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    if welcome_pref:
        welc = "✅ Aktif"
    else:
        welc = "❎ Tidak Aktif"
    if goodbye_pref:
        gdby = "✅ Aktif"
    else:
        gdby = "❎ Tidak Aktif"
    return "Obrolan ini memiliki preferensi `{}` untuk pesan sambutan.\n" \
           "Untuk preferensi pesan selamat tinggal `{}`.".format(welc, gdby)

def __chat_settings_btn__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    if welcome_pref:
        welc = "✅ Aktif"
    else:
        welc = "❎ Tidak Aktif"
    if goodbye_pref:
        gdby = "✅ Aktif"
    else:
        gdby = "❎ Tidak Aktif"
    button = []
    button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
        InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
    button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
        InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
    return button

def WELC_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button WELC EDIT".format(user.id))
    chat_id = query.data.split("|")[1]
    data = query.data.split("=")[1].split("|")[0]
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    if data == "w?":
        bot.answerCallbackQuery(query.id, "Bot akan mengirim pesan setiap ada member baru masuk jika di aktifkan.", show_alert=True)
    if data == "g?":
        bot.answerCallbackQuery(query.id, "Bot akan mengirim pesan setiap ada member yang keluar jika di aktifkan. Akan aktif hanya untuk grup dibawah 100 member.", show_alert=True)
    if data == "w":
        welcome_pref, _, _ = sql.get_welc_pref(chat_id)
        goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
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
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Obrolan ini preferensi pesan sambutannya telah diganti menjadi `{}`.\n".format(welc)
        text += "Untuk preferensi pesan selamat tinggal `{}`.".format(gdby)
        button = []
        button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
            InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
            InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        bot.answer_callback_query(query.id)
    if data == "g":
        welcome_pref, _, _ = sql.get_welc_pref(chat_id)
        goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
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
        chat = bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Obrolan ini preferensi pesan selamat tinggal telah diganti menjadi `{}`.\n".format(gdby)
        text += "Untuk preferensi pesan sambutan `{}`.".format(welc)
        button = []
        button.append([InlineKeyboardButton(text="Selamat datang", callback_data="set_welc=w?|{}".format(chat_id)),
            InlineKeyboardButton(text=welc, callback_data="set_welc=w|{}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Selamat tinggal", callback_data="set_welc=g?|{}".format(chat_id)),
            InlineKeyboardButton(text=gdby, callback_data="set_welc=g|{}".format(chat_id))])
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
 - /welcomesecurity <off/soft/hard>: soft - batasi pengguna mengirim file media selama 24 jam, hard - Membatasi pengguna mengirim pesan sementara dia tidak mengklik tombol \"Saya bukan bot\"

 - /welcomehelp: lihat informasi pemformatan lebih lanjut untuk pesan selamat datang/selamat tinggal kustom.
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
SECURITY_HANDLER = CommandHandler("welcomesecurity", security, pass_args=True, filters=Filters.group)
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
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(WELC_BTNSET_HANDLER)

dispatcher.add_handler(help_callback_handler)
