import html
import json
import random
from datetime import datetime
from typing import Optional, List
import time
import locale

import requests
from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity, InlineKeyboardMarkup
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER, spamfilters, MAPS_API
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters
from emilia.modules.helper_funcs.msg_types import get_message_type
from emilia.modules.helper_funcs.misc import build_keyboard_alternate

from emilia.modules.languages import tl
from emilia.modules.sql import languages_sql as lang_sql
import emilia.modules.sql.feds_sql as feds_sql
from emilia.modules.helper_funcs.alternate import send_message

# Change language locale to Indonesia
# Install language:
# - sudo apt-get install language-pack-id language-pack-id-base manpages
# locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

RUN_STRINGS = (
    "Kemana Anda pikir Anda akan pergi?",
    "Hah? apa? apakah mereka lolos?",
    "ZZzzZZzz... Hah? apa? oh... hanya mereka lagi, lupakan saja.",
    "Kembali kesini!",
    "Tidak terlalu cepat...",
    "Jangan lari-lari di ruangan! 😠",
    "Jangan tinggalkan aku sendiri bersama mereka!! 😧",
    "Anda lari, Anda mati.",
    "Lelucon pada Anda, saya ada di mana-mana 😏",
    "Anda akan menyesalinya...",
    "Anda juga bisa mencoba /kickme, saya dengar itu menyenangkan 😄",
    "Ganggulah orang lain, tidak ada yang peduli 😒",
    "Anda bisa lari, tetapi Anda tidak bisa bersembunyi.",
    "Apakah itu semua yang kamu punya?",
    "Saya di belakang Anda...",
    "Larilah sesuka kalian, Anda tidak dapat melarikan diri dari takdir",
    "Kita bisa melakukan ini dengan cara mudah, atau dengan cara yang sulit.",
    "Anda tidak mengerti, bukan?",
    "Ya, kamu sebaiknya lari!",
    "Tolong, ingatkan aku betapa aku peduli?",
    "Saya akan berlari lebih cepat jika saya adalah Anda.",
    "Itu pasti orang yang kita cari.",
    "Semoga peluang akan selalu menguntungkan Anda.",
    "Kata-kata terakhir yang terkenal.",
    "Dan mereka menghilang selamanya, tidak pernah terlihat lagi.",
    "\"Oh, lihat aku! Aku sangat keren, aku bisa lari dari bot!\" - orang ini",
    "Ya ya, cukup ketuk /kickme saja 😏",
    "Ini, ambil cincin ini dan pergi ke Mordor saat Anda berada di sana.",
    "Legenda mengatakan, mereka masih berlari...",
    "Tidak seperti Harry Potter, orang tuamu tidak bisa melindungimu dariku.",
    "Ketakutan menyebabkan kemarahan. Kemarahan menyebabkan kebencian. Kebencian menyebabkan penderitaan. "
    "Jika Anda terus berlari ketakutan, Anda mungkin menjadi Vader berikutnya.",
    "Darah hanya menyebabkan darah, dan kekerasan melahirkan kekerasan. Tidak lebih. Balas dendam hanyalah nama lain untuk pembunuhan."
    "Jika anda terus berlari dan mengganggu yang lain, maka saya akan membalaskan dendam untuk yang terganggu.",
    "Teruskan, tidak yakin kami ingin Anda di sini.",
    "Anda seorang penyi- Oh. Tunggu. Kamu bukan Harry, lanjutkan berlari.",
    "DILARANG BERLARI DI KORIDOR! 😠",
    "Vale, deliciae.",
    "Siapa yang membiarkan anjing-anjing itu keluar?",
    "Itu lucu, karena tidak ada yang peduli.",
    "Ah, sayang sekali. Saya suka yang itu.",
    "Terus terang, aku tidak peduli.",
    "Saya tidak peduli dengan anda... Jadi, lari lebih cepat!",
    "Anda tidak bisa MENANGANI kebenaran!",
    "Dulu, di galaksi yang sangat jauh... Seseorang pasti peduli dengan dia.",
    "Hei, lihat mereka! Mereka berlari dari Emilia yang tak terelakkan ... Lucu sekali 😂",
    "Han menembak lebih dulu. Begitu juga saya.",
    "Apa yang kamu kejar? kelinci putih?",
    "Sepertinya dokter akan mengatakan... LARI!",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} dengan {item}.",
    "{user1} {hits} {user2} di mukanya dengan {item}.",
    "{user1} {hits} {user2} dengan keras menggunakan {item}.",
    "{user1} {throws} sebuah {item} ke {user2}.",
    "{user1} meraih sebuah {item} dan {throws} itu di wajah {user2}.",
    "{user1} melempar sebuah {item} ke {user2}.",
    "{user1} mulai menampar konyol {user2} dengan {item}.",
    "{user1} menusuk {user2} dan berulang kali {hits} dia dengan {item}.",
    "{user1} {hits} {user2} dengan sebuah {item}.",
    "{user1} mengikat {user2} ke kursi dan {throws} sebuah {item}.",
    "{user1} memberikan dorongan ramah untuk membantu {user2} belajar berenang di lava."
)

