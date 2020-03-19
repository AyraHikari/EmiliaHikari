import datetime
import importlib
import re
import resource
import platform
import sys
import traceback
import wikipedia
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop, Dispatcher
from telegram.utils.helpers import escape_markdown, mention_html

from emilia import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, spamfilters
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from emilia.modules import ALL_MODULES
from emilia.modules.languages import tl
from emilia.modules.helper_funcs.chat_status import is_user_admin
from emilia.modules.helper_funcs.misc import paginate_modules
from emilia.modules.helper_funcs.verifier import verify_welcome
from emilia.modules.sql import languages_sql as langsql

from emilia.modules.connection import connect_button
from emilia.modules.languages import set_language

PM_START_TEXT = "start_text"

HELP_STRINGS = "help_text"#.format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n")

DONATE_STRING = "donate_text"

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("emilia.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(update, context):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(context.match)
    print(update.effective_message.text)


@run_async
def start(update, context):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if update.effective_chat.type == "private":
        args = context.args
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, tl(update.effective_message, HELP_STRINGS))

            elif args[0].lower() == "get_notes":
                update.effective_message.reply_text(tl(update.effective_message, "Anda sekarang dapat mengambil catatan di grup."))

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

            elif args[0][:4] == "wiki":
                wiki = args[0].split("-")[1].replace('_', ' ')
                message = update.effective_message
                getlang = langsql.get_lang(message)
                if getlang == "id":
                    wikipedia.set_lang("id")
                pagewiki = wikipedia.page(wiki)
                judul = pagewiki.title
                summary = pagewiki.summary
                if len(summary) >= 4096:
                    summary = summary[:4000]+"..."
                message.reply_text("<b>{}</b>\n{}".format(judul, summary), parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton(text=tl(update.effective_message, "Baca di Wikipedia"), url=pagewiki.url)]]))

            elif args[0][:6].lower() == "verify":
                chat_id = args[0].split("_")[1]
                verify_welcome(update, context, chat_id)

        else:
            first_name = update.effective_user.first_name
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="🎉 Add me to your group", url="https://t.me/{}?startgroup=new".format(context.bot.username))],
                [InlineKeyboardButton(text="💭 Language", callback_data="main_setlang"), InlineKeyboardButton(text="⚙️ Connect Group", callback_data="main_connect")],
                [InlineKeyboardButton(text="👥 Support Group", url="https://t.me/EmiliaOfficial"), InlineKeyboardButton(text="🔔 Update Channel", url="https://t.me/AyraBotNews")],
                [InlineKeyboardButton(text="❓ Help", url="https://t.me/{}?start=help".format(context.bot.username)), InlineKeyboardButton(text="💖 Donate", url="http://ayrahikari.github.io/donations.html")]])
            update.effective_message.reply_text(
                tl(update.effective_message, PM_START_TEXT).format(escape_markdown(first_name), escape_markdown(context.bot.first_name), OWNER_ID),
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=buttons)
    else:
        update.effective_message.reply_text(tl(update.effective_message, "Ada yang bisa saya bantu? 😊"))


def m_connect_button(update, context):
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    connect_button(update, context)

def m_change_langs(update, context):
    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    set_language(update, context)

