import html
import json
import random
from datetime import datetime
from typing import Optional, List
import time
import locale

import requests
from telegram.error import BadRequest, Unauthorized
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from emilia import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER, spamfilters, MAPS_API
from emilia.__main__ import STATS, USER_INFO
from emilia.modules.disable import DisableAbleCommandHandler
from emilia.modules.helper_funcs.extraction import extract_user
from emilia.modules.helper_funcs.filters import CustomFilters

# Change language locale to Indonesia
# Install language:
# - sudo apt-get install language-pack-id language-pack-id-base manpages
locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

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
    "Lari lari lari - Tsubatsa",
    "Ngapain lari-lari? Lagi lomba lari?",
    "Lari mulu, mau jadi atletik?",
    "Kejar saya kalau bisa 😜"
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
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send messages
    update.effective_message.reply_text(random.choice(RUN_STRINGS))

@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    #if msg.from_user.username:
    #    curr_user = "@" + escape_markdown(msg.from_user.username)
    #else:
    curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        #if slapped_user.username:
        #    user2 = "@" + escape_markdown(slapped_user.username)
        #else:
        user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "Pengirim asli, {}, memiliki ID `{}`.\nSi penerus pesan, {}, memiliki ID `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("Id {} adalah `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Id Anda adalah `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("Id grup ini adalah `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        msg.reply_text("Saya tidak dapat mengekstrak pengguna dari ini.")
        return

    else:
        return

    text = "<b>Info Pengguna</b>:" \
           "\nID: <code>{}</code>" \
           "\nNama depan: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nNama belakang: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nNama pengguna: @{}".format(html.escape(user.username))

    text += "\nTautan pengguna permanen: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nOrang ini adalah pemilik saya - saya tidak akan pernah melakukan apa pun terhadap mereka!"
    else:
        if user.id in SUDO_USERS:
            text += "\nOrang ini adalah salah satu pengguna sudo saya! " \
                    "Hampir sama kuatnya dengan pemilik saya - jadi tontonlah."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nOrang ini adalah salah satu pengguna dukungan saya! " \
                        "Tidak sekuat pengguna sudo, tetapi masih dapat menyingkirkan Anda dari peta."

            if user.id in WHITELIST_USERS:
                text += "\nOrang ini telah dimasukkan dalam daftar putih! " \
                        "Itu berarti saya tidak diizinkan untuk melarang/menendang mereka."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Selalu ada waktu banned untukku!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location, key=MAPS_API))
    print(res.text)

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
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
                update.message.reply_text("Sekarang pukul {} di {}".format(time_there, location))


@run_async
def get_time_alt(bot: Bot, update: Update, args: List[str]):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Selalu ada waktu banned untukku!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get('https://dev.virtualearth.net/REST/v1/timezone/?query={}&key={}'.format(location, MAPS_API))

    if res.status_code == 200:
        loc = res.json()
        if len(loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation']) == 0:
            update.message.reply_text("Lokasi tidak di temukan!")
            return
        placename = loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation'][0]['placeName']
        localtime = loc['resourceSets'][0]['resources'][0]['timeZoneAtLocation'][0]['timeZone'][0]['convertedTime']['localTime']
        time = datetime.strptime(localtime, '%Y-%m-%dT%H:%M:%S').strftime("%H:%M:%S hari %A, %d %B")
        update.message.reply_text("Sekarang pukul `{}` di `{}`".format(time, placename), parse_mode="markdown")


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    message.delete()
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1], parse_mode=ParseMode.MARKDOWN)
    else:
        message.reply_text(args[1], quote=False, parse_mode=ParseMode.MARKDOWN)
        


MARKDOWN_HELP = """
Markdown adalah alat pemformatan yang sangat kuat yang didukung oleh telegram. {} memiliki beberapa penyempurnaan, untuk memastikan \
pesan yang disimpan diurai dengan benar, dan memungkinkan Anda membuat tombol.

- <code>_miring_</code>: membungkus teks dengan '_' akan menghasilkan teks miring
- <code>*tebal*</code>: membungkus teks dengan '*' akan menghasilkan teks tebal
- <code>`kode`</code>: membungkus teks dengan '`' akan menghasilkan teks monospace, juga dikenal sebagai 'kode'
- <code>[teks](URL)</code>: ini akan membuat tautan - pesan hanya akan menampilkan <code>teks</code>, \
dan mengetuknya akan membuka halaman di <code>URL</code>.
Contoh: <code>[test](contoh.com)</code>

- <code>[TombolTeks](buttonurl:URL)</code>: ini adalah perangkat tambahan khusus yang memungkinkan pengguna memiliki \
tombol di markdown mereka. <code>TombolTeks</code> akan menjadi apa yang ditampilkan pada tombol, dan <code>URL</code> \
akan menjadi url yang dibuka.
Contoh: <code>[Ini sebuah tombol](buttonurl:contoh.com)</code>

Jika Anda ingin beberapa tombol pada baris yang sama, gunakan :same, seperti :
<code>[satu](buttonurl://contoh.com)
[dua](buttonurl://google.com:same)</code>
Ini akan membuat dua tombol pada satu baris, bukan satu tombol per baris.

Perlu diingat bahwa pesan Anda <b>HARUS</b> berisi beberapa teks selain hanya sebuah tombol!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Coba teruskan pesan berikut kepada saya, dan Anda akan lihat!")
    update.effective_message.reply_text("/save Tes Ini adalah tes markdown. _miring_, *tebal*, `kode`, "
                                        "[URL](contoh.com) [tombol](buttonurl:github.com) "
                                        "[tombol2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
    update.effective_message.reply_text("Statistik saat ini:\n" + "\n".join([mod.__stats__() for mod in STATS]))


# /ip is for private use
__help__ = """
 - /id: dapatkan ID grup saat ini. Jika digunakan dengan membalas pesan, dapatkan id pengguna itu.
 - /runs: balas string acak dari larik balasan.
 - /lari: sama seperti runs.
 - /slap: menampar pengguna, atau ditampar jika bukan balasan.
 - /time <tempat>: memberi waktu lokal di tempat yang ditentukan.
 - /info: mendapatkan informasi tentang seorang pengguna.
 - /stickerid: balas pesan stiker untuk mendapatkan id stiker
 - /ping: mengecek kecepatan bot

 - /markdownhelp: ringkasan singkat tentang cara kerja markdown di telegram - hanya dapat dipanggil dalam obrolan pribadi.
"""

__mod_name__ = "Lainnya"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time_alt, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
LARI_HANDLER = DisableAbleCommandHandler("lari", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(LARI_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
