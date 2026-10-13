# Arxitektura va kengaytirish

```text
Bot / KytsuClient
       │
AsyncTransport (httpx + envelope + errors)
       │
KytsuBot HTTP API

Dispatcher
  └── Router
       ├── message observer
       ├── update observer
       └── error observer
```

Qatlamlar ataylab ajratilgan:

- `transport.py` HTTP, token va JSON envelope uchun;
- `types.py` API modellarini Python obyektlariga aylantiradi;
- `bot.py` bot tokenli metodlar;
- `client.py` user/account/creator metodlari;
- `filters.py` handler filtrlari;
- `router.py` registratsiya va dependency injection;
- `dispatcher.py` polling, ACK va lifecycle.

Yangi update turi qo'shilganda:

1. `types.py`da typed model yaratiladi;
2. `Update.from_dict()` payloadni parse qiladi;
3. `Router`ga yangi observer qo'shiladi;
4. `Dispatcher.feed_update()` eventni Bot bilan bog'laydi;
5. test va `docs/ai-reference.md` yangilanadi.

Public API imkon qadar `kytsubot.__init__` orqali eksport qilinadi. Ichki modullarga bog'lanib
qolmaslik kerak. API'dan kelgan noma'lum update turi `str` sifatida saqlanadi, bu server yangi
tur chiqarganda eski SDK'ning butunlay yiqilmasligiga yordam beradi.

