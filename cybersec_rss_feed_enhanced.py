#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CyberNews — Agrégateur RSS intelligent de cybersécurité.

Récupère en parallèle les actualités depuis plus de 50 sources fiables
(médias, chercheurs, éditeurs, CERT/agences gouvernementales), puis :
  - déduplique les articles couvrant la même histoire,
  - calcule un score de pertinence (zero-day, CVE, ransomware, exploitation
    active, fuites de données...),
  - détecte les identifiants CVE et les relie à la base NVD,
  - génère un digest HTML (section "À la une" + classement par catégorie),
  - l'envoie par email et le sauvegarde localement (digest.html).

Usage :
    python cybersec_rss_feed_enhanced.py                 # digest + email
    python cybersec_rss_feed_enhanced.py --dry-run       # digest sans email
    python cybersec_rss_feed_enhanced.py --test-smtp     # teste la config SMTP
    python cybersec_rss_feed_enhanced.py --days 7        # fenêtre de 7 jours
    python cybersec_rss_feed_enhanced.py --list-feeds    # liste les sources

Configuration via un fichier .env (voir .env.example).
"""

import argparse
import calendar
import json
import os
import re
import smtplib
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape, unescape

import feedparser
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()


def _env(*names, default=""):
    """Lit la première variable d'environnement définie parmi `names`."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


# --- Configuration (les anciens noms EMAIL_SENDER/EMAIL_RECIPIENT restent acceptés) ---
SENDER_EMAIL = _env("SENDER_EMAIL", "EMAIL_SENDER", default="votre_email@example.com")
RECIPIENT_EMAIL = _env("RECIPIENT_EMAIL", "EMAIL_RECIPIENT", default="votre_email@example.com")
EMAIL_PASSWORD = _env("EMAIL_PASSWORD", default="votre_mot_de_passe_application")
SMTP_SERVER = _env("SMTP_SERVER", default="smtp.gmail.com")
SMTP_PORT = int(_env("SMTP_PORT", default="465"))
EMAIL_SUBJECT_PREFIX = _env("EMAIL_SUBJECT_PREFIX", default="🛡️ CyberNews — ")
DEFAULT_DAYS = float(_env("DAYS_LOOKBACK", default="2"))

TIMEOUT = 10
MAX_RETRIES = 2
MAX_WORKERS = 12

session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CyberNewsBot/2.0",
    "Accept": "application/rss+xml, application/xml, application/atom+xml, "
              "text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.8,en-US,en;q=0.5",
}

