# Emilia
Telegram modular Python bot berjalan di python3 dengan database sqlalchemy.

Based on [marie bot](https://github.com/PaulSonOfLars/tgbot)

### [Read english README](https://github.com/AyraHikari/EmiliaHikari/blob/master/README.md)

**If you want to translate this bot**, [please go here](https://github.com/AyraHikari/EmiliaHikari/blob/master/TRANSLATION.md)

Dapat ditemukan di telegram sebagai [Emilia](https://t.me/EmiliaHikariBot).


Awalnya bot manajemen grup sederhana dengan beberapa fitur admin, telah berevolusi, menjadi sangat modular dan

Marie dan saya sedang memoderasi [support group](https://t.me/TeamNusantaraDevs), di mana Anda dapat meminta bantuan untuk mengaturnya
bot, temukan / minta fitur baru, laporkan bug, dan tetap di dalam pengulangan setiap kali pembaruan baru tersedia. Tentu saja
Saya juga akan membantu ketika skema database berubah, dan beberapa kolom tabel perlu dimodifikasi/ditambahkan. Catatan untuk pengelola bahwa semua perubahan skema akan ditemukan dalam pesan commit, dan tanggung jawab mereka untuk membaca setiap commit baru.

Bergabunglah dengan [news channel](https://t.me/AyraBotNews) jika Anda hanya ingin tetap di loop tentang fitur-fitur baru atau pengumuman.

Kalau tidak, [temukan aku di telegram](https://t.me/AyraHikari)! (Simpan semua pertanyaan dukungan dalam obrolan dukungan, tempat lebih banyak orang dapat membantu Anda.)

Catatan untuk pengelola bahwa semua perubahan skema akan ditemukan dalam pesan komit, dan tanggung jawabnya untuk membaca komitmen baru.


## Mulai bot.

Setelah Anda mengatur database Anda dan konfigurasi Anda (lihat di bawah) selesai, jalankan saja:

`python3 -m tg_bot`


## Menyiapkan bot (Baca ini sebelum mencoba menggunakannya!):
Harap pastikan untuk menggunakan python3.6, karena saya tidak dapat menjamin semuanya akan bekerja seperti yang diharapkan pada versi python yang lebih tua!
Ini karena parsing markdown dilakukan dengan mengulangi melalui dict, yang diurutkan secara default di 3.6.

### Konfigurasi

Ada dua kemungkinan cara mengkonfigurasi bot Anda: file config.py, atau variabel ENV.

Versi yang lebih disukai adalah menggunakan file `config.py`, karena memudahkan untuk melihat semua pengaturan Anda dikelompokkan bersama.
File ini harus ditempatkan di folder `tg_bot` Anda, bersama file `__main__.py` . 
Di sinilah token bot Anda akan dimuat, serta URI database Anda (jika Anda menggunakan database), dan sebagian besar
pengaturan Anda yang lain.

Dianjurkan untuk mengimpor sample_config dan memperluas kelas Config, karena ini akan memastikan konfigurasi Anda berisi semua
default ditetapkan di sample_config, sehingga lebih mudah untuk ditingkatkan.

Sebuah contoh file `config.py` seperti ini:
```
from tg_bot.sample_config import Config


class Development(Config):
    OWNER_ID = 388576209  # my telegram ID
    OWNER_USERNAME = "AyraHikari"  # my telegram username
    API_KEY = "your bot api key"  # my api key, as provided by the botfather
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/database'  # sample db credentials
    MESSAGE_DUMP = '-1234567890' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [18673980, 83489514]  # List of id's for users which have sudo access to the bot.
    LOAD = []
    NO_LOAD = ['translation']
```

Jika Anda tidak dapat memiliki file config.py (EG on heroku), juga dimungkinkan untuk menggunakan variabel lingkungan.
Variabel env berikut ini didukung:
 - `ENV`: Pengaturan ini ke APA SAJA akan mengaktifkan variabel env

 - `TOKEN`: Token bot Anda, sebagai string.
 - `OWNER_ID`: Bilangan bulat yang terdiri dari ID pemilik Anda
 - `OWNER_USERNAME`: Nama pengguna Anda

 - `DATABASE_URL`: URL basis data Anda
 - `MESSAGE_DUMP`: opsional: obrolan tempat Anda menyimpan pesan yang disimpan, untuk menghentikan orang yang menghapus pesan lama mereka
 - `LOAD`: Daftar modul terpisah ruang yang ingin Anda muat
 - `NO_LOAD`: Daftar modul terpisah ruang yang Anda ingin TIDAK memuat
 - `WEBHOOK`: Mengatur ini ke APA SAJA akan mengaktifkan webhooks ketika dalam mode pesan env
 - `URL`: URL webhook Anda harus terhubung ke (hanya diperlukan untuk mode webhook)

 - `SUDO_USERS`: Daftar terpisah dari user_id yang harus dipertimbangkan pengguna sudo
 - `SUPPORT_USERS`: Daftar terpisah dari user_id yang harus dipertimbangkan sebagai pengguna dukungan (dapat gban / ungban, tidak ada yang lain)
 - `WHITELIST_USERS`: Daftar terpisah dari user_id yang harus dipertimbangkan dalam daftar putih - mereka tidak dapat dicekal.
 - `DONATION_LINK`: Opsional: tautan di mana Anda ingin menerima donasi.
 - `CERT_PATH`: Path ke sertifikat webhook Anda
 - `PORT`: Port digunakan untuk webhooks Anda
 - `DEL_CMDS`: Apakah akan menghapus perintah dari pengguna yang tidak memiliki hak untuk menggunakan perintah itu
 - `STRICT_GBAN`: Tegakkan gban melintasi kelompok-kelompok baru serta kelompok-kelompok lama. Ketika seorang pengguna yang di-gbanned berbicara, dia akan dilarang.
 - `WORKERS`: Jumlah utas yang akan digunakan. 8 adalah jumlah yang disarankan (dan standar), tetapi pengalaman Anda mungkin bervariasi.
 __Note__ bahwa menjadi gila dengan lebih banyak thread tidak akan selalu mempercepat bot Anda, mengingat banyaknya akses data sql, dan cara python asynchronous calls bekerja.
 - `BAN_STICKER`: Stiker mana yang digunakan saat melarang orang.
 - `ALLOW_EXCL`: Apakah akan mengizinkan menggunakan tanda seru! untuk perintah serta /.

### Dependensi Python

Instal dependensi python yang diperlukan dengan berpindah ke direktori proyek dan menjalankan:

`pip3 install -r requirements.txt`.

Ini akan menginstal semua paket python yang diperlukan.

### Database

Jika Anda ingin menggunakan modul yang bergantung pada database (misalnya: kunci, catatan, userinfo, pengguna, filter, selamat datang),
Anda harus memiliki database yang terpasang di sistem Anda. Saya menggunakan postgres, jadi saya sarankan menggunakannya untuk kompatibilitas optimal.

Dalam kasus postgres, ini adalah bagaimana Anda akan mengatur database pada sistem debian / ubuntu. Distribusi lainnya dapat bervariasi.

- install postgresql:

`sudo apt-get update && sudo apt-get install postgresql`

- ganti ke pengguna postgres:

`sudo su - postgres`

- buat pengguna basis data baru (ubah YOUR_USER secara tepat):

`createuser -P -s -e YOUR_USER`

Ini akan diikuti dengan Anda perlu memasukkan kata sandi Anda.

- buat tabel database baru:

`createdb -O YOUR_USER YOUR_DB_NAME`

Ubah YOUR_USER dan YOUR_DB_NAME dengan tepat.

- akhirnya:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

Ini akan memungkinkan Anda untuk terhubung ke database Anda melalui terminal Anda.
Secara default, YOUR_HOST seharusnya be 0.0.0.0:5432.

Anda sekarang harus dapat membangun URI basis data Anda. Ini akan menjadi:

`sqldbtype://username:pw@hostname:port/db_name`

Ganti jenis sqldbtype dengan mana saja db yang Anda gunakan (mis. Postgresql, mysql, sqlite, dll)
ulangi untuk nama pengguna, kata sandi, nama host (localhost?), port (5432?), dan nama db Anda.

## Modul
### Mengatur urutan pemuatan.

Urutan pemuatan modul dapat diubah melalui pengaturan konfigurasi `LOAD` dan `NO_LOAD`.
Ini harus mewakili daftar.

Jika `LOAD` adalah daftar kosong, semua modul dalam `modules/` akan dipilih untuk memuat secara default.

Jika `NO_LOAD` tidak ada, atau daftar kosong, semua modul yang dipilih untuk memuat akan dimuat.

Jika modul ada di `LOAD` dan `NO_LOAD`, modul tidak akan dimuat - `NO_LOAD` mengambil prioritas.

### Membuat modul Anda sendiri.

Membuat modul telah disederhanakan semaksimal mungkin - tetapi jangan ragu untuk menyarankan penyederhanaan lebih lanjut.

Semua yang diperlukan adalah file .py Anda berada di folder modul.

Untuk menambahkan perintah, pastikan untuk mengimpor petugas operator melalui

`from tg_bot import dispatcher`.

Anda kemudian dapat menambahkan perintah menggunakan perintah biasa

`dispatcher.add_handler()`.

Menetapkan variabel `__help__` ke string yang menjelaskan modul ini tersedia
perintah akan memungkinkan bot untuk memuatnya dan menambahkan dokumentasi untuk
modul Anda ke perintah `/help`. Mengatur variabel `__mod_name__` juga akan memungkinkan Anda menggunakan nama ramah pengguna yang lebih baik untuk modul.

Fungsi `__migrate __()` digunakan untuk melakukan migrasi obrolan - saat obrolan ditingkatkan ke supergrup, ID berubah, jadi
perlu untuk memigrasikannya dalam db

Fungsi `__stats __()` adalah untuk mengambil statistik modul, misalnya jumlah pengguna, jumlah obrolan. Ini diakses
melalui perintah `/stats`, yang hanya tersedia untuk pemilik bot.


## Special Credits

Thanks to this user:
- [Paul Larsen](https://github.com/PaulSonOfLars) - marie creator, inspiration to do many things
- [Yan Gorobtsov](https://github.com/MrYacha) - for welcome security base and connection base and maybe others
- [アキト ミズキト](https://github.com/peaktogoo) - for reworked federation module
