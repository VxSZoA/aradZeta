import asyncio, json, os
from highrise import BaseBot, User, Position
from highrise.models import Item, SessionMetadata
from highrise.webapi import *  # noqa

OWNER = os.environ.get("OWNER_USERNAME", "i.t4").strip().lstrip("@")
DATA = "data.json"

# ---------- دنس‌ها ----------
# ترتیب همین لیسته؛ شماره هر دنس = جای اون توی لیست (با !dances می‌بینی)
GROUPS = [
    ("dance-", "macarena floss tiktok2 tiktok8 tiktok9 tiktok10 tiktok11 blackpink pennywise russian shoppingcart weird zombie employee handsup kawai touch sexy icecream wild metal orangejustice jinglebell anime creepypuppet spiritual smoothwalk singlelady"),
    ("emote-", "ghost-idle float hello wave kiss laughing sad shy tired lust greedy model cutey curtsy bow flex gagging judochop theatrical snowball snowangel hot hug no yes confused charging frollicking teleporting telekinesis superpose snake maniac embarrassed boo zombierun shrink swordfight stargazer slap think peekaboo ropepull death death2 fainting gordonshuffle hearteyes heartfingers heartshape celebrationstep apart wings iceskating timejump proposing pose1 pose3 pose5 pose7 pose8"),
    ("idle-", "dance-casual dance-tiktok7 dance-swinging dance-tiktok4 loop-tapdance loop-aerobics loop-happy loop-sad loop-shy loop-tired loop-annoyed guitar uwu fighter hero enthusiastic angry singing"),
    ("emoji-", "angry cursing flex gagging celebrate crying dizzy eyeroll halo hadoken lying naughty pray punch sing scared shake sleep thumbsup arrogance poop"),
]
KEY_OVERRIDE = {"emote-ghost-idle": "ghostfloat"}
DUR = {}          # مدت دقیق هر دنس (ثانیه) اگه خواستی: {"ghostfloat": 20}
DEFAULT_DUR = 10  # مدت پیش‌فرض بین هر تکرار

EMOTES = {}  # key: (emote_id, duration)
for prefix, names in GROUPS:
    for n in names.split():
        eid = prefix + n
        key = KEY_OVERRIDE.get(eid) or n.replace("dance-", "", 1).replace("loop-", "", 1)
        if key in EMOTES:
            key = prefix.strip("-") + "_" + key
        EMOTES[key] = (eid, DUR.get(key, DEFAULT_DUR))

# صفحه‌بندی لیست برای چت (حداکثر ~۲۳۰ کاراکتر)
PAGES, _cur = [], ""
for _i, _k in enumerate(EMOTES, 1):
    _t = f"{_i}.{_k} "
    if len(_cur) + len(_t) > 230:
        PAGES.append(_cur)
        _cur = ""
    _cur += _t
PAGES.append(_cur)

LOOP_MESSAGES = ["به روم ما خوش اومدید 💜", "قوانین رو رعایت کنید 🙏"]
LOOP_EVERY = 120  # ثانیه


def load():
    if os.path.exists(DATA):
        return json.load(open(DATA))
    return {"admins": [], "spots": {}}


def save(d):
    json.dump(d, open(DATA, "w"))


