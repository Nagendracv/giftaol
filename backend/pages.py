"""Server-rendered public pages (home and unknown-host)."""

from html import escape

from course_pages import COURSE_STYLE, fill

DEFAULT_LOGO = "/api/static/aol-logo.png"

STYLE = """
:root{--bg:#FAF9F6;--surface:#FFFFFF;--text:#1C1917;--muted:#57534E;--border:#E7E5E4;
--primary:#B45309;--primary-hover:#92400E;--primary-light:#FEF3C7;--focus:#0284C7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:'DM Sans',-apple-system,sans-serif;line-height:1.6}
a:focus-visible{outline:3px solid var(--focus);outline-offset:3px;border-radius:999px}
.bar{background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:40}
.bar-inner{max-width:1200px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.logo{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--text)}
.logo img{height:44px;width:auto;display:block}
.site-name{font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;font-size:17px;border-left:1px solid var(--border);padding-left:12px}
.foot{border-top:1px solid var(--border);background:var(--surface);margin-top:40px}
.foot-inner{max-width:1100px;margin:0 auto;padding:28px 24px 96px;color:var(--muted);font-size:14px;display:grid;gap:8px}
.foot nav{display:flex;gap:18px}.foot a{color:#92400E}.foot p{margin:0}
.cookie{position:fixed;left:16px;right:16px;bottom:16px;max-width:640px;margin:0 auto;background:#1C1917;color:#FAF9F6;border-radius:14px;padding:14px 16px;display:flex;align-items:center;gap:14px;z-index:50;box-shadow:0 12px 32px -12px rgba(0,0,0,.4)}
.cookie p{margin:0;font-size:14px;flex:1}.cookie a{color:#FCD34D}
.legal{max-width:760px;margin:0 auto;padding:48px 24px 40px}.legal h2{font-family:'Plus Jakarta Sans',sans-serif;font-size:18px;margin:28px 0 6px}.legal p{color:#44403C}
.actions{display:flex;align-items:center;gap:12px}
.lang{display:flex;border:1px solid var(--border);border-radius:999px;padding:3px}
.lang a{color:var(--muted);text-decoration:none;font-size:13px;font-weight:600;padding:5px 11px;border-radius:999px;transition:background-color .2s,color .2s}
.lang a:hover{color:var(--text)}
.lang a[aria-current=true]{background:var(--primary-light);color:#78350F}
.btn{background:var(--primary);color:#fff;text-decoration:none;font-weight:600;font-size:14px;padding:10px 18px;border-radius:999px;transition:background-color .2s}
.btn:hover{background:var(--primary-hover)}.btn{white-space:nowrap}.btn .short{display:none}
.gift-link{display:inline-flex;align-items:center;gap:7px;color:var(--text);text-decoration:none;font-size:14px;font-weight:600;padding:8px 12px;border-radius:999px;transition:background-color .2s,color .2s}
.gift-link:hover{background:var(--primary-light);color:#78350F}.gift-link svg{width:17px;height:17px}
main{max-width:1200px;margin:0 auto;padding:clamp(64px,14vh,160px) 24px}
h1{font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;font-size:clamp(2.25rem,6vw,4rem);letter-spacing:-.02em;margin:0;animation:rise .7s ease-out both}
.card{max-width:520px;margin:18vh auto 0;padding:40px;background:var(--surface);border:1px solid var(--border);border-radius:16px}
.card h1{font-size:clamp(1.5rem,3vw,2rem)}
.card p{color:var(--muted);margin:12px 0 0}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@media (max-width:640px){.gift-link span{display:none}.btn .long{display:none}.btn .short{display:inline}.btn{padding:9px 14px;font-size:13px}.logo img{height:34px}.site-name{display:none}}
@media (prefers-reduced-motion:reduce){h1{animation:none}}
"""

GIFT_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/>'
             '<path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/></svg>')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700'
         '&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet">')


def _document(locale: str, title: str, body: str, head: str = "") -> str:
    return (f'<!doctype html><html lang="{escape(locale)}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)}</title>{head}{FONTS}<style>{STYLE}{COURSE_STYLE}</style>'
            f'<script src="/api/static/site.js" defer></script></head><body>{body}</body></html>')


def site_name(city: dict, texts: dict) -> str:
    return (city.get("theme") or {}).get("siteTitle") or fill(texts["siteName"], city=city["displayName"])


