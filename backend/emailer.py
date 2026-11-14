import os
import re
import asyncio
import ipaddress
import logging
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from core import db, now, ser, dollars, format_code, get_config

logger = logging.getLogger("giftaol.email")

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ["EMERGENT_EMAIL_KEY"]
EMAIL_FROM_NAME = os.environ["EMAIL_FROM_NAME"]
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> str:
    _assert_safe_email(subject, html)
    cfg = await get_config()
    payload = {"to": [to], "subject": subject, "html": html,
               "from_name": cfg.get("email_from_name") or EMAIL_FROM_NAME}
    reply_to = cfg.get("email_reply_to") or EMAIL_REPLY_TO
    if reply_to:
        payload["contact_email"] = reply_to
    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
    if resp.status_code >= 400:
        try:
            code = resp.json().get("code", "")
        except ValueError:
            code = ""
        if code in ("insufficient_credits", "integration_disabled", "daily_limit_reached"):
            logger.warning("Email paused: %s (%s)", code, resp.status_code)
            raise RuntimeError(f"paused:{code}")
        raise RuntimeError(f"http_{resp.status_code}")
    return resp.json().get("id")


async def send_with_retry(to: str, subject: str, html: str, delays=(2, 5)):
    # One first try plus one retry per delay (seconds).
    attempts = len(delays) + 1
    last = ""
    for i in range(attempts):
        try:
            await send_email(to=to, subject=subject, html=html)
            return True, None, i + 1
        except ValueError:
            raise
        except Exception as e:
            last = str(e)[:120]
            logger.warning("Email attempt %s failed: %s", i + 1, last)
            if last.startswith("paused:"):
                break
            if i < attempts - 1:
                await asyncio.sleep(delays[i])
    return False, last, attempts


# ---------- templates ----------
T = {
    "en": {
        "brand_footer": "Sent by giftaol.ca, a gift program for Art of Living. We never ask for your password or card details by email.",
        "code_subject": "Your giftaol.ca verification code",
        "code_body": "Use this code to finish signing in to giftaol.ca. Enter it on the screen where you requested it.",
        "code_note": "This code stays valid until you request a new one. If you did not request it, you can ignore this email.",
        "welcome_subject": "Welcome to giftaol.ca",
        "welcome_body": "You signed in to giftaol.ca with Google. You can keep using Google sign-in every time.",
        "welcome_pw": "If you would also like to sign in with your email and a password, open Dashboard > Account and choose a password, or use \"Email me a code\" on the sign-in page.",
        "gift_subject": "Your Art of Living gift code",
        "demo": "DEMO — this gift was created with a demo payment. No money was charged.",
        "gift_intro": "Thank you for your gift. Here are the details.",
        "code": "Gift code", "amount": "Amount", "date": "Date", "recipient": "Recipient",
        "message": "Your message", "how_title": "How the code works",
        "how": "The person enters this code during Art of Living course registration in Harmony on artofliving.org. The amount is deducted from the course fee and they pay the balance.",
        "steps_title": "Next steps",
        "greeting": "A gift for {name}",
        "red_subject": "Your gift code was used",
        "red_intro": "Your gift code {code} was just used for a course.",
        "course": "Course", "used": "Amount used", "remaining": "Remaining balance",
    },
    "fr": {
        "brand_footer": "Envoyé par giftaol.ca, un programme de cadeaux pour l'Art de vivre. Nous ne demandons jamais votre mot de passe ni vos données de carte par courriel.",
        "code_subject": "Votre code de vérification giftaol.ca",
        "code_body": "Utilisez ce code pour terminer votre connexion à giftaol.ca. Saisissez-le sur l'écran où vous l'avez demandé.",
        "code_note": "Ce code reste valide jusqu'à ce que vous en demandiez un nouveau. Si vous ne l'avez pas demandé, ignorez ce courriel.",
        "welcome_subject": "Bienvenue sur giftaol.ca",
        "welcome_body": "Vous vous êtes connecté à giftaol.ca avec Google. Vous pouvez continuer à utiliser la connexion Google en tout temps.",
        "welcome_pw": "Si vous souhaitez aussi vous connecter avec votre courriel et un mot de passe, ouvrez Tableau de bord > Compte et choisissez un mot de passe, ou utilisez « Recevoir un code par courriel » sur la page de connexion.",
        "gift_subject": "Votre code-cadeau de l'Art de vivre",
        "demo": "DÉMO — ce cadeau a été créé avec un paiement de démonstration. Aucun montant n'a été facturé.",
        "gift_intro": "Merci pour votre cadeau. Voici les détails.",
        "code": "Code-cadeau", "amount": "Montant", "date": "Date", "recipient": "Destinataire",
        "message": "Votre message", "how_title": "Comment fonctionne le code",
        "how": "La personne saisit ce code lors de l'inscription à un cours de l'Art de vivre dans Harmony sur artofliving.org. Le montant est déduit des frais du cours et elle paie le solde.",
        "steps_title": "Prochaines étapes",
        "greeting": "Un cadeau pour {name}",
        "red_subject": "Votre code-cadeau a été utilisé",
        "red_intro": "Votre code-cadeau {code} vient d'être utilisé pour un cours.",
        "course": "Cours", "used": "Montant utilisé", "remaining": "Solde restant",
    },
}


