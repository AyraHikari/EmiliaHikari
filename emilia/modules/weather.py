import pyowm
import json
import requests

from pyowm import timeutils, exceptions
from telegram import Message, Chat, Update, Bot
from telegram.ext import run_async

from emilia import dispatcher, updater, API_WEATHER, API_ACCUWEATHER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler

@run_async
def cuaca(bot, update, args):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Saya akan terus mengawasi di saat senang maupun sedih!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    try:
        bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
        owm = pyowm.OWM(API_WEATHER, language='id')
        observation = owm.weather_at_place(location)
        cuacanya = observation.get_weather()
        obs = owm.weather_at_place(location)
        lokasi = obs.get_location()
        lokasinya = lokasi.get_name()
        temperatur = cuacanya.get_temperature(unit='celsius')['temp']
        fc = owm.three_hours_forecast(location)
        besok = fc.get_weather_at(timeutils.tomorrow(5))
        temperaturbesok = besok.get_temperature(unit='celsius')['temp']

        # Simbol cuaca
        statusnya = ""
        cuacaskrg = cuacanya.get_weather_code()
        if cuacaskrg < 232: # Hujan badai
            statusnya += "⛈️ "
        elif cuacaskrg < 321: # Gerimis
            statusnya += "🌧️ "
        elif cuacaskrg < 504: # Hujan terang
            statusnya += "🌦️ "
        elif cuacaskrg < 531: # Hujan berawan
            statusnya += "⛈️ "
        elif cuacaskrg < 622: # Bersalju
            statusnya += "🌨️ "
        elif cuacaskrg < 781: # Atmosfer
            statusnya += "🌪️ "
        elif cuacaskrg < 800: # Cerah
            statusnya += "🌤️ "
        elif cuacaskrg < 801: # Sedikit berawan
            statusnya += "⛅️ "
        elif cuacaskrg < 804: # Berawan
            statusnya += "☁️ "
        statusnya += cuacanya._detailed_status
                    
        statusbesok = ""
        cuacaskrg = besok.get_weather_code()
        if cuacaskrg < 232: # Hujan badai
            statusbesok += "⛈️ "
        elif cuacaskrg < 321: # Gerimis
            statusbesok += "🌧️ "
        elif cuacaskrg < 504: # Hujan terang
            statusbesok += "🌦️ "
        elif cuacaskrg < 531: # Hujan berawan
            statusbesok += "⛈️ "
        elif cuacaskrg < 622: # Bersalju
            statusbesok += "🌨️ "
        elif cuacaskrg < 781: # Atmosfer
            statusbesok += "🌪️ "
        elif cuacaskrg < 800: # Cerah
            statusbesok += "🌤️ "
        elif cuacaskrg < 801: # Sedikit berawan
            statusbesok += "⛅️ "
        elif cuacaskrg < 804: # Berawan
            statusbesok += "☁️ "
        statusbesok += besok._detailed_status
                    

        cuacabsk = besok.get_weather_code()

        update.message.reply_text("{} hari ini sedang {}, sekitar {}°C.\n".format(lokasinya,
                statusnya, temperatur) +
                "Untuk besok pada pukul 06:00, akan {}, sekitar {}°C".format(statusbesok, temperaturbesok))

    except pyowm.exceptions.api_call_error.APICallError:
        update.effective_message.reply_text("Tulis lokasi untuk mengecek cuacanya")
    except pyowm.exceptions.api_response_error.NotFoundError:
        update.effective_message.reply_text("Maaf, lokasi tidak ditemukan 😞")
    else:
        return

