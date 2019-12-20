
__lang__ = "🇮🇩 Indonesia"

id = {
# main stuff
	"start_text": """
Hai {}, nama saya {}! Saya seorang manajer grup yang dikelola oleh [master saya ini](tg://user?id={}).
Untuk mendapatkan info status dan update bot ini, anda dapat bergabung dengan channel kami [Ayra's Bot News](https://t.me/AyraBotNews)

Ada masalah atau butuh bantuan lebih?
Gabung grup [Emilia Official Support](https://t.me/EmiliaOfficial)!

Anda dapat menemukan daftar perintah yang tersedia dengan /help.

Jika Anda menikmati menggunakan saya, dan/atau ingin membantu saya bertahan hidup, tekan /donate untuk membantu \
mendanai/meningkatkan VPS saya!
""",
	"help_text": """
Hai! Nama saya adalah *Emilia*.
Saya adalah bot manajemen grup dengan beberapa kelebihan yang menyenangkan! Silahkan lihat berikut ini untuk beberapa ide dari \
hal-hal yang bisa saya bantu.

*Perintah utama* yang tersedia:
 - /start: mulai bot
 - /help: PM Anda dengan pesan ini.
 - /help <module name>: PM Anda dengan info tentang modul itu.
 - /donate: informasi tentang cara menyumbang!
 - /settings:
   - di PM: akan mengirimkan pengaturan Anda untuk semua modul yang didukung.
   - di grup: akan mengarahkan Anda ke pm, dengan semua pengaturan obrolan itu.


All commands can either be used with / or !.

Dan berikut ini:
""",
	"donate_text": """Hai, senang mendengar Anda ingin menyumbang!
Butuh banyak pekerjaan untuk [pencipta saya](tg://user?id=388576209) untuk membawa saya ke tempat saya sekarang, dan \
setiap sumbangan membantu dan memotivasi dia untuk membuat saya lebih baik.

Semua uang sumbangan akan diberikan ke VPS yang lebih baik untuk menjadi tuan rumah saya, dan atau beberapa makanan. \
Dia hanya orang biasa, jadi akan sangat membantu dia!

Jika anda memang berminat untuk donate, silahkan kunjungi ayrahikari.github.io/donations.html, Terima kasih 😁""",
	
# Help modules
	"language_help": """Tidak semua grup berbicara bahasa Indonesia; beberapa grup lebih suka Emilia menanggapi dalam bahasa mereka sendiri.

Di sinilah terjemahan masuk; Anda dapat mengubah sebagian besar balasan Emilia menjadi bahasa pilihan Anda!

Bahasa yang tersedia adalah:
- 🇮🇩 Indonesia
- 🇺🇸 English

Perintah yang tersedia adalah:
 - /setlang: atur bahasa pilihan Anda.""",

	"admin_help": """
 - /adminlist | /admins: daftar admin dalam obrolan

*Hanya admin:*
 - /pin: diam-diam pin pesan yang dibalas - tambahkan 'loud' atau 'notify' untuk memberikan notif kepada pengguna.
 - /unpin: buka pin pesan yang saat ini disematkan
 - /permapin <teks>: Sematkan pesan khusus melalui bot. Pesan ini dapat berisi markdown, dan dapat digunakan dalam balasan ke media untuk menyertakan tombol dan teks tambahan.
 - /permanentpin: Setel pin permanen untuk obrolan supergroup, ketika admin atau saluran telegram mengubah pesan yang disematkan, bot akan segera mengubah pesan yang disematkan.
 - /invitelink: dapatkan tautan undangan
 - /promote: mempromosikan pengguna yang dibalas
 - /demote: demosikan pengguna yang dibalas
""",
	"afk_help": """
 - /afk <alasan>: tandai dirimu sebagai AFK.
 - brb <alasan>: sama dengan perintah afk - tetapi bukan perintah.

Ketika ditandai sebagai AFK, sebutan apa pun akan dibalas dengan pesan untuk mengatakan Anda tidak tersedia!
""",
	"antiflood_help": """
 - /flood: Dapatkan pengaturan kontrol pesan beruntun saat ini

*Hanya admin:*
 - /setflood <int/'no'/'off'>: mengaktifkan atau menonaktifkan kontrol pesan beruntun
 - /setfloodmode <ban/kick/mute/tban/tmute> <value>: pilih tindakan yang akan diambil pada pengguna yang mengirim pesan beruntun.

 Note:
 - Value wajib di isi untuk tban dan tmute, Bisa menjadi:
    `4m` = 4 minutes
    `3h` = 4 hours
    `2d` = 2 days
    `1w` = 1 week
""",
	"backups_help": """
*Hanya admin:*
 - /import: balas ke file cadangan grup butler/marie/rose/emilia untuk mengimpor sebanyak mungkin, membuat transfer menjadi sangat mudah! \
 Catatan bahwa file/foto tidak dapat diimpor karena pembatasan telegram. Kecuali backup dari Emilia.
 - /export: export data grup, hanya bisa di lakukan 12 jam sekali.
""",
	"bans_help": """
 - /kickme: menendang pengguna yang mengeluarkan perintah

*Hanya admin:*
 - /ban <userhandle>: banned seorang pengguna. (via pegangan, atau balasan)
 - /sban <userhandle>: silent ban seorang pengguna, bot tidak akan membalas dan menghapus pesan sban Anda.
 - /tban <userhandle> x(m/h/d): melarang pengguna untuk x waktu. (via pegangan, atau balasan). m = menit, h = jam, d = hari.
 - /unban <userhandle>: unbanned seorang pengguna. (via pegangan, atau balasan)
 - /kick <userhandle>: menendang seorang pengguna, (via pegangan, atau balasan)
 - /skick <userhandle>: silent kick seorang pengguna, bot tidak akan membalas dan menghapus pesan skick Anda.
""",
	"blacklist_help": """
Blacklist digunakan untuk menghentikan pemicu tertentu dari yang dikatakan dalam kelompok. Kapan pun pemicu disebutkan, \
pesan akan segera dihapus. Sebuah kombo yang bagus terkadang memasangkan ini dengan filter peringatan!

*CATATAN:* daftar hitam tidak mempengaruhi admin grup.

 - /blacklist: Lihat kata-kata daftar hitam saat ini.

*Hanya admin:*
 - /addblacklist <pemicu>: Tambahkan pemicu ke daftar hitam. Setiap baris dianggap sebagai pemicu, jadi gunakan garis yang \
berbeda akan memungkinkan Anda menambahkan beberapa pemicu.
 - /unblacklist <pemicu>: Hapus pemicu dari daftar hitam. Logika newline yang sama berlaku di sini, sehingga Anda dapat \
menghapus beberapa pemicu sekaligus.
 - /rmblacklist <pemicu>: Sama seperti di atas.
""",
	"blstickers_help": """
Daftar hitam stiker digunakan untuk menghentikan stiker tertentu. Kapan pun stiker dikirim, pesan akan segera dihapus.

*CATATAN:* daftar hitam stiker tidak mempengaruhi admin grup.

 - /blsticker: Lihat daftar hitam stiker saat ini.

*Hanya admin:*
 - /addblsticker <pemicu>: Tambahkan pemicu stiker ke daftar hitam. Dapat ditambahkan melalui balas stiker.
 - /unblsticker <pemicu>: Hapus pemicu dari daftar hitam. Logika newline yang sama berlaku di sini, sehingga Anda dapat menghapus beberapa pemicu sekaligus.
 - /rmblsticker <pemicu>: Sama seperti di atas.

Catatan:
 - `<pemicu>` bisa menjadi `https://t.me/addstickers/<pemicu>` atau hanya `<pemicu>` atau balas pesan stikernya.
""",
	"supportcmd": """
*Command yang support saat ini*

*「 Untuk Member Biasa 」*
*Admin*
-> `/adminlist` | `/admins`

*Anti Flood*
-> `/flood`

*Blacklist*
-> `/blacklist`

*Blacklist Sticker*
-> `/blsticker`

*Filter*
-> `/filters`

*Notes*
-> `/get`
-> `/notes` | `/saved`

*Peraturan*
-> `/rules`

*Peringatan*
-> `/warns`
-> `/warnlist` | `/warnfilters`

*「 Hanya Untuk Admin 」*
*Admin*
-> `/adminlist`

*Anti Flood*
-> `/setflood`
-> `/flood`

*Banned*
-> `/ban`
-> `/tban` | `/tempban`
-> `/kick`
-> `/unban`

*Blacklist*
-> `/blacklist`
-> `/addblacklist`
-> `/unblacklist` | `/rmblacklist`

*Blacklist Sticker*
-> `/blsticker`
-> `/addblsticker`
-> `/unblsticker` | `/rmblsticker`

*Bisukan Pengguna*
-> `/mute`
-> `/unmute`
-> `/tmute`

*Disabler*
-> `/enable`
-> `/disable`
-> `/cmds`

*Filter*
-> `/filter`
-> `/stop`
-> `/filters`

*Notes*
-> `/get`
-> `/save`
-> `/clear`
-> `/notes` | `/saved`

*Penguncian*
-> `/lock`
-> `/unlock`
-> `/locks`

*Peraturan*
-> `/rules`
-> `/setrules`
-> `/clearrules`

*Pencadangan*
-> `/import`
-> `/export`

*Peringatan*
-> `/warn`
-> `/resetwarn` | `/resetwarns`
-> `/warns`
-> `/addwarn`
-> `/nowarn` | `/stopwarn`
-> `/warnlist` | `/warnfilters`
-> `/warnlimit`
-> `/warnmode`
""",
	"connection_help": """
Atur grup anda via PM dengan mudah.

 - /connect <chatid>: Hubungkan ke obrolan jarak jauh
 - /connection: Minta list command koneksi yang di dukung
 - /disconnect: Putuskan sambungan dari obrolan
 - /allowconnect on/yes/off/no: Izinkan menghubungkan pengguna ke grup
 - /helpconnect: Dapatkan bantuan command untuk koneksi
""",
	"filters_help": """
 - /filters: daftar semua filter aktif dalam obrolan ini.

*Hanya admin:*
 - /filter <kata kunci> <pesan balasan>: tambahkan filter ke obrolan ini. Bot sekarang akan membalas pesan itu jika 'kata kunci' disebutkan. Jika Anda membalas stiker dengan kata kunci, bot akan membalas dengan stiker itu.
CATATAN: semua filter kata kunci dalam huruf kecil. Jika Anda ingin kata kunci Anda menjadi kalimat, gunakan tanda kutip. seperti: /filter "hei di sana" ada apa?
 - /stop <kata kunci filter>: hentikan filter itu.
""",
	"disable_help": """
 - /cmds: periksa status perintah yang dinonaktifkan saat ini

*Hanya admin:*
 - /enable <cmd name>: aktifkan perintah itu
 - /disable <cmd name>: nonaktifkan perintah itu
 - /listcmds: daftar semua perintah toggleable yang memungkinkan
 - /disabledel: hapus pesan jika perintah dinonaktifkan
    """,
    "feds_help": """
Ah, manajemen grup. Semuanya menyenangkan, sampai mulai spammer masuk grup anda, dan Anda harus mencekalnya. Maka Anda perlu mulai melarang lebih banyak, dan lebih banyak lagi, dan itu terasa menyakitkan.
Tetapi kemudian Anda memiliki banyak grup, dan Anda tidak ingin spammer ini ada di salah satu grup Anda - bagaimana kamu bisa berurusan? Apakah Anda harus mencekalnya secara manual, di semua grup Anda?

Tidak lagi! Dengan federasi, Anda dapat membuat larangan dalam satu obrolan tumpang tindih dengan semua obrolan lainnya.
Anda bahkan dapat menunjuk admin federasi, sehingga admin tepercaya Anda dapat melarang semua obrolan yang ingin Anda lindungi.

*Perintah:*
 - /fedstat: Daftarkan semua federasi yang telah dilarang dari Anda.
 - /fedstat <user ID>: Dapatkan info federasi banned yang telah ditentukan oleh pengguna (bisa juga menyebut nama pengguna, mention, dan balasan).
 - /fedstat <user ID> <Fed ID>: Memberikan informasi tentang alasan larangan pengguna yang ditentukan dalam federasi itu. Jika tidak ada pengguna yang ditentukan, periksa pengirimnya.

*Hanya admin federasi:*
 - /newfed <fedname>: membuat federasi baru dengan nama yang diberikan. Pengguna hanya diperbolehkan memiliki satu federasi. Metode ini juga dapat digunakan untuk mengubah nama federasi. (maks. 64 karakter)
 - /delfed: menghapus federasi Anda, dan informasi apa pun yang berkaitan dengannya. Tidak akan membatalkan pencekalan pengguna yang diblokir.
 - /fedinfo <FedID>: informasi tentang federasi yang ditentukan.
 - /joinfed <FedID>: bergabung dengan obrolan saat ini ke federasi. Hanya pemilik obrolan yang dapat melakukan ini. Setiap obrolan hanya bisa dalam satu federasi.
 - /leavefed <FedID>: meninggalkan federasi yang diberikan. Hanya pemilik obrolan yang dapat melakukan ini.
 - /fbroadcast <teks>: Broadcast teks ke seluruh grup yang join federasi tsb.
 - /fban <user>: melarang pengguna dari semua federasi tempat obrolan ini berlangsung, dan eksekutor memiliki kendali atas.
 - /unfban <user>: batalkan pengguna dari semua federasi tempat obrolan ini berlangsung, dan bahwa pelaksana memiliki kendali atas.
 - /setfrules: Atur peraturan federasi.
 - /frules: Lihat peraturan federasi.
 - /chatfed: Lihat federasi pada obrolan saat ini.
 - /fedadmins: Tampilkan admin federasi.
 - /fednotif <on/off>: Atur federasi notif di PM ketika ada pengguna yang di fban/unfban.
 - /fedchats: Dapatkan semua chat yang terhubung di federasi.

*Hanya pemilik federasi:*
 - /fpromote <user>: mempromosikan pengguna untuk memberi fed admin. Pemilik fed saja.
 - /fdemote <user>: menurunkan pengguna dari admin federasi ke pengguna normal. Pemilik fed saja.
 - /fbanlist: Menampilkan semua pengguna yang di fban pada federasi saat ini. Jika Anda menginginkan mode yang berbeda, gunakan /fbanlist
 - /importfbans: Balas file pesan cadangan federasi untuk mengimpor list banned ke federasi sekarang.
 - /subfed <fedid>: untuk berlangganan federasi, dapat berlangganan beberapa federasi.
 - /unsubfed <fedid>: berhenti berlangganan federasi itu.
 - /fedsubs: periksa semua yang berlangganan federasi saat ini.
 - /myfeds: dapatkan semua feds Anda, hanya untuk pemilik feds
""",
    "globalbans_help": """
*Hanya admin:*
 - /gbanstat <on/off/yes/no>: Akan menonaktifkan efek larangan global pada grup Anda, atau mengembalikan pengaturan Anda saat ini.

Larangan global, juga dikenal sebagai larangan global, digunakan oleh pemilik bot untuk melarang spammer di semua grup. Ini membantu melindungi \
Anda dan grup Anda dengan menghapus spam banjir secepat mungkin. Mereka dapat dinonaktifkan untuk grup Anda dengan memanggil \
/gbanstat
""",
	"locks_help": """
 - /locktypes: daftar kemungkinan tipe kunci

*Admin only:*
 - /lock <type>: mengunci sesuatu dengan jenis tertentu (tidak tersedia secara pribadi)
 - /unlock <type>: membuka kunci sesuatu dengan jenis tertentu (tidak tersedia secara pribadi)
 - /locks: daftar kunci saat ini di obrolan ini.
 - /lockwarns <on/off/yes/no>: apakah peringati atau tidak jika pengguna mengirim pesan terkunci.

Kunci dapat digunakan untuk membatasi pengguna grup.
seperti:
Mengunci url akan otomatis menghapus semua pesan dengan url yang belum masuk daftar putih, mengunci stiker akan menghapus semua \
stiker, dll.
Mengunci bot akan menghentikan non-admin menambahkan bots ke obrolan.
""",
	"logchannel_help": """
*Hanya admin:*
- /logchannel: dapatkan info saluran log
- /setlog: mengatur saluran log.
- /unsetlog: menonaktifkan saluran log.

Mengatur saluran log dilakukan dengan:
- menambahkan bot ke saluran yang diinginkan (sebagai admin!)
- Kirimkan /setlog di saluran
- Teruskan /setlog ke grup
""",
	"MARKDOWN_HELP": """
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
<code>[satu](buttonurl:contoh.com)
[dua](buttonurl:google.com:same)</code>
Ini akan membuat dua tombol pada satu baris, bukan satu tombol per baris.

Perlu diingat bahwa pesan Anda <b>HARUS</b> berisi beberapa teks selain hanya sebuah tombol!
""",
	"misc_help": """
 - /id: dapatkan ID grup saat ini. Jika digunakan dengan membalas pesan, dapatkan id pengguna itu.
 - /runs: balas string acak dari larik balasan.
 - /lari: sama seperti runs.
 - /slap: menampar pengguna, atau ditampar jika bukan balasan.
 - /time <tempat>: memberi waktu lokal di tempat yang ditentukan.
 - /info: mendapatkan informasi tentang seorang pengguna.
 - /stickerid: balas pesan stiker untuk mendapatkan id stiker
 - /ping: mengecek kecepatan bot

 - /markdownhelp: ringkasan singkat tentang cara kerja markdown di telegram - hanya dapat dipanggil dalam obrolan pribadi.
""",
	"msgdel_help": """
*Hanya admin:*
 - /del: menghapus pesan yang Anda balas
 - /purge: menghapus semua pesan antara ini dan membalas pesan.
 - /purge <integer X>: menghapus pesan yang dijawab, dan pesan X yang mengikutinya.
""",
	"mute_help": """
*Hanya admin:*
 - /mute <userhandle>: membungkam seorang pengguna. Bisa juga digunakan sebagai balasan, mematikan balasan kepada pengguna.
 - /tmute <userhandle> x(m/h/d): membisukan pengguna untuk x waktu. (via handle, atau membalas). m = menit, h = jam, d = hari.
 - /unmute <userhandle>: batalkan membungkam pengguna. Bisa juga digunakan sebagai balasan, mematikan balasan kepada pengguna.
""",
	"notes_help": """
 - /get <notename>: dapatkan catatan dengan notename ini, gunakan ``noformat`` di akhir untuk mendapatkan note tanpa format
 - #<notename>: sama seperti /get
 - /notes atau /saved: daftar semua catatan yang disimpan dalam obrolan ini

*Hanya admin:*
 - /save <notename> <notedata>: menyimpan recordsata sebagai catatan dengan nama notename
Sebuah tombol dapat ditambahkan ke catatan dengan menggunakan sintaks markdown standar tautan - tautan harus ditambahkan dengan \
bagian `buttonurl:`, Seperti: `[tulisannya](buttonurl:contoh.com)`. Cek /markdownhelp untuk info lebih lanjut.
 - /save <notename>: simpan pesan yang dijawab sebagai catatan dengan nama nama file
 - /clear <notename>: hapus catatan dengan nama ini
 - /privatenote <on/yes/off/no> <?del>: apakah atau tidak untuk mengirim catatan di PM. Tulis `del` di samping on/off untuk menghapus pesan hashtag pada grup.
""",
	"reporting_help": """
 - /report <alasan>: membalas pesan untuk melaporkannya ke admin.
 - @admin: membalas pesan untuk melaporkannya ke admin.
CATATAN: tidak satu pun dari ini akan dipicu jika digunakan oleh admin

*Hanya admin:*
 - /reports <on/off>: ubah pengaturan laporan, atau lihat status saat ini.
   - Jika selesai di PM, matikan status Anda.
   - Jika dalam obrolan, matikan status obrolan itu.
""",
	"rss_help": """
 - /addrss <link>: tambahkan tautan RSS ke langganan.
 - /removerss <link>: menghapus tautan RSS dari langganan.
 - /rss <link>: menunjukkan data tautan dan entri terakhir, untuk tujuan pengujian.
 - /listrss: menampilkan daftar rss feed yang saat ini dilanggankan oleh obrolan.

CATATAN: Dalam grup, hanya admin yang dapat menambah/menghapus tautan RSS ke langganan grup
""",
	"rules_help": """
 - /rules: dapatkan aturan untuk obrolan ini.

*Hanya admin:*
 - /setrules <aturan Anda di sini>: atur aturan untuk obrolan ini.
 - /clearrules: kosongkan aturan untuk obrolan ini.
 - /privaterules <yes/no/on/off>: apakah peraturan akan di kirim ke PM. Default: aktif.
""",
	"userinfo_help": """
 - /setbio <text>: saat membalas, akan menyimpan bio pengguna lain
 - /bio: akan mendapatkan biodata Anda atau pengguna lain. Ini tidak dapat diatur sendiri.
 - /setme <text>: akan mengatur info Anda
 - /me: akan mendapatkan info Anda atau pengguna lain
""",

# warns
	"CURRENT_WARNING_FILTER_STRING": "<b>Filter peringatan saat ini dalam obrolan ini:</b>\n",
	"warns_help": """
 - /warns <userhandle>: dapatkan nomor, dan alasan pengguna peringatan.
 - /warnlist: daftar semua filter peringatan saat ini

*Hanya admin:*
 - /warn <userhandle>: memperingatkan pengguna. Setelah 3 peringatan, pengguna akan dicekal dari grup. Bisa juga digunakan \
sebagai balasan.
 - /resetwarn <userhandle>: mengatur ulang peringatan untuk pengguna. Bisa juga digunakan sebagai balasan.
 - /addwarn <kata kunci> <pesan balasan>: mengatur filter peringatan pada kata kunci tertentu. Jika Anda ingin kata kunci Anda \
menjadi kalimat, mencakup dengan tanda kutip, seperti: `/addwarn "sangat marah" Ini adalah pengguna yang marah`. 
 - /nowarn <keyword>: hentikan filter peringatan
 - /warnlimit <num>: mengatur batas peringatan
 - /warnmode <kick/ban/mute>: Jika diatur, ketika pengguna maka melebihi batas peringatan akan menghasilkan mode tersebut.
""",
	"weather_lang": "id",
	"weather_help": """
 - /cuaca <kota>: mendapatkan info cuaca di tempat tertentu
""",
	"WELC_HELP_TXT": "Pesan selamat datang/selamat tinggal grup Anda dapat dipersonalisasi dengan berbagai cara. Jika Anda menginginkan pesan untuk dihasilkan secara individual, seperti pesan selamat datang default, Anda dapat menggunakan * variabel * ini:\n - `{{first}}`: ini mewakili nama *pertama* pengguna\n - `{{last}}`: ini mewakili nama *terakhir* pengguna. Default ke nama *depan* jika pengguna tidak memiliki nama terakhir.\n - `{{fullname}}`: ini mewakili nama *penuh* pengguna. Default ke *nama depan* jika pengguna tidak memiliki nama terakhir.\n - `{{username}}`: ini mewakili *nama pengguna* pengguna. Default ke *sebutan* jika pengguna jika tidak memiliki nama pengguna.\n - `{{mention}}`: ini hanya *menyebutkan* seorang pengguna - menandai mereka dengan nama depan mereka.\n - `{{id}}`: ini mewakili *id* pengguna\n - `{{count}}`: ini mewakili *nomor anggota* pengguna.\n - `{{chatname}}`: ini mewakili *nama obrolan saat ini*.\n\nSetiap variabel HARUS dikelilingi oleh `{{}}` untuk diganti.\nPesan sambutan juga mendukung markdown, sehingga Anda dapat membuat elemen apa pun teba/miring/kode/tautan. Tombol juga didukung, sehingga Anda dapat membuat sambutan Anda terlihat mengagumkan dengan beberapa tombol pengantar yang bagus.\nUntuk membuat tombol yang menautkan ke aturan Anda, gunakan ini: `[Peraturan](buttonurl:t.me/{}?start=group_id)`. Cukup ganti `group_id` dengan id grup Anda, yang dapat diperoleh melalui /id, dan Anda siap untuk pergi. Perhatikan bahwa id grup biasanya didahului oleh tanda `-`; ini diperlukan, jadi tolong jangan hapus itu.\nJika Anda merasa senang, Anda bahkan dapat mengatur gambar/gif/video/pesan suara sebagai pesan selamat datang dengan membalas media yang diinginkan, dan memanggil /setwelcome.",
    "welcome_help": """
*Hanya admin:*
 - /welcome <on/off>: mengaktifkan/menonaktifkan pesan selamat datang.
 - /goodbye <on/off>: mengaktifkan/menonaktifkan pesan selamat tinggal.
 - /welcome: menunjukkan pengaturan selamat datang saat ini, tanpa pemformatan - berguna untuk mendaur ulang pesan selamat datang Anda!
 - /goodbye: penggunaan yang sama dan sama seperti /welcome.
 - /setwelcome <beberapa teks>: mengatur pesan sambutan khusus. Jika digunakan untuk membalas media, gunakan media itu.
 - /setgoodbye <beberapa teks>: mengatur pesan selamat tinggal khusus. Jika digunakan untuk membalas media, gunakan media itu.
 - /resetwelcome: reset ulang ke pesan selamat datang default.
 - /resetgoodbye: reset ulang ke pesan selamat tinggal default.
 - /cleanwelcome <on/off>: menghapus pesan sambutan lama; ketika orang baru bergabung, pesan lama dihapus.
 - /cleanservice <on/off/yes/no>: menghapus semua pesan layanan; itu adalah "x bergabung kedalam grup" yang Anda lihat ketika orang-orang bergabung.
 - /welcomemute <on/ya/off/ga>: semua pengguna yang bergabung akan di bisukan; sebuah tombol ditambahkan ke pesan selamat datang bagi mereka untuk mensuarakan diri mereka sendiri. Ini membuktikan bahwa mereka bukan bot!
 - /welcomemutetime <Xw/d/h/m>: jika pengguna belum menekan tombol "unmute" di pesan sambutan setelah beberapa waktu ini, mereka akan dibunyikan secara otomatis setelah periode waktu ini.
   Catatan: jika Anda ingin mengatur ulang waktu bisu menjadi selamanya, gunakan `/welcomemutetime 0m`. 0 == abadi!
 - /setmutetext <teks tombol>: Ubahsuaikan untuk tombol "Klik disini untuk mensuarakan" yang diperoleh dari mengaktifkan welcomemute.
 - /resetmutetext: Reset teks tombol unmute menjadi default.

Baca /welcomehelp dan /markdownhelp untuk mempelajari tentang memformat teks Anda dan menyebutkan pengguna baru saat bergabung!

Jika Anda ingin menyimpan gambar, gif, atau stiker, atau data lain, lakukan hal berikut:
Balas pesan stiker atau data apa pun yang Anda inginkan dengan teks `/setwelcome`. Data ini sekarang akan dikirim untuk menyambut pengguna baru.

Tip: gunakan `/welcome noformat` untuk mengambil pesan sambutan yang belum diformat.
Ini akan mengambil pesan selamat datang dan mengirimkannya tanpa memformatnya; memberi Anda markdown mentah, memungkinkan Anda untuk mengedit dengan mudah.
Ini juga berfungsi dengan /goodbye.
""",
	"cleaner_help": """
*Admin only:*
 - /cleanbluetext <on/off>: Hapus semua pesan biru.

Catatan:
- Fitur ini dapat merusak bot orang lain
""",
	"exclusive_help": """
 - /stickerid: balas pesan stiker di PM untuk mendapatkan id stiker
 - /ping: mengecek kecepatan bot
 - /ramalan: cek ramalan kamu hari ini
 - /tr <dari>-<ke> <teks>: terjemahkan teks yang ditulis atau di balas untuk bahasa apa saja ke bahasa yang dituju
 atau bisa juga dengan
 - /tr <ke> <teks>: terjemahkan teks yang ditulis atau di balas untuk bahasa apa saja ke bahasa yang dituju
 - /wiki <teks>: mencari teks yang ditulis dari sumber wikipedia
 - /kbbi <teks>: mencari teks yang ditulis dari kamus besar bahasa indonesia
 - /kbgaul <teks>: mencari arti dan definisi yang ditulis dari kitab gaul, tulis `/kbgaul` untuk mendapatkan kata trending dan terbaik
 - /ud <teks>: cari arti dari urban dictionary
"""
}



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