# for test purposes
def error_callback(update, context):
    # add all the dev user_ids in this list. You can also add ids of channels or groups.
    devs = [OWNER_ID]
    # we want to notify the user of this problem. This will always work, but not notify users if the update is an 
    # callback or inline query, or a poll update. In case you want this, keep in mind that sending the message 
    # could fail
    if update.effective_message:
        text = "Hey. I'm sorry to inform you that an error happened while I tried to handle your update. " \
               "My developer(s) will be notified."
        update.effective_message.reply_text(text)
    # This traceback is created with accessing the traceback object from the sys.exc_info, which is returned as the
    # third value of the returned tuple. Then we use the traceback.format_tb to get the traceback as a string, which
    # for a weird reason separates the line breaks in a list, but keeps the linebreaks itself. So just joining an
    # empty string works fine.
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    # lets try to get as much information from the telegram update as possible
    payload = ""
    # normally, we always have an user. If not, its either a channel or a poll update.
    if update.effective_user:
        payload += f' with the user {mention_html(update.effective_user.id, update.effective_user.first_name)}'
    # there are more situations when you don't get a chat
    if update.effective_chat:
        payload += f' within the chat <i>{update.effective_chat.title}</i>'
        if update.effective_chat.username:
            payload += f' (@{update.effective_chat.username})'
    # but only one where you have an empty payload by now: A poll (buuuh)
    if update.poll:
        payload += f' with the poll id {update.poll.id}.'
    # lets put this in a "well" formatted text
    text = f"Hey.\n The error <code>{context.error}</code> happened{payload}. The full traceback:\n\n<code>{trace}" \
           f"</code>"
    # and send it to the dev(s)
    for dev_id in devs:
        context.bot.send_message(dev_id, text, parse_mode=ParseMode.HTML)
    # we raise the error again, so the logger module catches it. If you don't use the logger module, use it.
    try:
        raise context.error
    except Unauthorized:
        # remove update.message.chat_id from conversation list
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)
    except BadRequest:
        # handle malformed requests - read more below!
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)
    except TimedOut:
        # handle slow connection problems
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)
    except NetworkError:
        # handle other connection problems
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)
    except ChatMigrated as e:
        # the chat_id of a group has changed, use e.new_chat_id instead
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)
    except TelegramError:
        # handle all other telegram related errors
        LOGGER.exception('Update "%s" caused error "%s"', update, context.error)