def footer(city: dict, texts: dict, year: int) -> str:
    links = []
    if city.get("contactEmail"):
        links.append(f'<a href="mailto:{escape(city["contactEmail"])}">{escape(city["contactEmail"])}</a>')
    if city.get("contactPhone"):
        links.append(f'<a href="tel:{escape(city["contactPhone"])}">{escape(city["contactPhone"])}</a>')
    contact = " · ".join(links)
    return ('<footer class="foot" data-testid="site-footer"><div class="foot-inner">'
            f'<nav aria-label="{escape(texts["footerNav"])}"><a href="/privacy" data-testid="footer-privacy-link">{escape(texts["privacyTitle"])}</a>'
            f'<a href="/terms" data-testid="footer-terms-link">{escape(texts["termsTitle"])}</a></nav>'
            f'{f"<p>{contact}</p>" if contact else ""}'
            f'<p>© {year} {escape(site_name(city, texts))} · {escape(texts["placesCredit"])} '
            f'<a href="https://www.geonames.org" target="_blank" rel="noopener" data-testid="footer-geonames-credit">GeoNames</a></p></div></footer>')


def cookie_notice(texts: dict) -> str:
    return (f'<div class="cookie" role="region" aria-label="{escape(texts["cookieLabel"])}" data-cookie-notice data-testid="cookie-notice">'
            f'<p>{escape(texts["cookieText"])} <a href="/privacy">{escape(texts["privacyTitle"])}</a></p>'
            f'<button type="button" class="btn" data-cookie-ok data-testid="cookie-notice-ok-button">{escape(texts["cookieOk"])}</button></div>')


def paragraphs(text: str) -> str:
    """Legal page text: blank-line separated paragraphs; lines starting with '## ' are headings."""
    out = []
    for block in (b.strip() for b in text.split("\n\n")):
        if block.startswith("## "):
            heading, _, rest = block.partition("\n")
            out.append(f"<h2>{escape(heading[3:].strip())}</h2>")
            if rest.strip():
                out.append(f"<p>{escape(rest.strip())}</p>")
        elif block:
            out.append(f"<p>{escape(block)}</p>")
    return "".join(out)


def _language_links(locale: str, locales, texts: dict, path: str, tab: str) -> str:
    links = "".join(
        f'<a href="{path}?lang={escape(code)}&amp;tab={escape(tab)}" hreflang="{escape(code)}" lang="{escape(code)}" '
        f'aria-current="{"true" if code == locale else "false"}" '
        f'data-testid="lang-switch-{escape(code)}">{escape(code.upper())}</a>'
        for code in locales)
    return (f'<nav class="lang" aria-label="{escape(texts["languageLabel"])}" '
            f'data-testid="language-switcher">{links}</nav>')


def render_page(city: dict, texts: dict, locale: str, locales, *, signed_in: bool, content: str, path: str = "/",
                tab: str = "newcomer", cookie_ok: bool = False, title: str | None = None, head: str = "", year: int = 2026) -> str:
    logo = city.get("logoUrl") or DEFAULT_LOGO
    name = site_name(city, texts)
    account_link = (
        f'<a class="btn" href="/dashboard" data-testid="header-dashboard-link">{escape(texts["dashboardLink"])}</a>'
        if signed_in else
        f'<a class="btn" href="/sign-in" data-testid="auth-button"><span class="long">{escape(texts["signInButton"])}</span>'
        f'<span class="short">{escape(texts["signInShort"])}</span></a>')
    header = (
        '<header class="bar" data-testid="main-header"><div class="bar-inner">'
        f'<a class="logo" href="/" data-testid="header-logo-link">'
        f'<img src="{escape(logo)}" alt="{escape(texts["logoAlt"])}" data-testid="header-logo">'
        f'<span class="site-name" data-testid="header-site-name">{escape(name)}</span></a>'
        f'<div class="actions"><a class="gift-link" href="/gift" data-testid="header-give-gift-link" aria-label="{escape(texts["giftButton"])}">'
        f'{GIFT_ICON}<span>{escape(texts["giftButton"])}</span></a>'
        f'{account_link}{_language_links(locale, locales, texts, path, tab)}'
        '</div></div></header>')
    body = header + content + footer(city, texts, year) + ("" if cookie_ok else cookie_notice(texts))
    return _document(locale, f"{title} · {name}" if title else name, body, head)


def legal_content(kind: str, city: dict, texts: dict) -> str:
    contact = city.get("contactEmail") or texts["legalContactFallback"]
    text = fill(texts[f"{kind}Body"], site=site_name(city, texts), city=city["displayName"], contact=contact)
    return (f'<main class="legal" data-testid="{kind}-page"><h1 class="cs-title">{escape(texts[f"{kind}Title"])}</h1>'
            f'{paragraphs(text)}</main>')


def render_not_configured(texts: dict, locale: str) -> str:
    body = ('<main><div class="card" data-testid="not-found-container">'
            f'<h1 data-testid="not-found-title">{escape(texts["notConfiguredTitle"])}</h1>'
            f'<p data-testid="not-found-message">{escape(texts["notConfiguredMessage"])}</p></div></main>')
    return _document(locale, texts["notConfiguredTitle"], body)