RAMALAN_STRINGS = (
	"Tertawalah sepuasnya sebelum hal itu dilarang 😆",
	"Bila Anda membahagiakan seseorang, Anda sendiri akan merasa bahagia.\nBegitulah dunia bekerja 😊",
	"Nostalgia masa muda hari ini akan membuat Anda tersenyum 🌸",
	"Lanjutkan terus pekerjaan Anda, niscaya akan selesai juga.\nOke, saya akui ramalan hari ini agak jayus 😝",
	"Mengetahui bahwa ilusi bukanlah kenyataan tidak membuat keindahannya berkurang 💖",
	"Anda akan mengalami kejadian aneh hari ini.\nDan itu tidak termasuk mendapatkan ramalan dari Emilia 😜",
	"Akhirnya ada kesempatan untuk beristirahat...\ndan mendengar ramalan dari Emilia 😉",
	"Pencarian Anda sudah selesai.\nAnda telah menemukan sahabat sejati (saya) 😀",
	"Anda akan menunjukkan bahwa Anda kuat melewati tantangan demi tantangan.",
	"Anda hanyalah setitik air di tengah lautan luas.\nTapi setitik air pun bisa bikin gadget rusak 😱 💦",
	"Anda akan mencoba hal baru hari ini.\nTapi maaf, mencoba makanan gratis di supermarket tidak termasuk 🍦🚫",
	"Kirimlah pesan ke seorang teman lama hari ini.",
	"Akan ada sesuatu yang baru di lingkungan sekitar Anda 🏡",
	"Traktirlah diri sendiri 🍭",
	"Semua hal ada solusinya, kalau Anda terbuka untuk berubah.",
	"Karma baik menghampiri Anda minggu ini.\nTapi hati-hati, karma itu rapuh seperti barang pecah belah.",
	"Habiskanlah waktu di luar rumah hari ini.\nSepertinya di luar sana indah... kalau tidak hujan.",
	"Jika Anda mendengarkan dengan sungguh-sungguh, angin akan memberikan semua jawaban atas pertanyaan Anda 💨",
	"Pergilah ke tempat yang belum pernah Anda kunjungi, walaupun tempat itu hanya sepelemparan batu dari rumah Anda.",
	"Anda akan menerima kabar baik, tapi mungkin Anda harus mencari dari apa yang tersirat.",
	"Anda akan segera menemukan apa yang Anda cari.\nKalau Anda bisa menemukan kacamata Anda.",
	"Pergilah ke suatu tempat baru.\nApa yang akan Anda temukan pasti akan mengesankan.",
	"Kesempatan akan muncul bila Anda tahu ke mana harus melihat 👀",
	"Hari ini Anda akan menjadi keren 😎\nYah, nggak terlalu beda dengan hari-hari lain 😉",
	"Hal-hal positif akan muncul di hidup Anda hari ini.\nTapi jangan lupa, di dalam komposisi sebuah atom selalu ada atom negatif 🔬😀",
	"Penuhilah diri hanya dengan kebaikan, baik dalam pikiran, perkataan, perbuatan, maupun pertwitteran 🐥",
	"Bersiaplah untuk menerima hal-hal menyenangkan hari ini 😎",
	"Waktunya belajar keterampilan dan topik baru.",
	"Video YouTube favorit Anda masih belum dibuat.",
	"Ketika ragu, Google dulu 😉",
	"Dua hari dari sekarang, besok akan jadi kemarin 😌",
	"Perhatikan detail-detail.\nPasti banyak hal menarik yang Anda bisa temukan.",
	"Wah, Anda belum beruntung.\nSilakan coba lagi 😉",
	"Buatlah keputusan dengan mendengarkan dan menyelaraskan hati maupun pikiran Anda.",
	"Biasanya maling akan teriak maling.",
	"Anda tidak akan diberi kalau tidak meminta 👐",
	"Nostalgia masa muda hari ini akan membuat Anda tersenyum 🌸",
	"Sahabat sejati Anda berada dalam jangkauan.\nSebenarnya, Anda sedang membaca ramalan darinya 😊",
	"Masa depan Anda akan dipenuhi kesuksesan 💎\nTapi hati-hati, keserakahan bisa menghancurkan semuanya 💰",
	"Hari ini adalah hari esok yang Anda nantikan kemarin.",
	"Bersyukur akan membuat kita bahagia.\nKatakan terima kasih pada seseorang hari ini.",
	"Hari ini, dunia akan jadi milik Anda 🌍\nJangan lupa menjadikannya indah untuk orang lain 😊",
	"Petualangan baru akan segera menghampiri Anda.",
	"Semakin banyak yang Anda katakan, semakin sedikit yang akan mereka ingat.",
	"Hari ini, jadilah superhero untuk seorang anak kecil.",
	"Makanan yang kelihatannya aneh itu mungkin sebenarnya enak banget.",
	"Hari ini, ambillah rute yang lain dari biasanya.",
	"Waktunya mengekspresikan kreativitas Anda.",
	"Jodoh Anda lebih dekat dari yang Anda kira 💞",
	"Waktunya belajar keterampilan dan topik baru.",
	"Hal-hal positif akan muncul di hidup Anda hari ini.\nTapi jangan lupa, di dalam komposisi sebuah atom selalu ada atom negatif 🔬😀",
	"Waktunya berlibur bersama orang-orang kesayangan Anda ✈️",
	"Besok akan menjadi hari yang lebih menyenangkan daripada hari Anda yang paling menyebalkan.",
	"Jangan cari peruntungan di situs abal-abal atau SMS mencurigakan.",
	"Kejadian yang tak terduga akan menghampiri hidup Anda.",
	"Hadiah berharga tengah menanti Anda.\nTapi tampaknya hadiah tersebut sangat sabar menanti.",
	"Keluarga Anda sangat kangen pada Anda.\nTeleponlah mereka, jangan kasih tahu ini ide saya 😉",
	"Hari yang baik untuk memperjuangkan kebenaran.",
	"Semua hal ada solusinya, kalau Anda terbuka untuk berubah.",
	"Hewan peliharaan akan menambah kebahagiaan Anda 🐱🐹🐔",
	"Ketika Anda jatuh, bangun lagi.\nDan jangan lupa bersihkan lukanya 👍",
	"Minumlah cukup air hari ini.\nIni bukan benar-benar ramalan, saya hanya ingin Anda tetap sehat 😊",
	"Biarkan intuisi Anda menunjukkan jalan.\nTapi tulisan berisi syarat dan ketentuan yang berlaku harus dibaca baik-baik.",
	"Hal baik akan datang bagi mereka yang...\nSabar.",
	"Waktu yang tepat untuk berhenti bermalas-malasan 🏃‍♀️",
	"Waktunya bernostalgia dengan buku favorit masa kecil Anda.",
	"Hari ini, Anda akan melihat dunia dengan mata terbuka 👀",
	"Seorang asing akan datang ke dalam hidup Anda dan membuat kesan di sana.",
	"Hari yang baik untuk mendengarkan intuisi daripada nasihat.",
	"Hati-hati dengan kata-kata manis orang yang baru Anda kenal.",
	"Seluruh alam semesta akan bekerja sama untuk membantu Anda 🙏",
	"Waktu yang tepat untuk jadi diri Anda sendiri.",
	"Walaupun seperti menyebalkan, orang terdekat Anda jauh lebih peduli pada Anda daripada dia yang tampak manis namun cuma basa-basi.",
	"Kejarlah mentari, niscaya kegelapan akan Anda lewati.",
	"Hidup Anda akan diabadikan dalam sebuah film dokumenter.",
	"Suara tawa anak-anak akan menceriakan hari Anda.",
	"Saatnya mencari hobi baru.",
	"Cinta tidaklah statis.\nIa dinamis seperti arus listrik bolak-balik 💖",
	"Penantian akan segera berakhir 😁",
	"Perhatikan detail-detail.\nPasti banyak hal menarik yang Anda bisa temukan.",
	"Dua hari dari sekarang, besok akan jadi kemarin 😌",
	"Anda akan mendengar sebuah lagu yang membuat Anda tersenyum berhari-hari.",
	"Gapailah cita-cita.\nKecuplah mimpi 😘🌛",
	"Semua mawar pasti berduri 🌹\nJadilah seseorang yang selalu siap memotong duri tersebut.",
	"Banyak orang kagum pada bakat dan kemampuan Anda... lebih dari yang Anda sadari 👏",
	"Lakukan yang Anda sukai hari ini 💞\nSaya janji Anda akan merasa bahagia, walau hanya sesaat 😃",
	"Keberuntungan akan datang bagi orang yang pemberani.",
	"Anda tidak akan di beri kalau tidak meminta 👐",
	"Cobalah menggambar sesuatu ✏️\nAnda akan menikmatinya.",
	"Saatnya mengubah gaya berpakaian Anda? 👠",
	"Cobalah konsekuen dengan semua kata-kata Anda.",
	"Hari yang tepat untuk menghargai dan mensyukuri hal-hal kecil.",
	"Malam ini Anda akan mimpi indah.\nTapi saya nggak janji Anda bisa ingat mimpinya 😉",
	"Anda akan menunjukkan bahwa Anda kuat melewati tantangan demi tantangan.",
	"Hari yang tepat untuk memberi tahu keluarga dan teman-teman Anda tentang saya 😉",
	"beristirahatlah sejenak dan ngobrollah dari hati ke hati dengan orang-orang yang Anda sayangi 👨‍👩‍👧‍👦",
	"Semua akan berjalan sesuai rencana.",
	"Pergilah ke suatu tempat baru.\nApa yang akan Anda temukan pasti akan mengesankan.",
	"Ini salah satu waktu di mana Anda bertanya-tanya tentang arti hidup.",
	"Jangan sampai dikelabui ramalan 😏"
)

RAMALAN_FIRST = (
	"Saya bukan paranormal, tapi memang saya bisa meramal sedikit-sedikit.\n",
	"Sebuah ramalan siap meluncur.\n",
	"Ramalan kali ini untuk Anda.\n"
)
