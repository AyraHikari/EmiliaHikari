import pyowm
import json
import requests

from pyowm import timeutils, exceptions
from telegram import Message, Chat, Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import run_async

from emilia import dispatcher, updater, API_WEATHER, API_ACCUWEATHER, spamfilters
from emilia.modules.disable import DisableAbleCommandHandler

from emilia.modules.languages import tl
from emilia.modules.helper_funcs.alternate import send_message

@run_async
def cuaca(bot, update, args):
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        send_message(update.effective_message, tl(update.effective_message, "Saya akan terus mengawasi di saat senang maupun sedih!"))
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    try:
        owm = pyowm.OWM(API_WEATHER, language='id')
        observation = owm.weather_at_place(location)
        cuacanya = observation.get_weather()
        obs = owm.weather_at_place(location)
        lokasi = obs.get_location()
        lokasinya = lokasi.get_name()
        temperatur = cuacanya.get_temperature(unit='celsius')['temp']
        fc = owm.three_hours_forecast(location)

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
                    

        cuacabsk = besok.get_weather_code()

        send_message(update.effective_message, tl(update.effective_message, "{} hari ini sedang {}, sekitar {}°C.\n").format(lokasinya,
                statusnya, temperatur))

    except pyowm.exceptions.api_call_error.APICallError:
        send_message(update.effective_message, tl(update.effective_message, "Tulis lokasi untuk mengecek cuacanya"))
    except pyowm.exceptions.api_response_error.NotFoundError:
        send_message(update.effective_message, tl(update.effective_message, "Maaf, lokasi tidak ditemukan 😞"))
    else:
        return

@run_async
def accuweather(bot, update, args):
    chat_id = update.effective_chat.id
    message = update.effective_message
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
    if spam == True:
        return
    if args == []:
        return send_message(update.effective_message, tl(update.effective_message, "Masukan nama lokasinya untuk mengecek cuacanya!"))
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        send_message(update.effective_message, tl(update.effective_message, "Saya akan terus mengawasi di saat senang maupun sedih!"))
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    if True:
        url = "http://api.accuweather.com/locations/v1/cities/search.json?q={}&apikey={}".format(location, API_ACCUWEATHER)
        headers = {'Content-type': 'application/json'}
        r = requests.get(url, headers=headers)
        try:
            data = r.json()[0]
        except:
            return send_message(update.effective_message, tl(update.effective_message, "Maaf, lokasi tidak ditemukan 😞"))
        locid = data.get('Key')
        weatherlang = tl(update.effective_message, "weather_lang")
        urls = "http://api.accuweather.com/currentconditions/v1/{}.json?apikey={}&language={}&details=true&getphotos=true".format(locid, API_ACCUWEATHER, weatherlang)
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
        cuaca += tl(update.effective_message, "*Suhu:* `{}°C`/`{}°F`\n").format(datas.get('Temperature').get('Metric').get('Value'), datas.get('Temperature').get('Imperial').get('Value'))
        cuaca += tl(update.effective_message, "*Kelembapan:* `{}`\n").format(datas.get('RelativeHumidity'))
        direct = "{}".format(datas.get('Wind').get('Direction').get('English'))
        direct = direct.replace("N", "↑").replace("E", "→").replace("S", "↓").replace("W", "←")
        cuaca += tl(update.effective_message, "*Angin:* `{} {} km/h` | `{} mi/h`\n").format(direct, datas.get('Wind').get('Speed').get('Metric').get('Value'), datas.get('Wind').get('Speed').get('Imperial').get('Value'))
        cuaca += tl(update.effective_message, "*Tingkat UV:* `{}`\n").format(datas.get('UVIndexText'))
        cuaca += tl(update.effective_message, "*Tekanan:* `{}` (`{} mb`)\n").format(datas.get('PressureTendency').get('LocalizedText'), datas.get('Pressure').get('Metric').get('Value'))

        lok = []
        lok.append(data.get('LocalizedName'))
        lok.append(data.get('AdministrativeArea').get('LocalizedName'))
        for x in reversed(range(len(data.get('SupplementalAdminAreas')))):
            lok.append(data.get('SupplementalAdminAreas')[x].get('LocalizedName'))
        lok.append(data.get('Country').get('LocalizedName'))
        teks = tl(update.effective_message, "*Cuaca di {} saat ini*\n").format(data.get('LocalizedName'))
        teks += "{}\n".format(cuaca)
        teks += tl(update.effective_message, "*Lokasi:* `{}`\n\n").format(", ".join(lok))

        # try:
        #     bot.send_photo(chat_id, photo=datas.get('Photos')[0].get('LandscapeLink'), caption=teks, parse_mode="markdown", reply_to_message_id=message.message_id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="More info", url=datas.get('Link'))]]))
        # except:
        send_message(update.effective_message, teks, parse_mode="markdown", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="More info", url=datas.get('Link'))]]))


__help__ = "weather_help"

__mod_name__ = "Weather"

CUACA_HANDLER = DisableAbleCommandHandler(["cuaca", "weather"], accuweather, pass_args=True)
# ACCUWEATHER_HANDLER = DisableAbleCommandHandler("accuweather", accuweather, pass_args=True)


dispatcher.add_handler(CUACA_HANDLER)
# dispatcher.add_handler(ACCUWEATHER_HANDLER)
