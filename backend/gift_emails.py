"""Server-side email templates for gift codes (verification, gift delivery, redemption)."""

from html import escape

from course_pages import fill
from emailer import send_email
from reminders import _button, _layout, sender, site_url


def money(cents: int, locale: str) -> str:
    whole = f"{cents / 100:,.2f}"
    if locale == "fr":
        return whole.replace(",", " ").replace(".", ",") + " $"
    return f"${whole}"


def format_code(code: str) -> str:
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def steps_list(texts: dict) -> str:
    items = "".join(f"<li style=\"margin:0 0 8px\">{escape(s.strip())}</li>" for s in texts["giftNextSteps"].split("\n") if s.strip())
    return f'<ol style="padding-left:20px;margin:8px 0 0">{items}</ol>'


def _notice(text: str, bg: str, border: str) -> str:
    return (f'<p style="background:{bg};border:1px solid {border};border-radius:10px;padding:12px 14px;'
            f'font-weight:bold;margin:0 0 16px">{escape(text)}</p>')


def _date(dt, locale: str) -> str:
    return dt.strftime("%Y-%m-%d")


async def send_verification(checkout: dict, code: str, city: dict, texts: dict) -> None:
    body = (f'<p>{escape(texts["giftVerifyEmailIntro"])}</p>'
            f'<p style="font-size:30px;font-weight:bold;letter-spacing:6px;margin:18px 0">{escape(code)}</p>'
            f'<p style="font-size:13px;color:#57534E">{escape(texts["giftVerifyEmailIgnore"])}</p>')
    await send_email(to=checkout["email"], subject=fill(texts["giftVerifySubject"], code=code),
                     html=_layout(texts, city, body), from_name=sender(city, texts), reply_to=city.get("contactEmail"))


async def send_gift(gift: dict, city: dict, texts: dict) -> None:
    loc = gift["locale"]
    name = gift.get("recipient_first_name")
    greeting = fill(texts["giftEmailGreeting"], name=name) if name else texts["giftEmailGreetingNoName"]
    message = (f'<p style="white-space:pre-wrap;font-style:italic;margin:8px 0 0">{escape(gift["message"])}</p>'
               if gift.get("message") else "")
    details = (f'<table role="presentation" style="margin:14px 0;font-size:14px">'
               f'<tr><td style="padding:2px 16px 2px 0;color:#57534E">{escape(texts["giftAmount"])}</td>'
               f'<td><strong>{escape(money(gift["amount_cents"], loc))} {escape(gift["currency"])}</strong></td></tr>'
               f'<tr><td style="padding:2px 16px 2px 0;color:#57534E">{escape(texts["giftDate"])}</td>'
               f'<td>{escape(_date(gift["created_at"], loc))}</td></tr></table>')
    body = (_notice(texts["giftRegisteredBanner"], "#ECFDF5", "#A7F3D0")
            + (_notice(texts["giftDemoPaymentNote"], "#FEF3C7", "#FCD34D") if gift.get("demo") else "")
            + f'<p>{escape(texts["giftEmailIntro"])}</p>'
            f'<div style="border:1px dashed #D6D3D1;border-radius:12px;padding:18px;margin:16px 0">'
            f'<p style="margin:0">{escape(greeting)}</p>{message}'
            f'<p style="font-size:24px;font-weight:bold;letter-spacing:3px;margin:16px 0 4px;font-family:Courier,monospace">'
            f'{escape(format_code(gift["code"]))}</p>{details}'
            f'<p style="margin:0;font-size:14px">{escape(texts["giftHowItWorks"])}</p></div>'
            f'<p style="margin:18px 0 0"><strong>{escape(texts["giftNextStepsTitle"])}</strong></p>{steps_list(texts)}'
            + _notice(texts["giftSecurityNotice"], "#FEF2F2", "#FECACA")
            + _button(site_url(gift["host"], "/dashboard"), texts["giftEmailDashboard"]))
    await send_email(to=gift["gift_giver_email"],
                     subject=fill(texts["giftEmailSubject"], amount=f'{money(gift["amount_cents"], loc)} {gift["currency"]}'),
                     html=_layout(texts, city, body), from_name=sender(city, texts), reply_to=city.get("contactEmail"))


async def send_redemption(gift: dict, redemption: dict, city: dict, texts: dict) -> None:
    loc = gift["locale"]
    rows = ((texts["giftRedeemCourse"], redemption["course_name"]),
            (texts["giftRedeemUsed"], f'{money(redemption["amount_cents"], loc)} {gift["currency"]}'),
            (texts["giftBalance"], f'{money(redemption["balance_after_cents"], loc)} {gift["currency"]}'),
            (texts["giftDate"], _date(redemption["created_at"], loc)))
    table = "".join(f'<tr><td style="padding:3px 16px 3px 0;color:#57534E">{escape(k)}</td><td><strong>{escape(v)}</strong></td></tr>'
                    for k, v in rows)
    body = (f'<p>{escape(fill(texts["giftRedeemIntro"], code=format_code(gift["code"])))}</p>'
            f'<table role="presentation" style="margin:14px 0;font-size:14px">{table}</table>'
            + _button(site_url(gift["host"], "/dashboard"), texts["giftEmailDashboard"]))
    await send_email(to=gift["gift_giver_email"], subject=fill(texts["giftRedeemSubject"], course=redemption["course_name"]),
                     html=_layout(texts, city, body), from_name=sender(city, texts), reply_to=city.get("contactEmail"))