def _lang(lang):
    return lang if lang in T else "en"


def _shell(title: str, inner: str, lang: str) -> str:
    t = T[_lang(lang)]
    return (
        '<table role="presentation" width="100%" style="background:#FAF7F2;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="600" style="max-width:600px;background:#ffffff;border:1px solid #E7E5E4;border-radius:12px">'
        '<tr><td style="padding:24px 28px;border-bottom:3px solid #D95D39;font-family:Georgia,serif;font-size:22px;color:#2A4736">giftaol.ca</td></tr>'
        f'<tr><td style="padding:24px 28px;font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#1C1917">'
        f'<h1 style="font-family:Georgia,serif;font-size:24px;color:#1C1917;margin:0 0 16px">{escape(title)}</h1>{inner}</td></tr>'
        f'<tr><td style="padding:16px 28px;font-family:Arial,sans-serif;font-size:12px;color:#57534E;border-top:1px solid #E7E5E4">{escape(t["brand_footer"])}</td></tr>'
        '</table></td></tr></table>'
    )


def _box(text: str, bg: str, border: str) -> str:
    return f'<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:12px 14px;margin:14px 0">{escape(text)}</div>'


def code_email(code: str, lang: str):
    t = T[_lang(lang)]
    inner = (f"<p>{escape(t['code_body'])}</p>"
             f'<p style="font-family:Courier New,monospace;font-size:30px;letter-spacing:6px;font-weight:bold;color:#2A4736;margin:18px 0">{escape(code)}</p>'
             f'<p style="color:#57534E;font-size:13px">{escape(t["code_note"])}</p>')
    return t["code_subject"], _shell(t["code_subject"], inner, lang)


def welcome_email(lang: str):
    t = T[_lang(lang)]
    inner = f"<p>{escape(t['welcome_body'])}</p><p>{escape(t['welcome_pw'])}</p>"
    return t["welcome_subject"], _shell(t["welcome_subject"], inner, lang)


def _row(label, value):
    return (f'<tr><td style="padding:6px 0;color:#57534E;width:40%">{escape(label)}</td>'
            f'<td style="padding:6px 0;font-weight:bold">{escape(value)}</td></tr>')