ITEMS = (
    "wajan besi cor",
    "ikan tongkol",
    "tongkat pemukul baseball",
    "pedang excalibur",
    "tongkat kayu",
    "paku",
    "mesin pencetak",
    "sekop",
    "monitor CRT",
    "buku pelajaran fisika",
    "pemanggang roti",
    "potret Richard Stallman",
    "televisi",
    "lima ton truk",
    "gulungan lakban",
    "buku",
    "laptop",
    "televisi lama",
    "karung batu",
    "ikan lele",
    "gas LPG",
    "tongkat pemukul berduri",
    "pemadam api",
    "batu yang berat",
    "potongan kotoran",
    "sarang lebah",
    "sepotong daging busuk",
    "beruang",
    "sekarung batu bata",
)

THROW = (
    "melempar",
    "melempar",
    "membuang",
    "melempar",
)

HIT = (
    "memukul",
    "memukul",
    "menampar",
    "memukul",
    "menampar keras",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


@run_async
def runs(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    send_message(update.effective_message, random.choice(tl(update.effective_message, "RUN_STRINGS")))

@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    #if msg.from_user.username:
    #    curr_user = "@" + escape_markdown(msg.from_user.username)
    #else:
    curr_user = "{}".format(mention_markdown(msg.from_user.id, msg.from_user.first_name))

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        #if slapped_user.username:
        #    user2 = "@" + escape_markdown(slapped_user.username)
        #else:
        user2 = "{}".format(mention_markdown(slapped_user.id, slapped_user.first_name))

    # if no target found, bot targets the sender
    else:
        user1 = "{}".format(mention_markdown(bot.id, bot.first_name))
        user2 = curr_user

    temp = random.choice(tl(update.effective_message, "SLAP_TEMPLATES"))
    item = random.choice(tl(update.effective_message, "ITEMS"))
    hit = random.choice(tl(update.effective_message, "HIT"))
    throw = random.choice(tl(update.effective_message, "THROW"))

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    send_message(update.effective_message, repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    send_message(update.effective_message, res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            send_message(update.effective_message, 
                tl(update.effective_message, "Pengirim asli, {}, memiliki ID `{}`.\nSi penerus pesan, {}, memiliki ID `{}`.").format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            send_message(update.effective_message, tl(update.effective_message, "Id {} adalah `{}`.").format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            send_message(update.effective_message, tl(update.effective_message, "Id Anda adalah `{}`.").format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            send_message(update.effective_message, tl(update.effective_message, "Id grup ini adalah `{}`.").format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        send_message(update.effective_message, tl(update.effective_message, "Saya tidak dapat mengekstrak pengguna dari ini."))
        return

    else:
        return

    text = tl(update.effective_message, "<b>Info Pengguna</b>:") \
           + "\nID: <code>{}</code>".format(user.id) + \
           tl(update.effective_message, "\nNama depan: {}").format(html.escape(user.first_name))

    if user.last_name:
        text += tl(update.effective_message, "\nNama belakang: {}").format(html.escape(user.last_name))

    if user.username:
        text += tl(update.effective_message, "\nNama pengguna: @{}").format(html.escape(user.username))

    text += tl(update.effective_message, "\nTautan pengguna permanen: {}").format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += tl(update.effective_message, "\n\nOrang ini adalah pemilik saya - saya tidak akan pernah melakukan apa pun terhadap mereka!")
    else:
        if user.id in SUDO_USERS:
            text += tl(update.effective_message, "\n\nOrang ini adalah salah satu pengguna sudo saya! " \
                    "Hampir sama kuatnya dengan pemilik saya - jadi tontonlah.")
        else:
            if user.id in SUPPORT_USERS:
                text += tl(update.effective_message, "\n\nOrang ini adalah salah satu pengguna dukungan saya! " \
                        "Tidak sekuat pengguna sudo, tetapi masih dapat menyingkirkan Anda dari peta.")

            if user.id in WHITELIST_USERS:
                text += tl(update.effective_message, "\n\nOrang ini telah dimasukkan dalam daftar putih! " \
                        "Itu berarti saya tidak diizinkan untuk melarang/menendang mereka.")

    fedowner = feds_sql.get_user_owner_fed_name(user.id)
    if fedowner:
        text += tl(update.effective_message, "\n\n<b>Pengguna ini adalah pemilik federasi ini:</b>\n<code>")
        text += "</code>, <code>".join(fedowner)
        text += "</code>"
    # fedadmin = feds_sql.get_user_admin_fed_name(user.id)
    # if fedadmin:
    #     text += tl(update.effective_message, "\n\nThis user is a fed admin in the current federation:\n")
    #     text += ", ".join(fedadmin)

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id, chat.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        send_message(update.effective_message, tl(update.effective_message, "Selalu ada waktu banned untukku!"))
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location, key=MAPS_API))
    print(res.text)

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S hari %A %d %B")
                send_message(update.effective_message, "Sekarang pukul {} di {}".format(time_there, location))


@run_async
def get_time_alt(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if args:
        location = " ".join(args)
        if location.lower() == bot.first_name.lower():
            send_message(update.effective_message, "Selalu ada waktu banned untukku!")
            bot.send_sticker(update.effective_chat.id, BAN_STICKER)
            return

        res = requests.get('https://dev.virtualearth.net/REST/v1/timezone/?query={}&key={}'.format(location, MAPS_API))

        if res.status_code == 200:
            loc = res.json()
            if len(loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation']) == 0:
                send_message(update.effective_message, tl(update.effective_message, "Lokasi tidak di temukan!"))
                return
            placename = loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation'][0]['placeName']
            localtime = loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation'][0]['timeZone'][0]['convertedTime']['localTime']
            if lang_sql.get_lang(update.effective_chat.id) == "id":
                locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
                time = datetime.strptime(localtime, '%Y-%m-%dT%H:%M:%S').strftime("%H:%M:%S hari %A, %d %B")
            else:
                time = datetime.strptime(localtime, '%Y-%m-%dT%H:%M:%S').strftime("%H:%M:%S %A, %d %B")
            send_message(update.effective_message, tl(update.effective_message, "Sekarang pukul `{}` di `{}`").format(time, placename), parse_mode="markdown")
    else:
        send_message(update.effective_message, tl(update.effective_message, "Gunakan `/time nama daerah`\nMisal: `/time jakarta`"), parse_mode="markdown")


@run_async
def echo(bot: Bot, update: Update):
    message = update.effective_message
    chat_id = update.effective_chat.id
    try:
        message.delete()
    except BadRequest:
        pass
    # Advanced
    text, data_type, content, buttons = get_message_type(message)
    tombol = build_keyboard_alternate(buttons)
    if str(data_type) in ('Types.BUTTON_TEXT', 'Types.TEXT'):
        try:
            if message.reply_to_message:
                bot.send_message(chat_id, text, parse_mode="markdown", reply_to_message_id=message.reply_to_message.message_id, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
            else:
                bot.send_message(chat_id, text, quote=False, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(tombol))
        except BadRequest:
            bot.send_message(chat_id, tl(update.effective_message, "Teks markdown salah!\nJika anda tidak tahu apa itu markdown, silahkan ketik `/markdownhelp` pada PM."), parse_mode="markdown")
            return


@run_async
def markdown_help(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    send_message(update.effective_message, tl(update.effective_message, "MARKDOWN_HELP").format(dispatcher.bot.first_name), parse_mode=ParseMode.HTML)
    send_message(update.effective_message, tl(update.effective_message, "Coba teruskan pesan berikut kepada saya, dan Anda akan lihat!"))
    send_message(update.effective_message, tl(update.effective_message, "/save test Ini adalah tes markdown. _miring_, *tebal*, `kode`, "
                                        "[URL](contoh.com) [tombol](buttonurl:github.com) "
                                        "[tombol2](buttonurl:google.com:same)"))


@run_async
def stats(bot: Bot, update: Update):
    send_message(update.effective_message, tl(update.effective_message, "Statistik saat ini:\n") + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = "misc_help"

__mod_name__ = "Misc"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = DisableAbleCommandHandler("time", get_time_alt, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler(["runs", "lari"], runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