# --- Sources RSS (plus de 50 flux vérifiés, classés par catégorie) ---
# weight : bonus de score appliqué aux articles de la source (sources à haut signal).
RSS_FEEDS = [
    # --- Actualités & médias spécialisés ---
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": "Actualités", "weight": 2},
    {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "category": "Actualités", "weight": 2},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": "Actualités", "weight": 3},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "category": "Actualités", "weight": 1},
    {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/", "category": "Actualités", "weight": 1},
    {"name": "Infosecurity Magazine", "url": "https://www.infosecurity-magazine.com/rss/news/", "category": "Actualités", "weight": 1},
    {"name": "Security Affairs", "url": "https://securityaffairs.com/feed", "category": "Actualités", "weight": 1},
    {"name": "The Record (Recorded Future)", "url": "https://therecord.media/feed", "category": "Actualités", "weight": 2},
    {"name": "CyberScoop", "url": "https://cyberscoop.com/feed/", "category": "Actualités", "weight": 1},
    {"name": "Help Net Security", "url": "https://www.helpnetsecurity.com/feed/", "category": "Actualités", "weight": 1},
    {"name": "Ars Technica Security", "url": "https://feeds.arstechnica.com/arstechnica/security", "category": "Actualités", "weight": 1},
    {"name": "Wired Security", "url": "https://www.wired.com/feed/category/security/latest/rss", "category": "Actualités", "weight": 1},
    {"name": "ZDNet Security", "url": "https://www.zdnet.com/topic/security/rss.xml", "category": "Actualités", "weight": 0},
    {"name": "Schneier on Security", "url": "https://www.schneier.com/feed/atom/", "category": "Actualités", "weight": 2},
    {"name": "Graham Cluley", "url": "https://grahamcluley.com/feed/", "category": "Actualités", "weight": 1},
    {"name": "The Register Security", "url": "https://www.theregister.com/security/headlines.atom", "category": "Actualités", "weight": 1},

    # --- Sources françaises ---
    {"name": "ZATAZ Magazine", "url": "https://www.zataz.com/feed/", "category": "Sources françaises", "weight": 1},
    {"name": "UnderNews", "url": "https://www.undernews.fr/feed", "category": "Sources françaises", "weight": 1},
    {"name": "Le Monde Informatique Sécurité", "url": "https://www.lemondeinformatique.fr/flux-rss/thematique/securite/rss.xml", "category": "Sources françaises", "weight": 1},
    {"name": "CNIL", "url": "https://www.cnil.fr/fr/rss.xml", "category": "Sources françaises", "weight": 1},

    # --- Recherche & éditeurs de sécurité ---
    {"name": "Google Security Blog", "url": "https://security.googleblog.com/feeds/posts/default", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "Google Project Zero", "url": "https://googleprojectzero.blogspot.com/feeds/posts/default", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Microsoft Security Blog", "url": "https://www.microsoft.com/en-us/security/blog/feed/", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "MSRC Blog", "url": "https://msrc.microsoft.com/blog/feed", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Cisco Talos", "url": "https://blog.talosintelligence.com/rss/", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Unit 42 (Palo Alto)", "url": "https://unit42.paloaltonetworks.com/feed/", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Mandiant / Google Threat Intelligence", "url": "https://cloud.google.com/blog/topics/threat-intelligence/rss/", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Securelist (Kaspersky)", "url": "https://securelist.com/feed/", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "WeLiveSecurity (ESET)", "url": "https://www.welivesecurity.com/en/rss/feed/", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "Malwarebytes Labs", "url": "https://www.malwarebytes.com/blog/feed/index.xml", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "SentinelOne Labs", "url": "https://www.sentinelone.com/blog/feed/", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "CrowdStrike Blog", "url": "https://www.crowdstrike.com/blog/feed/", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "Sophos News", "url": "https://news.sophos.com/en-us/feed/", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "Trend Micro Research", "url": "https://feeds.trendmicro.com/TrendMicroResearch", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "Check Point Research", "url": "https://research.checkpoint.com/feed/", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "Rapid7 Blog", "url": "https://blog.rapid7.com/rss/", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "Tenable Blog", "url": "https://www.tenable.com/blog/feed", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "Qualys Blog", "url": "https://blog.qualys.com/feed", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "PortSwigger Research", "url": "https://portswigger.net/research/rss", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "The DFIR Report", "url": "https://thedfirreport.com/feed/", "category": "Recherche & éditeurs", "weight": 3},
    {"name": "Elastic Security Labs", "url": "https://www.elastic.co/security-labs/rss/feed.xml", "category": "Recherche & éditeurs", "weight": 2},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/", "category": "Recherche & éditeurs", "weight": 1},
    {"name": "GitHub Security Blog", "url": "https://github.blog/category/security/feed/", "category": "Recherche & éditeurs", "weight": 1},

    # --- CERT & agences gouvernementales ---
    {"name": "CERT-FR — Alertes (ANSSI)", "url": "https://www.cert.ssi.gouv.fr/alerte/feed/", "category": "CERT & gouvernemental", "weight": 4},
    {"name": "CERT-FR — Avis (ANSSI)", "url": "https://www.cert.ssi.gouv.fr/avis/feed/", "category": "CERT & gouvernemental", "weight": 2},
    {"name": "CERT-FR — Actualités (ANSSI)", "url": "https://www.cert.ssi.gouv.fr/actualite/feed/", "category": "CERT & gouvernemental", "weight": 2},
    {"name": "CISA Advisories", "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml", "category": "CERT & gouvernemental", "weight": 3},
    {"name": "NCSC UK", "url": "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml", "category": "CERT & gouvernemental", "weight": 2},
    {"name": "SANS Internet Storm Center", "url": "https://isc.sans.edu/rssfeed_full.xml", "category": "CERT & gouvernemental", "weight": 2},
    {"name": "EFF Deeplinks", "url": "https://www.eff.org/rss/updates.xml", "category": "CERT & gouvernemental", "weight": 0},

    # --- Vulnérabilités & exploits ---
    {"name": "Zero Day Initiative", "url": "https://www.zerodayinitiative.com/rss/published/", "category": "Vulnérabilités & exploits", "weight": 2},
    {"name": "Exploit-DB", "url": "https://www.exploit-db.com/rss.xml", "category": "Vulnérabilités & exploits", "weight": 1},
    {"name": "Full Disclosure", "url": "https://seclists.org/rss/fulldisclosure.rss", "category": "Vulnérabilités & exploits", "weight": 1},
    {"name": "r/netsec (Reddit)", "url": "https://www.reddit.com/r/netsec/.rss", "category": "Vulnérabilités & exploits", "weight": 0},

    # --- IA & technologies émergentes ---
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "IA & émergent", "weight": 0},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "category": "IA & émergent", "weight": 0},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "IA & émergent", "weight": 0},
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "IA & émergent", "weight": 0},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "category": "IA & émergent", "weight": 0},
]

