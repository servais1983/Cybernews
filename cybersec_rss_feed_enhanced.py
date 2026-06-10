#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CyberNews — Agrégateur RSS intelligent de cybersécurité.

Pipeline complet :
  1. Récupération parallèle de plus de 55 flux RSS fiables (avec cache ETag),
  2. Filtrage par mots-clés (KEYWORDS_INCLUDE / KEYWORDS_EXCLUDE),
  3. Score de pertinence (zero-day, exploitation active, RCE, ransomware...),
  4. Déduplication intra-run + historique inter-jours (data/state.json),
  5. Enrichissement CVE : score CVSS (API NVD) + catalogue KEV de la CISA,
  6. Synthèse IA en français via l'API Claude (brief exécutif + résumés),
  7. Diffusion : email HTML, Discord, Slack, Telegram,
  8. Publication : digest.html, GitHub Pages (docs/) + flux RSS sortant.

Usage :
    python cybersec_rss_feed_enhanced.py                 # digest + diffusion
    python cybersec_rss_feed_enhanced.py --dry-run       # digest sans envoi
    python cybersec_rss_feed_enhanced.py --pages         # publie aussi docs/
    python cybersec_rss_feed_enhanced.py --test-smtp     # teste la config SMTP
    python cybersec_rss_feed_enhanced.py --check-feeds   # santé des sources
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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime
from html import escape, unescape
from xml.sax.saxutils import escape as xml_escape

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


def _env_list(name):
    """Lit une variable d'environnement comme liste (séparateur : virgule)."""
    return [item.strip().lower() for item in _env(name).split(",") if item.strip()]


# --- Email (les anciens noms EMAIL_SENDER/EMAIL_RECIPIENT restent acceptés) ---
SENDER_EMAIL = _env("SENDER_EMAIL", "EMAIL_SENDER", default="votre_email@example.com")
RECIPIENT_EMAIL = _env("RECIPIENT_EMAIL", "EMAIL_RECIPIENT", default="votre_email@example.com")
EMAIL_PASSWORD = _env("EMAIL_PASSWORD", default="votre_mot_de_passe_application")
SMTP_SERVER = _env("SMTP_SERVER", default="smtp.gmail.com")
SMTP_PORT = int(_env("SMTP_PORT", default="465"))
EMAIL_SUBJECT_PREFIX = _env("EMAIL_SUBJECT_PREFIX", default="🛡️ CyberNews — ")
DEFAULT_DAYS = float(_env("DAYS_LOOKBACK", default="2"))

# --- Personnalisation ---
KEYWORDS_INCLUDE = _env_list("KEYWORDS_INCLUDE")
KEYWORDS_EXCLUDE = _env_list("KEYWORDS_EXCLUDE")

# --- IA (optionnel : laisser vide pour désactiver) ---
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _env("CLAUDE_MODEL", default="claude-opus-4-8")

# --- Enrichissement CVE (NVD_API_KEY optionnelle, accélère les requêtes) ---
NVD_API_KEY = _env("NVD_API_KEY")
KEV_CATALOG_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# --- Canaux de diffusion supplémentaires (optionnels) ---
DISCORD_WEBHOOK_URL = _env("DISCORD_WEBHOOK_URL")
SLACK_WEBHOOK_URL = _env("SLACK_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# --- Publication GitHub Pages ---
SITE_URL = _env("SITE_URL").rstrip("/")
DOCS_DIR = "docs"
STATE_FILE = os.path.join("data", "state.json")
SEEN_MAX_AGE_DAYS = 30

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
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CyberNewsBot/3.0",
    "Accept": "application/rss+xml, application/xml, application/atom+xml, "
              "text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.8,en-US,en;q=0.5",
}

# --- Sources RSS (plus de 55 flux vérifiés, classés par catégorie) ---
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

# Nombre maximum d'articles conservés par flux.
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


# ---------------------------------------------------------------------------
# Récupération et traitement des articles
# ---------------------------------------------------------------------------

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