@run_async
def accuweather(bot, update, args):
    chat_id = update.effective_chat.id
    message = update.effective_message
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return update.effective_message.reply_text("Saya kecewa dengan anda, saya tidak akan mendengar kata-kata anda sekarang!")
    if args == []:
        return update.effective_message.reply_text("Masukan nama lokasinya untuk mengecek cuacanya!")
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Saya akan terus mengawasi di saat senang maupun sedih!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    if True:
        bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send message
        url = "http://api.accuweather.com/locations/v1/cities/search.json?q={}&apikey={}".format(location, API_ACCUWEATHER)
        headers = {'Content-type': 'application/json'}
        r = requests.get(url, headers=headers)
        try:
            data = r.json()[0]
        except:
            return update.effective_message.reply_text("Maaf, lokasi tidak ditemukan 😞")
        locid = data.get('Key')
        urls = "http://api.accuweather.com/currentconditions/v1/{}.json?apikey={}&language=id&details=true&getphotos=true".format(locid, API_ACCUWEATHER)
        rs = requests.get(urls, headers=headers)
        datas = rs.json()[0]

        if datas.get('WeatherIcon') <= 44:
            icweather = "☁"
        elif datas.get('WeatherIcon') <= 42:
            icweather = "⛈"
        elif datas.get('WeatherIcon') <= 40:
            icweather = "🌧"
        elif datas.get('WeatherIcon') <= 38:
            icweather = "☁"
        elif datas.get('WeatherIcon') <= 36:
            icweather = "⛅"
        elif datas.get('WeatherIcon') <= 33:
            icweather = "🌑"
        elif datas.get('WeatherIcon') <= 32:
            icweather = "🌬"
        elif datas.get('WeatherIcon') <= 31:
            icweather = "⛄"
        elif datas.get('WeatherIcon') <= 30:
            icweather = "🌡"
        elif datas.get('WeatherIcon') <= 29:
            icweather = "☃"
        elif datas.get('WeatherIcon') <= 24:
            icweather = "❄"
        elif datas.get('WeatherIcon') <= 23:
            icweather = "🌥"
        elif datas.get('WeatherIcon') <= 19:
            icweather = "☁"
        elif datas.get('WeatherIcon') <= 18:
            icweather = "🌨"
        elif datas.get('WeatherIcon') <= 17:
            icweather = "🌦"
        elif datas.get('WeatherIcon') <= 15:
            icweather = "⛈"
        elif datas.get('WeatherIcon') <= 14:
            icweather = "🌦"
        elif datas.get('WeatherIcon') <= 12:
            icweather = "🌧"
        elif datas.get('WeatherIcon') <= 11:
            icweather = "🌫"
        elif datas.get('WeatherIcon') <= 8:
            icweather = "⛅️"
        elif datas.get('WeatherIcon') <= 5:
            icweather = "☀️"
        else:
            icweather = ""

        cuaca = "*{} {}*\n".format(icweather, datas.get('WeatherText'))
        cuaca += "*Suhu:* `{}°C`/`{}°F`\n".format(datas.get('Temperature').get('Metric').get('Value'), datas.get('Temperature').get('Imperial').get('Value'))
        cuaca += "*Kelembapan:* `{}`\n".format(datas.get('RelativeHumidity'))
        direct = "{}".format(datas.get('Wind').get('Direction').get('English'))
        direct = direct.replace("N", "↑").replace("E", "→").replace("S", "↓").replace("W", "←")
        cuaca += "*Angin:* `{} {} km/h` | `{} mi/h`\n".format(direct, datas.get('Wind').get('Speed').get('Metric').get('Value'), datas.get('Wind').get('Speed').get('Imperial').get('Value'))
        cuaca += "*Tingkat UV:* `{}`\n".format(datas.get('UVIndexText'))
        cuaca += "*Tekanan:* `{}` (`{} mb`)\n".format(datas.get('PressureTendency').get('LocalizedText'), datas.get('Pressure').get('Metric').get('Value'))

        lok = []
        lok.append(data.get('LocalizedName'))
        lok.append(data.get('AdministrativeArea').get('LocalizedName'))
        for x in reversed(range(len(data.get('SupplementalAdminAreas')))):
            lok.append(data.get('SupplementalAdminAreas')[x].get('LocalizedName'))
        lok.append(data.get('Country').get('LocalizedName'))
        teks = "*Cuaca di {} saat ini*\n".format(data.get('LocalizedName'))
        teks += "{}\n".format(cuaca)
        teks += "*Lokasi:* `{}`\n\n".format(", ".join(lok))
        teks += "Untuk lebih lanjut silahkan cek cuacanya [disini]({}) atau [disini]({})".format(datas.get('MobileLink'), datas.get('Link'))

        #try:
        bot.send_photo(chat_id, photo=datas.get('Photos')[0].get('LandscapeLink'), caption=teks, parse_mode="markdown", reply_to_message_id=message.message_id)
        #except:
        #    update.message.reply_text(teks, parse_mode="markdown", disable_web_page_preview=True)


__help__ = """
 - /cuaca <kota>: mendapatkan info cuaca di tempat tertentu
"""

__mod_name__ = "Cuaca"

CUACA_HANDLER = DisableAbleCommandHandler("cuaca", accuweather, pass_args=True)
# ACCUWEATHER_HANDLER = DisableAbleCommandHandler("accuweather", accuweather, pass_args=True)


dispatcher.add_handler(CUACA_HANDLER)
# dispatcher.add_handler(ACCUWEATHER_HANDLER)