# Nombre maximum d'articles conservés par flux (les flux CERT/alertes sont courts).
MAX_PER_FEED = 15

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

# Mots-clés de scoring : (motif, poids). Un motif trouvé dans le TITRE compte double.
SCORING_PATTERNS = [
    (re.compile(r"\b(?:0|zero)[- ]?day\b", re.I), 12),
    (re.compile(r"exploited in the wild|actively exploited|activement exploit", re.I), 12),
    (re.compile(r"\bKEV\b|known exploited", re.I), 9),
    (re.compile(r"remote code execution|\bRCE\b|unauthenticated", re.I), 8),
    (re.compile(r"\bcritical\b|critique", re.I), 5),
    (re.compile(r"ransomware|rançongiciel|extortion", re.I), 6),
    (re.compile(r"data (?:breach|leak)|fuite de données|stolen data", re.I), 6),
    (re.compile(r"supply[- ]chain", re.I), 6),
    (re.compile(r"\bAPT[- ]?\d+\b|state[- ]sponsored|nation[- ]state", re.I), 5),
    (re.compile(r"backdoor|porte dérobée|implant", re.I), 4),
    (re.compile(r"\bPoC\b|proof[- ]of[- ]concept|exploit (?:code|released|available)", re.I), 5),
    (re.compile(r"vulnerabilit|vulnérabilit", re.I), 3),
    (re.compile(r"patch|correctif|security update|mise à jour de sécurité", re.I), 2),
    (re.compile(r"phishing|malware|botnet|spyware|infostealer|trojan", re.I), 3),
    (re.compile(r"\bMFA bypass\b|credential|password leak", re.I), 3),
]


def clean_html(html_text, max_len=300):
    """Supprime les balises HTML et normalise le texte d'une description."""
    if not html_text:
        return ""
    html_text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", html_text, flags=re.DOTALL)
    html_text = re.sub(r"<[^>]+>", " ", html_text)
    html_text = unescape(html_text)
    html_text = re.sub(r"\s+", " ", html_text).strip()
    if len(html_text) > max_len:
        html_text = html_text[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return html_text


def parse_entry_date(entry):
    """Retourne la date de publication (UTC, aware) d'une entrée, ou None."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    return None


def score_article(title, description, source_weight, pub_date, now):
    """Score de pertinence : mots-clés (titre x2), CVE, fraîcheur, poids de la source."""
    score = source_weight
    text = f"{title} {description}"
    for pattern, weight in SCORING_PATTERNS:
        if pattern.search(title):
            score += weight * 2
        elif pattern.search(text):
            score += weight
    cves = set(cve.upper() for cve in CVE_RE.findall(text))
    score += min(len(cves), 3) * 4
    age_hours = (now - pub_date).total_seconds() / 3600
    if age_hours <= 24:
        score += 5
    elif age_hours <= 48:
        score += 2
    return score, sorted(cves)


def fetch_feed(feed_source, cutoff_date, max_per_feed):
    """Récupère et analyse un flux RSS. Retourne (nom, articles, erreur)."""
    name = feed_source["name"]
    try:
        response = session.get(feed_source["url"], headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as exc:
        return name, [], str(exc)

    now = datetime.now(timezone.utc)
    articles = []
    for entry in feed.entries[:max_per_feed]:
        try:
            pub_date = parse_entry_date(entry) or now
            if pub_date < cutoff_date:
                continue
            description = ""
            for attr in ("description", "summary"):
                if getattr(entry, attr, None):
                    description = getattr(entry, attr)
                    break
            else:
                content = getattr(entry, "content", None)
                if content:
                    description = content[0].value
            description = clean_html(description)
            title = clean_html(getattr(entry, "title", "")) or "Sans titre"
            link = getattr(entry, "link", "") or ""
            score, cves = score_article(title, description, feed_source.get("weight", 0), pub_date, now)
            articles.append({
                "title": title,
                "link": link,
                "description": description,
                "source": name,
                "category": feed_source.get("category", "Autre"),
                "pub_date": pub_date.isoformat(),
                "score": score,
                "cves": cves,
            })
        except Exception:
            continue
    return name, articles, None


def get_cybersecurity_news(days, max_per_feed=MAX_PER_FEED):
    """Récupère tous les flux en parallèle et retourne la liste brute d'articles."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"Récupération de {len(RSS_FEEDS)} flux RSS (fenêtre : {days:g} jour(s))...")

    all_articles, failures = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_feed, feed, cutoff_date, max_per_feed): feed
            for feed in RSS_FEEDS
        }
        for future in as_completed(futures):
            name, articles, error = future.result()
            if error:
                failures.append(name)
                print(f"  ✗ {name}: {error}")
            else:
                print(f"  ✓ {name}: {len(articles)} article(s)")
                all_articles.extend(articles)

    print(f"\n{len(all_articles)} articles récupérés, {len(failures)} flux en échec"
          f"{' (' + ', '.join(failures) + ')' if failures else ''}.")
    return all_articles