def fetch_feed(feed_source, cutoff_date, max_per_feed, cache=None):
    """Récupère et analyse un flux RSS (avec GET conditionnel ETag/Last-Modified).

    Retourne (nom, articles, erreur, cache_http).
    """
    name = feed_source["name"]
    cache = cache or {}
    headers = dict(DEFAULT_HEADERS)
    if cache.get("etag"):
        headers["If-None-Match"] = cache["etag"]
    if cache.get("last_modified"):
        headers["If-Modified-Since"] = cache["last_modified"]

    try:
        response = session.get(feed_source["url"], headers=headers, timeout=TIMEOUT)
        if response.status_code == 304:
            return name, [], None, cache  # flux inchangé depuis le dernier run
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as exc:
        return name, [], str(exc), cache

    new_cache = {
        key: value
        for key, value in (
            ("etag", response.headers.get("ETag")),
            ("last_modified", response.headers.get("Last-Modified")),
        )
        if value
    }

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
                "kev": [],
            })
        except Exception:
            continue
    return name, articles, None, new_cache


def get_cybersecurity_news(days, max_per_feed=MAX_PER_FEED, etags=None):
    """Récupère tous les flux en parallèle. Retourne (articles, nouveaux etags)."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    etags = etags or {}
    print(f"Récupération de {len(RSS_FEEDS)} flux RSS (fenêtre : {days:g} jour(s))...")

    all_articles, failures, new_etags = [], [], {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_feed, feed, cutoff_date, max_per_feed, etags.get(feed["url"])): feed
            for feed in RSS_FEEDS
        }
        for future in as_completed(futures):
            feed = futures[future]
            name, articles, error, cache = future.result()
            if cache:
                new_etags[feed["url"]] = cache
            if error:
                failures.append(name)
                print(f"  ✗ {name}: {error}")
            else:
                print(f"  ✓ {name}: {len(articles)} article(s)")
                all_articles.extend(articles)

    print(f"\n{len(all_articles)} articles récupérés, {len(failures)} flux en échec"
          f"{' (' + ', '.join(failures) + ')' if failures else ''}.")
    return all_articles, new_etags


def link_key(link):
    """Clé canonique d'un lien pour la déduplication et l'historique."""
    return link.split("?")[0].rstrip("/").lower()


def apply_keyword_filters(articles, include=None, exclude=None):
    """Filtre les articles selon les listes de mots-clés (insensible à la casse)."""
    include = KEYWORDS_INCLUDE if include is None else include
    exclude = KEYWORDS_EXCLUDE if exclude is None else exclude
    if not include and not exclude:
        return articles

    def haystack(article):
        return f"{article['title']} {article['description']}".lower()

    kept = articles
    if include:
        kept = [a for a in kept if any(k in haystack(a) for k in include)]
    if exclude:
        kept = [a for a in kept if not any(k in haystack(a) for k in exclude)]
    removed = len(articles) - len(kept)
    if removed:
        print(f"Filtres mots-clés : {removed} article(s) écarté(s).")
    return kept


def deduplicate(articles):
    """Supprime les doublons (même lien ou titres quasi identiques entre sources).

    Les articles sont parcourus par score décroissant pour conserver
    la version la mieux notée de chaque histoire.
    """
    kept, seen_links, seen_titles = [], set(), []
    for article in sorted(articles, key=lambda a: a["score"], reverse=True):
        key = link_key(article["link"])
        if key and key in seen_links:
            continue
        norm = re.sub(r"[^a-z0-9 ]", "", article["title"].lower()).strip()
        if any(
            SequenceMatcher(None, norm, seen).ratio() > 0.92
            for seen in seen_titles
            if abs(len(seen) - len(norm)) < 20
        ):
            continue
        seen_links.add(key)
        seen_titles.append(norm)
        kept.append(article)
    removed = len(articles) - len(kept)
    if removed:
        print(f"Déduplication : {removed} doublon(s) supprimé(s).")
    return kept


def filter_already_sent(articles, seen):
    """Écarte les articles déjà envoyés lors des runs précédents."""
    kept = [a for a in articles if link_key(a["link"]) not in seen]
    removed = len(articles) - len(kept)
    if removed:
        print(f"Historique : {removed} article(s) déjà envoyé(s) précédemment.")
    return kept


# ---------------------------------------------------------------------------
# Historique inter-jours (data/state.json)
# ---------------------------------------------------------------------------

def load_state():
    """Charge l'état persistant (liens déjà envoyés + cache ETag des flux)."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        return {"seen": state.get("seen", {}), "etags": state.get("etags", {})}
    except (OSError, ValueError):
        return {"seen": {}, "etags": {}}