@run_async
def help_button(update, context):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = tl(update.effective_message, "Ini bantuan untuk modul *{}*:\n").format(HELPABLE[module].__mod_name__) \
                   + tl(update.effective_message, HELPABLE[module].__help__)

            query.message.reply_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(
                                        [[InlineKeyboardButton(text=tl(query.message, "Kembali"), callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(text=tl(query.message, HELP_STRINGS),
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(
                                        paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(text=tl(query.message, HELP_STRINGS),
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(
                                        paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=tl(query.message, HELP_STRINGS),
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        query.message.delete()
        context.bot.answer_callback_query(query.id)
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def get_help(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        # update.effective_message.reply_text("Contact me in PM to get the list of possible commands.",
        update.effective_message.reply_text(tl(update.effective_message, "Hubungi saya di PM untuk mendapatkan daftar perintah."),
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text=tl(update.effective_message, "Tolong"),
                                                                       url="t.me/{}?start=help".format(
                                                                           context.bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = tl(update.effective_message, "Ini adalah bantuan yang tersedia untuk modul *{}*:\n").format(HELPABLE[module].__mod_name__) \
               + tl(update.effective_message, HELPABLE[module].__help__)
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text=tl(update.effective_message, "Kembali"), callback_data="help_back")]]))

    else:
        send_help(chat.id, tl(update.effective_message, HELP_STRINGS))


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, tl(chat_id, "Ini adalah pengaturan Anda saat ini:") + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, tl(chat_id, "Sepertinya tidak ada pengaturan khusus pengguna yang tersedia 😢"),
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text=tl(chat_id, "Modul mana yang ingin Anda periksa untuk pengaturan {}?").format(
                                            chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, tl(chat_id, "Sepertinya tidak ada pengaturan obrolan yang tersedia 😢\nKirim ini "
                                                 "ke obrolan Anda sebagai admin untuk menemukan pengaturannya saat ini!"),
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(update, context):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = context.bot.get_chat(chat_id)
            getstatusadmin = context.bot.get_chat_member(chat_id, user.id)
            isadmin = getstatusadmin.status in ('administrator', 'creator')
            if isadmin == False or user.id != OWNER_ID:
                query.message.edit_text("Status admin anda telah berubah")
                return
            text = tl(update.effective_message, "*{}* memiliki pengaturan berikut untuk modul *{}*:\n\n").format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[
                                                                                        module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            try:
                set_button = CHAT_SETTINGS[module].__chat_settings_btn__(chat_id, user.id)
            except AttributeError:
                set_button = []
            set_button.append([InlineKeyboardButton(text=tl(query.message, "Kembali"),
                                                               callback_data="stngs_back({})".format(chat_id))])
            query.message.reply_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(set_button))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(text=tl(update.effective_message, "Hai! Ada beberapa pengaturan untuk {} - lanjutkan dan pilih "
                                       "apa yang Anda minati.").format(chat.title),
                                  reply_markup=InlineKeyboardMarkup(
                                        paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                         chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(text=tl(update.effective_message, "Hai! Ada beberapa pengaturan untuk {} - lanjutkan dan pilih "
                                       "apa yang Anda minati.").format(chat.title),
                                  reply_markup=InlineKeyboardMarkup(
                                        paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                         chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(text=tl(update.effective_message, "Hai! Ada beberapa pengaturan untuk {} - lanjutkan dan pilih "
                                       "apa yang Anda minati.").format(escape_markdown(chat.title)),
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                     chat=chat_id)))

        # ensure no spinny white circle
        query.message.delete()
        context.bot.answer_callback_query(query.id)
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = tl(update.effective_message, "Klik di sini untuk mendapatkan pengaturan obrolan ini, serta milik Anda.")
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="Pengaturan",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          context.bot.username, chat.id))]]))
        # else:
        #     text = tl(update.effective_message, "Klik di sini untuk memeriksa pengaturan Anda.")

    else:
        send_settings(chat.id, user.id, True)


@run_async
def donate(update, context):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return

    if chat.type == "private":
        update.effective_message.reply_text(tl(update.effective_message, DONATE_STRING), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        if OWNER_ID != 388576209 and DONATION_LINK:
            update.effective_message.reply_text(tl(update.effective_message, "Anda juga dapat menyumbang kepada orang yang saat ini menjalankan saya "
                                                "[disini]({})").format(DONATION_LINK),
                                                parse_mode=ParseMode.MARKDOWN)

    else:
        try:
            context.bot.send_message(user.id, tl(update.effective_message, DONATE_STRING), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            update.effective_message.reply_text(tl(update.effective_message, "Saya sudah PM Anda tentang donasi untuk pencipta saya!"))
        except Unauthorized:
            update.effective_message.reply_text(tl(update.effective_message, "Hubungi saya di PM dulu untuk mendapatkan informasi donasi."))




# Avoid memory dead
def memory_limit(percentage: float):
    if platform.system() != "Linux":
        print('Only works on linux!')
        return
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (int(get_memory() * 1024 * percentage), hard))

def get_memory():
    with open('/proc/meminfo', 'r') as mem:
        free_memory = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                free_memory += int(sline[1])
    return free_memory

def memory(percentage=0.5):
    def decorator(function):
        def wrapper(*args, **kwargs):
            memory_limit(percentage)
            try:
                function(*args, **kwargs)
            except MemoryError:
                mem = get_memory() / 1024 /1024
                print('Remain: %.2f GB' % mem)
                sys.stderr.write('\n\nERROR: Memory Exception\n')
                sys.exit(1)
        return wrapper
    return decorator


@memory(percentage=0.8)
def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    donate_handler = CommandHandler("donate", donate)
    M_CONNECT_BTN_HANDLER = CallbackQueryHandler(m_connect_button, pattern=r"main_connect")
    M_SETLANG_BTN_HANDLER = CallbackQueryHandler(m_change_langs, pattern=r"main_setlang")

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(donate_handler)
    dispatcher.add_handler(M_CONNECT_BTN_HANDLER)
    dispatcher.add_handler(M_SETLANG_BTN_HANDLER)

    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="127.0.0.1",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4)

    updater.idle()

if __name__ == '__main__':
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()