class Bot(BaseBot):
    async def on_start(self, session_metadata: SessionMetadata) -> None:
        self.db = load()
        self.dances = {}  # user_id -> task
        asyncio.create_task(self.msg_loop())

    async def msg_loop(self):
        i = 0
        while True:
            await asyncio.sleep(LOOP_EVERY)
            await self.highrise.chat(LOOP_MESSAGES[i % len(LOOP_MESSAGES)])
            i += 1

    def is_admin(self, user):
        return user.username == OWNER or user.username in self.db["admins"]

    async def on_user_join(self, user: User, position) -> None:
        await self.highrise.chat(f"خوش اومدی {user.username} 🎉")

    # ---------- دنس بی‌پایان ----------
    async def dance_loop(self, user_id, emote, dur):
        while True:
            try:
                await self.highrise.send_emote(emote, user_id)
            except Exception:
                return
            await asyncio.sleep(dur)

    def stop_dance(self, uid):
        t = self.dances.pop(uid, None)
        if t:
            t.cancel()

    async def user_pos(self, uid):
        for u, p in (await self.highrise.get_room_users()).content:
            if u.id == uid:
                return p

    async def find_user(self, name):
        for u, p in (await self.highrise.get_room_users()).content:
            if u.username.lower() == name.lower().lstrip("@"):
                return u
    
    async def on_chat(self, user: User, message: str) -> None:
        parts = message.strip().split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]

        # --- دنس (برای همه): فقط اسم یا شماره دنس رو بنویسن ---
        word = message.strip().lower()
        names = list(EMOTES)
        key = None
        if word in EMOTES:
            key = word
        elif word.isdigit() and 1 <= int(word) <= len(names):
            key = names[int(word) - 1]
        elif cmd == "!dance" and args and args[0].lower() in EMOTES:
            key = args[0].lower()
        if key:
            self.stop_dance(user.id)
            eid, dur = EMOTES[key]
            self.dances[user.id] = asyncio.create_task(self.dance_loop(user.id, eid, dur))
            return
        if cmd == "!stop":
            self.stop_dance(user.id)
            return
        if cmd == "!dances":
            p = int(args[0]) if args and args[0].isdigit() else 1
            p = min(max(p, 1), len(PAGES))
            await self.highrise.chat(f"[{p}/{len(PAGES)}] " + PAGES[p - 1])
            return
        if cmd == "!admins":
            await self.highrise.chat("👑 اونر: " + OWNER + " | ادمین‌ها: " + (", ".join(self.db["admins"]) or "ندارد"))
            return
        if cmd == "!fun":
            import random
            await self.highrise.chat(random.choice(["😂 جوک: ...", "🎲 عدد تو: %d" % random.randint(1, 100)]))
            return

        # --- از اینجا به بعد فقط ادمین ---
        if not self.is_admin(user):
            return

        if cmd in ("!ban", "!kick") and args:
            t = await self.find_user(args[0])
            if t:
                act = "ban" if cmd == "!ban" else "kick"
                await self.highrise.moderate_room(t.id, act, 3600) if act == "ban" else await self.highrise.moderate_room(t.id, act)
        elif cmd == "!unban" and args:
            pass  # unban به user_id نیاز داره؛ ایدی رو از لاگ/ذخیره بگیر

        elif cmd == "!setspot" and args:
            p = await self.user_pos(user.id)
            self.db["spots"][args[0]] = [p.x, p.y, p.z, p.facing]
            save(self.db)
            await self.highrise.chat(f"موقعیت {args[0]} ذخیره شد")
        elif cmd == "!tp" and len(args) >= 2:
            t = await self.find_user(args[0])
            s = self.db["spots"].get(args[1])
            if t and s:
                await self.highrise.teleport(t.id, Position(*s))
        elif cmd == "!tpall":
            # !tpall -> همه میان پیش خودت | !tpall نام -> همه میرن به اون موقعیت
            if args:
                s = self.db["spots"].get(args[0])
                dest = Position(*s) if s else None
            else:
                dest = await self.user_pos(user.id)
            if dest:
                my_id = getattr(self.highrise, "my_id", None)
                for u, _ in (await self.highrise.get_room_users()).content:
                    if u.id in (user.id, my_id):
                        continue
                    try:
                        await self.highrise.teleport(u.id, dest)
                    except Exception:
                        pass
            else:
                await self.highrise.chat("موقعیت پیدا نشد")
        elif cmd == "!tpme" and args:
            s = self.db["spots"].get(args[0])
            if s:
                await self.highrise.teleport(user.id, Position(*s))

        elif cmd == "!outfit" and args:
            # !outfit shirt-n_a,pants-n_b,...  (آیدی آیتم‌ها)
            items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1)
                     for i in args[0].split(",")]
            await self.highrise.set_outfit(items)

        # --- ست ادمین (فقط اونر) ---
        elif cmd == "!addadmin" and args and user.username == OWNER:
            n = args[0].lstrip("@")
            if n not in self.db["admins"]:
                self.db["admins"].append(n)
                save(self.db)
            await self.highrise.chat(f"{n} ادمین شد ✅")
        elif cmd == "!deladmin" and args and user.username == OWNER:
            n = args[0].lstrip("@")
            if n in self.db["admins"]:
                self.db["admins"].remove(n)
                save(self.db)