def prune_seen(seen, max_age_days=SEEN_MAX_AGE_DAYS, now=None):
    """Supprime les entrées de l'historique plus vieilles que `max_age_days`."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    pruned = {}
    for key, iso_date in seen.items():
        try:
            if datetime.fromisoformat(iso_date) >= cutoff:
                pruned[key] = iso_date
        except ValueError:
            continue
    return pruned


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state["seen"] = prune_seen(state.get("seen", {}))
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)


# ---------------------------------------------------------------------------
# Enrichissement CVE : catalogue KEV (CISA) + scores CVSS (NVD)
# ---------------------------------------------------------------------------

def fetch_kev_catalog():
    """Retourne l'ensemble des CVE du catalogue KEV (exploitation active connue)."""
    try:
        response = session.get(KEV_CATALOG_URL, headers=DEFAULT_HEADERS, timeout=30)
        response.raise_for_status()
        kev = {v["cveID"].upper() for v in response.json().get("vulnerabilities", [])}
        print(f"Catalogue KEV : {len(kev)} CVE en exploitation active connue.")
        return kev
    except Exception as exc:
        print(f"  ! Catalogue KEV indisponible : {exc}")
        return set()


def mark_kev_articles(articles, kev_catalog):
    """Marque les articles citant une CVE du catalogue KEV (+10 au score)."""
    for article in articles:
        article["kev"] = [cve for cve in article["cves"] if cve in kev_catalog]
        if article["kev"]:
            article["score"] += 10


def fetch_cvss_scores(cve_ids, api_key=NVD_API_KEY, max_cves=12):
    """Interroge l'API NVD pour les scores CVSS (rate limit public : 5 req/30 s)."""
    if not cve_ids:
        return {}
    headers = {"apiKey": api_key} if api_key else {}
    delay = 1.0 if api_key else 6.5
    info = {}
    print(f"Enrichissement CVSS via NVD ({min(len(cve_ids), max_cves)} CVE)...")
    for i, cve in enumerate(cve_ids[:max_cves]):
        if i:
            time.sleep(delay)
        try:
            response = session.get(NVD_API_URL, params={"cveId": cve},
                                   headers=headers, timeout=20)
            response.raise_for_status()
            vulns = response.json().get("vulnerabilities", [])
            metrics = vulns[0]["cve"].get("metrics", {}) if vulns else {}
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    metric = metrics[key][0]
                    data = metric.get("cvssData", {})
                    severity = data.get("baseSeverity") or metric.get("baseSeverity") or ""
                    info[cve] = {"score": data.get("baseScore"), "severity": severity.upper()}
                    break
        except Exception:
            continue
    print(f"  {len(info)} score(s) CVSS récupéré(s).")
    return info


def enrich_articles_cvss(articles, max_cves=12):
    """Récupère les scores CVSS des CVE des articles les mieux notés."""
    ordered_cves, seen = [], set()
    for article in sorted(articles, key=lambda a: a["score"], reverse=True):
        for cve in article["cves"]:
            if cve not in seen:
                seen.add(cve)
                ordered_cves.append(cve)
    cvss = fetch_cvss_scores(ordered_cves, max_cves=max_cves)
    for article in articles:
        article["cvss"] = {cve: cvss[cve] for cve in article["cves"] if cve in cvss}
    return cvss


# ---------------------------------------------------------------------------
# Synthèse IA (API Claude) — brief exécutif + résumés en français
# ---------------------------------------------------------------------------

AI_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "brief": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 à 5 points clés du jour, en français",
        },
        "resumes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "resume": {"type": "string"},
                },
                "required": ["id", "resume"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["brief", "resumes"],
    "additionalProperties": False,
}