def gift_email(gift: dict, cfg: dict, lang: str):
    lang = _lang(lang)
    t = T[lang]
    texts = cfg["texts"]
    created = ser(gift["created_at"])[:10]
    inner = ""
    if gift.get("demo"):
        inner += _box(t["demo"], "#FEF3C7", "#F59E0B")
    if gift.get("recipient_first_name"):
        inner += f'<p style="font-size:17px;color:#2A4736"><strong>{escape(t["greeting"].format(name=gift["recipient_first_name"]))}</strong></p>'
    inner += f"<p>{escape(t['gift_intro'])}</p>"
    inner += (f'<div style="background:#FFFBEB;border:1px solid #FCD34D;border-radius:10px;padding:16px;text-align:center;'
              f'font-family:Courier New,monospace;font-size:24px;letter-spacing:3px;font-weight:bold;color:#78350F">{escape(format_code(gift["code"]))}</div>')
    inner += '<table role="presentation" width="100%" style="margin:12px 0">'
    inner += _row(t["amount"], f"${dollars(gift['amount_cents']):.2f} {gift['currency']}")
    inner += _row(t["date"], created)
    if gift.get("recipient_first_name"):
        inner += _row(t["recipient"], gift["recipient_first_name"])
    inner += "</table>"
    if gift.get("message"):
        inner += f'<p style="color:#57534E;margin-bottom:4px">{escape(t["message"])}</p>'
        inner += f'<blockquote style="margin:0 0 12px;padding:10px 14px;border-left:3px solid #D95D39;background:#FDF2EE;white-space:pre-wrap">{escape(gift["message"])}</blockquote>'
    inner += _box(texts["banner"][lang], "#EBF2ED", "#2A4736")
    inner += f'<h2 style="font-family:Georgia,serif;font-size:18px;margin:18px 0 6px">{escape(t["how_title"])}</h2><p>{escape(t["how"])}</p>'
    inner += f'<p style="color:#57534E">{escape(texts["explainer"][lang])}</p>'
    inner += f'<h2 style="font-family:Georgia,serif;font-size:18px;margin:18px 0 6px">{escape(t["steps_title"])}</h2><ol style="padding-left:20px">'
    inner += "".join(f'<li style="margin-bottom:6px">{escape(s)}</li>' for s in texts["next_steps"][lang])
    inner += "</ol>"
    inner += _box(texts["security"][lang], "#FEF2F2", "#FCA5A5")
    subject = t["gift_subject"] + (" (DEMO)" if gift.get("demo") else "")
    return subject, _shell(t["gift_subject"], inner, lang)


def redemption_email(gift: dict, red: dict, lang: str):
    lang = _lang(lang)
    t = T[lang]
    inner = f"<p>{escape(t['red_intro'].format(code=format_code(gift['code'])[:4] + '-****'))}</p>"
    inner += '<table role="presentation" width="100%" style="margin:12px 0">'
    inner += _row(t["course"], red["course_name"])
    inner += _row(t["used"], f"${dollars(red['amount_used_cents']):.2f} {gift['currency']}")
    inner += _row(t["remaining"], f"${dollars(red['balance_after_cents']):.2f} {gift['currency']}")
    inner += _row(t["date"], ser(red["created_at"])[:10])
    inner += "</table>"
    return t["red_subject"], _shell(t["red_subject"], inner, lang)


# ---------- background deliveries ----------
_tasks = set()
BACKGROUND_DELAYS = (10, 60, 300)


def spawn(coro):
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def deliver_gift_email(gift_id: str):
    gift = await db.gifts.find_one({"id": gift_id}, {"_id": 0})
    giver = await db.users.find_one({"id": gift["gift_giver_id"]}, {"_id": 0, "email": 1, "lang": 1})
    cfg = await get_config()
    subject, html = gift_email(gift, cfg, gift.get("lang") or giver.get("lang") or "en")
    ok, err, n = await send_with_retry(giver["email"], subject, html, delays=BACKGROUND_DELAYS)
    await db.gifts.update_one({"id": gift_id}, {
        "$set": {"email_status": "sent" if ok else "failed", "email_last_error": err, "email_updated_at": now()},
        "$inc": {"email_attempts": n},
    })
    return ok


async def deliver_redemption_email(gift_id: str, redemption_id: str):
    gift = await db.gifts.find_one({"id": gift_id}, {"_id": 0})
    red = await db.redemptions.find_one({"id": redemption_id}, {"_id": 0})
    giver = await db.users.find_one({"id": gift["gift_giver_id"]}, {"_id": 0, "email": 1, "lang": 1})
    subject, html = redemption_email(gift, red, giver.get("lang") or gift.get("lang") or "en")
    ok, err, _ = await send_with_retry(giver["email"], subject, html, delays=BACKGROUND_DELAYS)
    await db.redemptions.update_one({"id": redemption_id}, {"$set": {"email_status": "sent" if ok else "failed"}})
