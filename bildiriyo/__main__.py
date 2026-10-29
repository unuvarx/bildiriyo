"""Bildiriyo: kamu ilanlarını tarar, yenilerini Telegram'a gönderir.

Kural: bir ilan ancak Telegram'a başarıyla gönderildikten sonra "görüldü"
sayılır. Gönderim başarısız olursa bir sonraki çalışmada tekrar denenir.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from . import dedupe, state
from .eligibility import CHECK, OK, SKIP, decide
from .http import session
from .models import Ilan
from .sources import SOURCES
from .telegram import Telegram, esc

TR = timezone(timedelta(hours=3))
ALERT_AFTER = 1  # günde bir tarama: ilk hatada uyar
SCAN_GAP_HOURS = 12  # bundan yakın zamanda tarama yapıldıysa yedek çalışmalar çıkar
ENRICH_TRIES = 3  # ilan metni bu kadar denemede alınamazsa metinsiz karar ver
ICON = {OK: "🟢", CHECK: "🟡"}
HEAD = {OK: "BAŞVURABİLİRSİNİZ", CHECK: "ŞARTLARI KONTROL EDİN"}
WHY = {OK: "✅", CHECK: "❓"}

log = logging.getLogger("bildiriyo")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_one(i: Ilan, dec: str, why: str) -> str:
    label = SOURCES[i.source].LABEL
    lines = [f"{ICON[dec]} <b>{HEAD[dec]}</b> · {esc(label)}", f"<b>{esc(i.title)}</b>"]
    if i.org and i.org.lower() not in i.title.lower():
        lines.append(f"🏢 {esc(i.org)}")
    if i.category:
        lines.append(f"🏷 {esc(i.category)}")
    if i.deadline:
        lines.append(f"📅 Başvuru: {esc(i.deadline)}")
    if i.note:
        lines.append(f"ℹ️ {esc(i.note)}")
    lines.append(f"{WHY[dec]} {esc(why[:300])}")
    lines.append(f'🔗 <a href="{esc(i.url)}">İlana git</a>')
    return "\n".join(lines)


def format_line(i: Ilan, dec: str) -> str:
    title = i.title[:140]
    if i.org and i.org.lower() not in i.title.lower():
        title = f"{i.org[:80]} – {title}"
    extra = f" ({esc(i.deadline)})" if i.deadline else ""
    return f'{ICON[dec]} <a href="{esc(i.url)}">{esc(title)}</a>{extra}'


def judge(i: Ilan, mod, s, st) -> tuple[str, str, bool] | None:
    """(karar, sebep, tekrar mı). None: metin alınamadı, sonraki çalışmada tekrar dene."""
    enrich = getattr(mod, "enrich", None)
    if enrich and not i.has_text:
        key = f"{i.source}:{i.id}"
        try:
            enrich(s, i)
        except Exception as e:
            fails = st.setdefault("enrich_fail", {})
            fails[key] = fails.get(key, 0) + 1
            log.warning("%s metni alınamadı (%d. deneme): %s", key, fails[key], e)
            if fails[key] < ENRICH_TRIES:
                return None
        st.get("enrich_fail", {}).pop(key, None)

    dec, why = decide(i)
    fp = dedupe.fingerprint(i)
    prior = dedupe.find(st, fp) if dec != SKIP else None
    if prior and prior["sent"]:
        return dec, f"daha önce gönderildi: {prior['t']}", True
    if dec != SKIP and not i.has_text and prior and prior["dec"] == SKIP:
        return SKIP, f"aynı ilanın metnine göre: {prior['why']}", False
    return dec, why, False


def check_source(key, mod, s, st, tg) -> None:
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
    digest = []
    for i in new:
        if i.silent:
            seen[i.id] = now()
            continue
        verdict = judge(i, mod, s, st)
        if verdict is None:
            continue
        dec, why, dup = verdict
        log.info("  [%s%s] %s — %s", dec, " tekrar" if dup else "", i.title[:80], why[:120])
        if dec == SKIP or dup:
            if dec == SKIP:
                st.setdefault("skipped", {})[f"{key}:{i.id}"] = {"t": i.title[:120], "why": why, "d": now()}
                if i.has_text:
                    dedupe.remember(st, dedupe.fingerprint(i), dec, why, i.title, sent=False)
            seen[i.id] = now()
        elif bootstrap:
            digest.append((i, dec, why))
        elif tg.send(format_one(i, dec, why)):
            seen[i.id] = now()
            dedupe.remember(st, dedupe.fingerprint(i), dec, why, i.title, sent=True)

    if digest:
        # İlk çalışma: şu an açık olan uygun ilanları tek mesajda özetle.
        digest.sort(key=lambda x: x[1] != OK)
        lines = [format_line(i, dec) for i, dec, _ in digest]
        if tg.send_long(f"📋 <b>{esc(mod.LABEL)}</b>: şu an açık ve size uygun olabilecek ilanlar:", lines):
            for i, dec, why in digest:
                seen[i.id] = now()
                dedupe.remember(st, dedupe.fingerprint(i), dec, why, i.title, sent=True)


def summary(keys, s, st, tg) -> None:
    """Şu an açık olan TÜM ilanları (görülmüş olsalar da) değerlendirip uygun olanları tek mesajda özetler."""
    rows = []
    for key in keys:
        mod = SOURCES[key]
        try:
            items = mod.fetch(s, {})
        except Exception as e:
            log.exception("%s özet için taranamadı", key)
            rows.append((None, CHECK, f"⚠️ {mod.LABEL} taranamadı: {e}"[:200]))
            continue
        for i in items:
            if i.silent:
                continue
            verdict = judge(i, mod, s, st)
            if verdict and verdict[0] == SKIP and i.has_text:
                # Kariyer Kapısı'ndaki kopyası bu karara göre elensin
                dedupe.remember(st, dedupe.fingerprint(i), SKIP, verdict[1], i.title, sent=False)
            if not verdict or verdict[2] or verdict[0] == SKIP:
                continue
            dec, why, _ = verdict
            dedupe.remember(st, dedupe.fingerprint(i), dec, why, i.title, sent=True)
            st["seen"].setdefault(key, {})[i.id] = now()
            rows.append((i, dec, why))
    rows.sort(key=lambda r: r[1] != OK)
    lines = [format_line(i, dec) if i else why for i, dec, why in rows]
    n_ok = sum(dec == OK for i, dec, _ in rows if i)
    tg.send_long(f"📋 <b>Şu an açık ve başvurabileceğiniz ilanlar</b> "
                 f"({n_ok} uygun 🟢, {len(rows) - n_ok} şartları kontrol edilmeli 🟡):", lines or ["(yok)"])


def heartbeat(st, tg, keys) -> None:
    """Her taramanın sonunda durum mesajı: bu mesaj gelmezse bot durmuş demektir."""
    today = datetime.now(TR).date().isoformat()
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    lines = []
    last = st.get("last_scan", "")
    if last and last < (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat():
        # GitHub o gün(ler) hiç çalıştırmadı: sayılar arada geçen tüm süreyi kapsasın.
        since = last
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).days
        lines.append(f"⏱ Son tarama {days} gün önceydi. Arada çıkan ve hâlâ açık olan ilanlar bu taramada kontrol edildi.\n")
    for key in keys:
        h = st["health"].get(key, {})
        lines.append(("✅" if not h.get("fails") else "⚠️ taranamadı:") + f" {esc(SOURCES[key].LABEL)}")
    sent = sum(x["sent"] and x["d"] >= since for x in st.get("decided", []))
    skipped = sum(v["d"] >= since for v in st.get("skipped", {}).values())
    lines.append(f"\n📨 Size gönderilen yeni ilan: {sent}")
    lines.append(f"🚫 Uygun olmadığı için gönderilmeyen: {skipped}")
    if tg.send(f"🤖 <b>Bildiriyo günlük tarama</b> · {today}\n" + "\n".join(lines)):
        st["heartbeat"] = today
        st["last_scan"] = now()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = sys.argv[1:]
    force = "--force" in args
    only = [a for a in args if not a.startswith("--")]
    st, tg, s = state.load(), Telegram(), session()
    # Takvim günü yerine son taramadan geçen süreye bakılır: GitHub zamanlanmış
    # çalışmaları saatlerce geciktirebiliyor; gece yarısını geçen bir tarama
    # ertesi günün taramasını da "yapıldı" saydırıyordu.
    recent = (datetime.now(timezone.utc) - timedelta(hours=SCAN_GAP_HOURS)).isoformat()
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and st.get("last_scan", "") >= recent and not force:
        log.info("Son tarama %s, yedek çalışma çıkıyor.", st["last_scan"])
        return 0
    if tg.dry_run and os.environ.get("GITHUB_ACTIONS"):
        # Gönderemediğimiz ilanları "görüldü" saymamak için hiç çalışma.
        log.error("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID secret'ları tanımlı değil")
        return 1
    try:
        keys = [k for k in SOURCES if not only or k in only]
        if "--ozet" in args:
            summary(keys, s, st, tg)
            return 0
        for key in keys:
            mod = SOURCES[key]
            check_source(key, mod, s, st, tg)
            state.save(st)
        heartbeat(st, tg, keys)
    finally:
        dedupe.prune(st)
        state.save(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