AI_SYSTEM_PROMPT = (
    "Tu es un analyste senior en cybersécurité. On te fournit la liste des articles "
    "les plus importants du jour (JSON avec id, titre, source, description). "
    "Produis :\n"
    "1. 'brief' : 3 à 5 points clés du jour en français, orientés action "
    "(ce qu'un RSSI doit savoir/faire), concis (une phrase par point).\n"
    "2. 'resumes' : pour chaque article, une seule phrase de résumé EN FRANÇAIS "
    "(traduis si l'article est en anglais), factuelle et précise, reprenant l'id fourni."
)


def ai_enhance(articles, top_n=12):
    """Génère via l'API Claude un brief exécutif FR et des résumés par article.

    Retourne la liste des points du brief (ou None si IA indisponible).
    Les résumés sont ajoutés en place sous la clé 'ai_summary'.
    """
    if not ANTHROPIC_API_KEY or not articles:
        return None
    try:
        import anthropic
    except ImportError:
        print("  ! Paquet 'anthropic' non installé : synthèse IA désactivée "
              "(pip install anthropic).")
        return None

    top = sorted(articles, key=lambda a: a["score"], reverse=True)[:top_n]
    payload = [
        {"id": i, "titre": a["title"], "source": a["source"],
         "description": a["description"]}
        for i, a in enumerate(top)
    ]
    print(f"Synthèse IA ({CLAUDE_MODEL}) sur les {len(top)} meilleurs articles...")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=AI_SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": json.dumps(payload, ensure_ascii=False)}],
            output_config={"format": {"type": "json_schema",
                                      "schema": AI_OUTPUT_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
    except Exception as exc:
        print(f"  ! Synthèse IA indisponible : {exc}")
        return None

    summaries = {item["id"]: item["resume"] for item in data.get("resumes", [])}
    for i, article in enumerate(top):
        if i in summaries:
            article["ai_summary"] = summaries[i]
    print(f"  Brief généré ({len(data.get('brief', []))} points), "
          f"{len(summaries)} résumé(s) ajoutés.")
    return data.get("brief") or None


# ---------------------------------------------------------------------------
# Rendu HTML / texte
# ---------------------------------------------------------------------------

def _fmt_date(iso_date):
    try:
        return datetime.fromisoformat(iso_date).astimezone().strftime("%d/%m/%Y à %H:%M")
    except ValueError:
        return iso_date


def _cve_badge(article, cve):
    """Badge HTML d'une CVE : lien NVD + score CVSS + marqueur KEV éventuel."""
    label = cve
    info = article.get("cvss", {}).get(cve)
    if info and info.get("score") is not None:
        label += f" · CVSS {info['score']}"
    if cve in article.get("kev", []):
        label += " ⚠️ KEV"
        color = "#7b0000"
    elif info and (info.get("score") or 0) >= 9:
        color = "#a30000"
    else:
        color = "#c0392b"
    return (f' <a href="https://nvd.nist.gov/vuln/detail/{escape(cve, quote=True)}" '
            f'style="background:{color};color:#fff;padding:1px 6px;border-radius:3px;'
            f'font-size:11px;text-decoration:none;margin-right:4px;">{escape(label)}</a>')


def _render_article(article, highlight=False):
    """Rend un article en HTML (tout le contenu externe est échappé)."""
    title = escape(article["title"])
    link = escape(article["link"], quote=True)
    source = escape(article["source"])
    cve_badges = "".join(_cve_badge(article, cve) for cve in article["cves"][:5])
    ai_summary = ""
    if article.get("ai_summary"):
        ai_summary = (f'<div style="font-size:14px;color:#1a5276;font-style:italic;'
                      f'margin-bottom:4px;">🧠 {escape(article["ai_summary"])}</div>')
    border = "border-left:4px solid #e67e22;" if highlight else ""
    return f"""
        <div style="border:1px solid #ddd;{border}padding:12px 15px;margin-bottom:12px;border-radius:5px;">
            <div style="font-weight:bold;font-size:16px;margin-bottom:6px;">
                <a href="{link}" style="color:#2c3e50;text-decoration:none;">{title}</a>
            </div>
            <div style="font-size:12px;color:#7f8c8d;margin-bottom:6px;">
                <strong>{source}</strong> &middot; {_fmt_date(article["pub_date"])}{cve_badges}
            </div>
            {ai_summary}
            <div style="font-size:14px;color:#333;">{escape(article["description"])}</div>
        </div>"""


def format_email_content(articles, days, top_n=10, ai_brief=None):
    """Construit le digest HTML : brief IA, statistiques, À la une, catégories."""
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    if not articles:
        return (f"<html><body><p>Aucune nouvelle actualité en cybersécurité "
                f"sur les derniers {days:g} jour(s). ({now_str})</p></body></html>")

    all_cves = sorted({cve for a in articles for cve in a["cves"]})
    kev_cves = sorted({cve for a in articles for cve in a.get("kev", [])})
    sources = {a["source"] for a in articles}
    top_articles = sorted(articles, key=lambda a: a["score"], reverse=True)[:top_n]
    top_links = {a["link"] for a in top_articles}

    by_category = {}
    for article in sorted(articles, key=lambda a: a["pub_date"], reverse=True):
        by_category.setdefault(article["category"], []).append(article)

    kev_stat = (f' &middot; <strong style="color:#a30000;">{len(kev_cves)}</strong> '
                f'CVE en exploitation active (KEV)') if kev_cves else ""
    html = f"""<html>
    <head><meta charset="utf-8"><title>CyberNews — {datetime.now().strftime("%d/%m/%Y")}</title></head>
    <body style="font-family:Arial,sans-serif;line-height:1.5;color:#333;max-width:780px;margin:auto;padding:10px;">
        <h1 style="color:#2c3e50;">🛡️ CyberNews — {datetime.now().strftime("%d/%m/%Y")}</h1>
        <p style="background:#ecf0f1;padding:10px 15px;border-radius:5px;">
            <strong>{len(articles)}</strong> articles &middot;
            <strong>{len(sources)}</strong> sources &middot;
            <strong>{len(all_cves)}</strong> CVE mentionnées{kev_stat} &middot;
            fenêtre de <strong>{days:g}</strong> jour(s)
        </p>"""

    if ai_brief:
        points = "".join(f"<li>{escape(point)}</li>" for point in ai_brief)
        html += f"""
        <div style="background:#eaf2f8;border-left:4px solid #1a5276;padding:10px 15px;border-radius:5px;">
            <h2 style="color:#1a5276;margin-top:0;">🧠 Synthèse IA du jour</h2>
            <ul style="margin-bottom:0;">{points}</ul>
        </div>"""

    html += '<h2 style="color:#e67e22;">🔥 À la une</h2>'
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


def format_text_content(articles, top_n=10, ai_brief=None, digest_url=""):
    """Version texte brut du digest (email alternatif et webhooks)."""
    if not articles:
        return "Aucune nouvelle actualité en cybersécurité aujourd'hui."
    lines = [f"🛡️ CyberNews — {datetime.now().strftime('%d/%m/%Y')} "
             f"({len(articles)} articles)", ""]
    if ai_brief:
        lines.append("🧠 Synthèse du jour :")
        lines.extend(f"• {point}" for point in ai_brief)
        lines.append("")
    lines.append("🔥 À la une :")
    for article in sorted(articles, key=lambda a: a["score"], reverse=True)[:top_n]:
        kev = " ⚠️ KEV" if article.get("kev") else ""
        lines.append(f"- {article['title']} ({article['source']}){kev}")
        lines.append(f"  {article['link']}")
    if digest_url:
        lines.append("")
        lines.append(f"Digest complet : {digest_url}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Diffusion : email, Discord, Slack, Telegram
# ---------------------------------------------------------------------------

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


def broadcast_to_channels(text_content):
    """Envoie le résumé texte vers Discord, Slack et Telegram si configurés."""
    sent = []
    if DISCORD_WEBHOOK_URL:
        try:
            session.post(DISCORD_WEBHOOK_URL,
                         json={"content": text_content[:1990]}, timeout=15
                         ).raise_for_status()
            sent.append("Discord")
        except Exception as exc:
            print(f"  ! Discord : {exc}")
    if SLACK_WEBHOOK_URL:
        try:
            session.post(SLACK_WEBHOOK_URL,
                         json={"text": text_content}, timeout=15).raise_for_status()
            sent.append("Slack")
        except Exception as exc:
            print(f"  ! Slack : {exc}")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            session.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text_content[:4000],
                      "disable_web_page_preview": True},
                timeout=15,
            ).raise_for_status()
            sent.append("Telegram")
        except Exception as exc:
            print(f"  ! Telegram : {exc}")
    if sent:
        print(f"✓ Diffusé sur : {', '.join(sent)}")
    return sent


# ---------------------------------------------------------------------------
# Publication : GitHub Pages (docs/) + flux RSS sortant
# ---------------------------------------------------------------------------

def generate_rss(articles, site_url="", max_items=50):
    """Génère un flux RSS 2.0 à partir du digest (CyberNews devient une source)."""
    items = []
    for article in sorted(articles, key=lambda a: a["score"], reverse=True)[:max_items]:
        try:
            pub = format_datetime(datetime.fromisoformat(article["pub_date"]))
        except ValueError:
            pub = ""
        description = article.get("ai_summary") or article["description"]
        attr_link = xml_escape(article["link"], {'"': "&quot;"})
        items.append(
            "    <item>\n"
            f"      <title>{xml_escape(article['title'])}</title>\n"
            f"      <link>{xml_escape(article['link'])}</link>\n"
            f'      <guid isPermaLink="false">{xml_escape(link_key(article["link"]))}</guid>\n'
            f"      <pubDate>{xml_escape(pub)}</pubDate>\n"
            f'      <source url="{attr_link}">{xml_escape(article["source"])}</source>\n'
            f"      <description>{xml_escape(description)}</description>\n"
            "    </item>"
        )
    link = xml_escape(site_url or "https://github.com/servais1983/Cybernews")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>CyberNews — Digest cybersécurité</title>\n"
        f"    <link>{link}</link>\n"
        "    <description>Articles cybersécurité agrégés, dédupliqués et "
        "classés par pertinence depuis plus de 55 sources fiables.</description>\n"
        "    <language>fr</language>\n"
        f"    <lastBuildDate>{xml_escape(format_datetime(datetime.now(timezone.utc)))}</lastBuildDate>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )


def _archive_nav():
    """Construit la liste HTML des archives présentes dans docs/archive/."""
    archive_dir = os.path.join(DOCS_DIR, "archive")
    try:
        dates = sorted(
            (f[:-5] for f in os.listdir(archive_dir) if f.endswith(".html")),
            reverse=True,
        )
    except OSError:
        return ""
    links = " &middot; ".join(
        f'<a href="archive/{escape(d, quote=True)}.html">{escape(d)}</a>'
        for d in dates[:30]
    )
    return (f'<div style="margin-top:20px;font-size:13px;color:#7f8c8d;">'
            f'<strong>Archives :</strong> {links}</div>') if links else ""


def publish_pages(html_content, articles):
    """Publie le digest sur docs/ (GitHub Pages) : index, archive datée, feed.xml."""
    archive_dir = os.path.join(DOCS_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    with open(os.path.join(archive_dir, f"{today}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    feed_link = '<p><a href="feed.xml">📡 S\'abonner au flux RSS de ce digest</a></p>'
    index_html = html_content.replace("</body>", f"{feed_link}{_archive_nav()}</body>")
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    with open(os.path.join(DOCS_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(generate_rss(articles, SITE_URL))
    print(f"✓ Pages publiées dans {DOCS_DIR}/ (index, archive/{today}.html, feed.xml)")


# ---------------------------------------------------------------------------
# Santé des flux
# ---------------------------------------------------------------------------

def check_feeds():
    """Vérifie que chaque flux répond et contient des entrées. Code retour 1 sinon."""
    print(f"Vérification de {len(RSS_FEEDS)} flux RSS...")
    dead = []

    def probe(feed):
        try:
            response = session.get(feed["url"], headers=DEFAULT_HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if not parsed.entries:
                return feed["name"], "flux vide (0 entrée)"
            return feed["name"], None
        except Exception as exc:
            return feed["name"], str(exc)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for future in as_completed([executor.submit(probe, f) for f in RSS_FEEDS]):
            name, error = future.result()
            if error:
                dead.append(name)
                print(f"  ✗ {name}: {error}")
            else:
                print(f"  ✓ {name}")

    if dead:
        print(f"\n{len(dead)} flux en échec : {', '.join(dead)}")
        return 1
    print("\nTous les flux répondent.")
    return 0


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

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
    parser.add_argument("--pages", action="store_true",
                        help="publie aussi le digest sur docs/ (GitHub Pages + RSS)")
    parser.add_argument("--no-ai", action="store_true",
                        help="désactive la synthèse IA même si ANTHROPIC_API_KEY est définie")
    parser.add_argument("--no-enrich", action="store_true",
                        help="désactive l'enrichissement KEV/CVSS")
    parser.add_argument("--no-history", action="store_true",
                        help="ignore l'historique des articles déjà envoyés")
    parser.add_argument("--dry-run", action="store_true",
                        help="génère le digest sans envoyer d'email ni de webhook")
    parser.add_argument("--test-smtp", action="store_true",
                        help="teste uniquement la connexion SMTP puis quitte")
    parser.add_argument("--check-feeds", action="store_true",
                        help="vérifie la santé de toutes les sources puis quitte")
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

    if args.check_feeds:
        sys.exit(check_feeds())

    if args.test_smtp:
        sys.exit(0 if test_smtp_connection() else 1)

    state = load_state()

    # 1. Récupération + filtres + déduplication + historique
    articles, new_etags = get_cybersecurity_news(
        args.days, args.max_per_feed,
        etags=state["etags"] if not args.no_history else None,
    )
    articles = apply_keyword_filters(articles)
    articles = deduplicate(articles)
    if not args.no_history:
        articles = filter_already_sent(articles, state["seen"])
    print(f"{len(articles)} articles retenus.")

    # 2. Enrichissement KEV + CVSS
    if articles and not args.no_enrich:
        mark_kev_articles(articles, fetch_kev_catalog())
        enrich_articles_cvss(articles)

    # 3. Synthèse IA (brief exécutif + résumés français)
    ai_brief = None
    if articles and not args.no_ai:
        ai_brief = ai_enhance(articles, top_n=max(args.top, 12))

    # 4. Rendu
    digest_url = f"{SITE_URL}/" if SITE_URL else ""
    html_content = format_email_content(articles, args.days, args.top, ai_brief)
    text_content = format_text_content(articles, args.top, ai_brief, digest_url)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Aperçu HTML sauvegardé dans {args.output}")
    with open("latest_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    if args.pages:
        publish_pages(html_content, articles)

    if args.dry_run:
        print("Mode --dry-run : aucun envoi, historique inchangé.")
        return

    # 5. Diffusion
    if not articles:
        print("Aucun nouvel article : pas d'envoi.")
        state["etags"] = new_etags
        save_state(state)
        return

    subject = (f"{EMAIL_SUBJECT_PREFIX}{datetime.now().strftime('%d/%m/%Y')} "
               f"({len(articles)} articles)")
    email_ok = send_email(RECIPIENT_EMAIL, subject, html_content, text_content)
    broadcast_to_channels(text_content)

    if not email_ok:
        print(f"L'email n'a pas été envoyé ; le digest reste disponible dans {args.output}.")
        sys.exit(1)

    # 6. Persistance de l'historique (uniquement après un envoi réussi)
    now_iso = datetime.now(timezone.utc).isoformat()
    for article in articles:
        state["seen"][link_key(article["link"])] = now_iso
    state["etags"] = new_etags
    save_state(state)
    print("Historique mis à jour.")


if __name__ == "__main__":
    main()
