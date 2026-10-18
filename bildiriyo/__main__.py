"""Bildiriyo: kamu ilanlarını tarar, yenilerini Telegram'a gönderir.

Kural: bir ilan ancak Telegram'a başarıyla gönderildikten sonra "görüldü"
sayılır. Gönderim başarısız olursa bir sonraki çalışmada tekrar denenir.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone

from . import state
from .classify import GREEN, GREY, YELLOW, classify
from .http import session
from .models import Ilan
from .sources import SOURCES
from .telegram import Telegram, esc

TR = timezone(timedelta(hours=3))
ALERT_AFTER = 3  # art arda bu kadar hatalı çalışmadan sonra uyar (~1 saat)
HEARTBEAT_HOUR = 9
ICON = {GREEN: "🟢", YELLOW: "🟡", GREY: "⚪"}
HEAD = {GREEN: "SİZE UYGUN OLABİLİR", YELLOW: "YENİ KAMU İLANI", GREY: ""}

log = logging.getLogger("bildiriyo")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_one(i: Ilan, level: str, kw: str) -> str:
    label = SOURCES[i.source].LABEL
    lines = [f"{ICON[level]} <b>{HEAD[level]}</b> · {esc(label)}", f"<b>{esc(i.title)}</b>"]
    if i.org and i.org.lower() not in i.title.lower():
        lines.append(f"🏢 {esc(i.org)}")
    if i.deadline:
        lines.append(f"📅 Başvuru: {esc(i.deadline)}")
    if i.note:
        lines.append(f"ℹ️ {esc(i.note)}")
    if kw:
        lines.append(f"🔎 Eşleşen: <i>{esc(kw)}</i>")
    lines.append(f'🔗 <a href="{esc(i.url)}">İlana git</a>')
    return "\n".join(lines)


def format_line(i: Ilan, level: str) -> str:
    title = i.title[:140]
    if i.org and i.org.lower() not in i.title.lower():
        title = f"{i.org[:80]} – {title}"
    extra = f" ({esc(i.deadline)})" if i.deadline else ""
    return f'{ICON[level]} <a href="{esc(i.url)}">{esc(title)}</a>{extra}'


def check_source(key, mod, s, st, tg, grey_out) -> None:
    seen = st["seen"].setdefault(key, {})
    health = st["health"].setdefault(key, {"fails": 0, "alerted": False, "error": ""})
    bootstrap = not seen

    try:
        items = mod.fetch(s, seen)
    except Exception as e:
        health["fails"] += 1
        health["error"] = f"{type(e).__name__}: {e}"[:300]
        log.exception("%s başarısız (%d. kez)", key, health["fails"])
        if health["fails"] >= ALERT_AFTER and not health["alerted"]:
            if tg.send(f"⚠️ <b>{esc(mod.LABEL)}</b> {health['fails']} kez üst üste taranamadı.\n"
                       f"Bu sitedeki ilanları bir süre elle kontrol edin.\n<code>{esc(health['error'])}</code>"):
                health["alerted"] = True
        return

    if health["alerted"]:
        tg.send(f"✅ <b>{esc(mod.LABEL)}</b> yeniden taranabiliyor.")
    health.update(fails=0, alerted=False, error="")

    new = [i for i in items if i.id not in seen]
    log.info("%s: %d ilan, %d yeni", key, len(items), len(new))
    for i in new:
        if i.silent:
            seen[i.id] = now()
    new = [i for i in new if not i.silent]
    if not new:
        return

    ranked = [(i, *classify(i)) for i in new]
    if bootstrap:
        # İlk çalışma: şu an açık olan ilanları tek tek değil, özet olarak gönder.
        good = [format_line(i, lv) for i, lv, _ in ranked if lv != GREY]
        n_grey = sum(lv == GREY for _, lv, _ in ranked)
        header = (f"📋 <b>{esc(mod.LABEL)}</b>: takip başladı. Şu an açık {len(ranked)} ilan var"
                  + (f" ({n_grey} tanesi muhtemelen size uygun değil, listelenmedi)" if n_grey else "") + ":")
        good.sort(key=lambda x: not x.startswith(ICON[GREEN]))
        if tg.send_long(header, good or ["(listelenecek ilan yok)"]):
            for i in new:
                seen[i.id] = now()
        return

    for i, lv, kw in ranked:
        if lv == GREY:
            grey_out.append((i, lv, kw))
        elif tg.send(format_one(i, lv, kw)):
            seen[i.id] = now()


def send_grey(grey, st, tg) -> None:
    if not grey:
        return
    lines = [format_line(i, lv) + f" · {esc(SOURCES[i.source].LABEL)}" for i, lv, _ in grey]
    if tg.send_long(f"⚪ <b>Muhtemelen size uygun olmayan {len(grey)} yeni ilan</b> (yine de göz atın):", lines):
        for i, _, _ in grey:
            st["seen"][i.source][i.id] = now()


def heartbeat(st, tg) -> None:
    """Günde bir 'çalışıyorum' mesajı: bu mesaj gelmezse bot durmuş demektir."""
    t = datetime.now(TR)
    today = t.date().isoformat()
    if t.hour < HEARTBEAT_HOUR or st.get("heartbeat") == today:
        return
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    lines = []
    for key, mod in SOURCES.items():
        h = st["health"].get(key, {})
        n = sum(v >= since for v in st["seen"].get(key, {}).values())
        status = "✅" if not h.get("fails") else f"⚠️ {h['fails']} hata"
        lines.append(f"{status} {esc(mod.LABEL)}: son 24 saatte {n} yeni kayıt")
    if tg.send("🤖 <b>Bildiriyo günlük durum</b>\n" + "\n".join(lines)):
        st["heartbeat"] = today


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    only = sys.argv[1:]
    st, tg, s = state.load(), Telegram(), session()
    grey = []
    try:
        for key, mod in SOURCES.items():
            if only and key not in only:
                continue
            check_source(key, mod, s, st, tg, grey)
            state.save(st)
        send_grey(grey, st, tg)
        heartbeat(st, tg)
    finally:
        state.save(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