def deduplicate(articles):
    """Supprime les doublons (même lien ou titres quasi identiques entre sources).

    Les articles sont parcourus par score décroissant pour conserver
    la version la mieux notée de chaque histoire.
    """
    kept, seen_links, seen_titles = [], set(), []
    for article in sorted(articles, key=lambda a: a["score"], reverse=True):
        link = article["link"].split("?")[0].rstrip("/").lower()
        if link and link in seen_links:
            continue
        norm = re.sub(r"[^a-z0-9 ]", "", article["title"].lower()).strip()
        if any(
            SequenceMatcher(None, norm, seen).ratio() > 0.92
            for seen in seen_titles
            if abs(len(seen) - len(norm)) < 20
        ):
            continue
        seen_links.add(link)
        seen_titles.append(norm)
        kept.append(article)
    removed = len(articles) - len(kept)
    if removed:
        print(f"Déduplication : {removed} doublon(s) supprimé(s).")
    return kept


def _fmt_date(iso_date):
    try:
        return datetime.fromisoformat(iso_date).astimezone().strftime("%d/%m/%Y à %H:%M")
    except ValueError:
        return iso_date


def _render_article(article, highlight=False):
    """Rend un article en HTML (tout le contenu externe est échappé)."""
    title = escape(article["title"])
    link = escape(article["link"], quote=True)
    description = escape(article["description"])
    source = escape(article["source"])
    cve_badges = "".join(
        f' <a href="https://nvd.nist.gov/vuln/detail/{escape(cve, quote=True)}" '
        f'style="background:#c0392b;color:#fff;padding:1px 6px;border-radius:3px;'
        f'font-size:11px;text-decoration:none;margin-right:4px;">{escape(cve)}</a>'
        for cve in article["cves"][:5]
    )
    border = "border-left:4px solid #e67e22;" if highlight else ""
    return f"""
        <div style="border:1px solid #ddd;{border}padding:12px 15px;margin-bottom:12px;border-radius:5px;">
            <div style="font-weight:bold;font-size:16px;margin-bottom:6px;">
                <a href="{link}" style="color:#2c3e50;text-decoration:none;">{title}</a>
            </div>
            <div style="font-size:12px;color:#7f8c8d;margin-bottom:6px;">
                <strong>{source}</strong> &middot; {_fmt_date(article["pub_date"])}{cve_badges}
            </div>
            <div style="font-size:14px;color:#333;">{description}</div>
        </div>"""


def format_email_content(articles, days, top_n=10):
    """Construit le digest HTML : statistiques, À la une, puis par catégorie."""
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    if not articles:
        return (f"<html><body><p>Aucune actualité en cybersécurité trouvée "
                f"sur les derniers {days:g} jour(s). ({now_str})</p></body></html>")

    all_cves = sorted({cve for a in articles for cve in a["cves"]})
    sources = {a["source"] for a in articles}
    top_articles = sorted(articles, key=lambda a: a["score"], reverse=True)[:top_n]
    top_links = {a["link"] for a in top_articles}

    by_category = {}
    for article in sorted(articles, key=lambda a: a["pub_date"], reverse=True):
        by_category.setdefault(article["category"], []).append(article)

    html = f"""<html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:Arial,sans-serif;line-height:1.5;color:#333;max-width:780px;margin:auto;padding:10px;">
        <h1 style="color:#2c3e50;">🛡️ CyberNews — {datetime.now().strftime("%d/%m/%Y")}</h1>
        <p style="background:#ecf0f1;padding:10px 15px;border-radius:5px;">
            <strong>{len(articles)}</strong> articles &middot;
            <strong>{len(sources)}</strong> sources &middot;
            <strong>{len(all_cves)}</strong> CVE mentionnées &middot;
            fenêtre de <strong>{days:g}</strong> jour(s)
        </p>
        <h2 style="color:#e67e22;">🔥 À la une</h2>"""
    for article in top_articles:
        html += _render_article(article, highlight=True)

    for category, cat_articles in by_category.items():
        remaining = [a for a in cat_articles if a["link"] not in top_links]
        if not remaining:
            continue
        html += f'<h2 style="color:#3498db;margin-top:25px;">{escape(category)} ({len(remaining)})</h2>'
        for article in remaining:
            html += _render_article(article)

    html += f"""
        <div style="margin-top:30px;font-size:12px;color:#7f8c8d;border-top:1px solid #ddd;padding-top:10px;">
            <p>Digest généré automatiquement le {now_str} par
            <a href="https://github.com/servais1983/Cybernews">CyberNews</a>.</p>
        </div>
    </body></html>"""
    return html


def format_text_content(articles, top_n=10):
    """Version texte brut du digest (partie alternative de l'email)."""
    if not articles:
        return "Aucune actualité en cybersécurité trouvée."
    lines = [f"CyberNews — {datetime.now().strftime('%d/%m/%Y')}", ""]
    for article in sorted(articles, key=lambda a: a["score"], reverse=True)[:top_n]:
        lines.append(f"- {article['title']} ({article['source']})")
        lines.append(f"  {article['link']}")
    lines.append("")
    lines.append(f"... et {max(len(articles) - top_n, 0)} autres articles dans la version HTML.")
    return "\n".join(lines)


def _smtp_connect():
    """Ouvre une connexion SMTP (SSL implicite sur 465, STARTTLS sinon)."""
    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=30)
    else:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.starttls(context=context)
    server.login(SENDER_EMAIL, EMAIL_PASSWORD)
    return server


def send_email(recipient, subject, html_content, text_content):
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = recipient
        message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        print(f"Connexion à {SMTP_SERVER}:{SMTP_PORT}...")
        with _smtp_connect() as server:
            server.sendmail(SENDER_EMAIL, recipient, message.as_string())
        print(f"✓ Email envoyé à {recipient}")
        return True
    except Exception as exc:
        print(f"✗ Erreur lors de l'envoi de l'email : {exc}")
        return False


def test_smtp_connection():
    print(f"Test de connexion SMTP ({SENDER_EMAIL} via {SMTP_SERVER}:{SMTP_PORT})...")
    try:
        with _smtp_connect():
            pass
        print("✓ Connexion SMTP réussie !")
        return True
    except Exception as exc:
        print(f"✗ Erreur de connexion SMTP : {exc}")
        return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="CyberNews — agrégateur RSS intelligent de cybersécurité.")
    parser.add_argument("--days", type=float, default=DEFAULT_DAYS,
                        help=f"fenêtre de récupération en jours (défaut : {DEFAULT_DAYS:g})")
    parser.add_argument("--top", type=int, default=10,
                        help="nombre d'articles dans la section À la une (défaut : 10)")
    parser.add_argument("--max-per-feed", type=int, default=MAX_PER_FEED,
                        help=f"articles maximum par flux (défaut : {MAX_PER_FEED})")
    parser.add_argument("--output", default="digest.html",
                        help="fichier de sortie du digest HTML (défaut : digest.html)")
    parser.add_argument("--dry-run", action="store_true",
                        help="génère le digest sans envoyer d'email")
    parser.add_argument("--test-smtp", action="store_true",
                        help="teste uniquement la connexion SMTP puis quitte")
    parser.add_argument("--list-feeds", action="store_true",
                        help="liste les sources configurées puis quitte")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_feeds:
        for feed in RSS_FEEDS:
            print(f"[{feed['category']}] {feed['name']} — {feed['url']}")
        print(f"\n{len(RSS_FEEDS)} sources configurées.")
        return

    if args.test_smtp:
        sys.exit(0 if test_smtp_connection() else 1)

    articles = deduplicate(get_cybersecurity_news(args.days, args.max_per_feed))
    print(f"{len(articles)} articles retenus après déduplication.")

    html_content = format_email_content(articles, args.days, args.top)
    text_content = format_text_content(articles, args.top)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Aperçu HTML sauvegardé dans {args.output}")

    with open("latest_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    if args.dry_run:
        print("Mode --dry-run : aucun email envoyé.")
        return

    if not articles:
        print("Aucun article : email non envoyé.")
        return

    subject = (f"{EMAIL_SUBJECT_PREFIX}{datetime.now().strftime('%d/%m/%Y')} "
               f"({len(articles)} articles)")
    if not send_email(RECIPIENT_EMAIL, subject, html_content, text_content):
        print(f"L'email n'a pas été envoyé ; le digest reste disponible dans {args.output}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
