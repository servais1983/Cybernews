# -*- coding: utf-8 -*-
"""Tests unitaires de CyberNews (aucun accès réseau requis)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cybersec_rss_feed_enhanced as cn  # noqa: E402

NOW = datetime.now(timezone.utc)


def make_article(**overrides):
    article = {
        "title": "Titre de test",
        "link": "https://example.com/article",
        "description": "Description de test",
        "source": "Source Test",
        "category": "Actualités",
        "pub_date": NOW.isoformat(),
        "score": 1,
        "cves": [],
        "kev": [],
    }
    article.update(overrides)
    return article


# --- clean_html -------------------------------------------------------------

def test_clean_html_strips_tags_and_entities():
    assert cn.clean_html("<p>Hello &amp; <b>world</b></p>") == "Hello & world"


def test_clean_html_truncates_on_word_boundary():
    text = "mot " * 200
    cleaned = cn.clean_html(text, max_len=50)
    assert len(cleaned) <= 50
    assert cleaned.endswith("...")


def test_clean_html_handles_empty():
    assert cn.clean_html("") == ""
    assert cn.clean_html(None) == ""


# --- score_article ----------------------------------------------------------

def test_score_critical_article_outranks_mundane():
    critical, cves = cn.score_article(
        "Critical zero-day CVE-2026-1234 actively exploited in VPN appliances",
        "PoC exploit released, unauthenticated RCE", 3, NOW, NOW)
    mundane, _ = cn.score_article(
        "Weekly recap of conference talks", "Slides available", 0, NOW, NOW)
    assert critical > 50
    assert mundane < 10
    assert cves == ["CVE-2026-1234"]


def test_score_freshness_bonus():
    fresh, _ = cn.score_article("Titre", "texte", 0, NOW, NOW)
    old, _ = cn.score_article("Titre", "texte", 0, NOW - timedelta(days=5), NOW)
    assert fresh == old + 5


def test_score_title_match_counts_double():
    in_title, _ = cn.score_article("Ransomware attack", "", 0, NOW, NOW)
    in_body, _ = cn.score_article("Une attaque", "ransomware attack", 0, NOW, NOW)
    assert in_title > in_body


# --- déduplication ----------------------------------------------------------

def test_deduplicate_keeps_best_scored_version():
    articles = [
        make_article(title="Critical flaw in Acme Router exploited",
                     link="https://a.com/1", source="A", score=20),
        make_article(title="Critical flaw in Acme Router exploited!",
                     link="https://b.com/2", source="B", score=10),
        make_article(title="Totally different story about phishing",
                     link="https://c.com/3", source="C", score=5),
    ]
    kept = cn.deduplicate(articles)
    assert len(kept) == 2
    assert kept[0]["source"] == "A"


def test_deduplicate_same_link_different_query():
    articles = [
        make_article(link="https://a.com/x?utm=1", score=5),
        make_article(title="Autre titre complètement différent ici",
                     link="https://a.com/x?utm=2", score=3),
    ]
    assert len(cn.deduplicate(articles)) == 1


# --- filtres mots-clés ------------------------------------------------------

def test_keyword_include_filter():
    articles = [
        make_article(title="VMware ESXi patch"),
        make_article(title="Conference recap", link="https://b.com/2"),
    ]
    kept = cn.apply_keyword_filters(articles, include=["vmware"], exclude=[])
    assert len(kept) == 1
    assert "VMware" in kept[0]["title"]


def test_keyword_exclude_filter():
    articles = [
        make_article(title="Crypto giveaway scam"),
        make_article(title="Critical RCE in firewall", link="https://b.com/2"),
    ]
    kept = cn.apply_keyword_filters(articles, include=[], exclude=["giveaway"])
    assert len(kept) == 1
    assert "RCE" in kept[0]["title"]


def test_keyword_filters_noop_when_unset():
    articles = [make_article()]
    assert cn.apply_keyword_filters(articles, include=[], exclude=[]) == articles


# --- historique inter-jours -------------------------------------------------

def test_filter_already_sent():
    articles = [
        make_article(link="https://a.com/seen?ref=rss"),
        make_article(link="https://a.com/new", title="Autre"),
    ]
    seen = {"https://a.com/seen": NOW.isoformat()}
    kept = cn.filter_already_sent(articles, seen)
    assert len(kept) == 1
    assert kept[0]["link"] == "https://a.com/new"


def test_link_key_canonicalization():
    assert cn.link_key("https://A.com/Path/?utm_source=x") == "https://a.com/path"


def test_prune_seen_drops_old_entries():
    seen = {
        "recent": NOW.isoformat(),
        "old": (NOW - timedelta(days=60)).isoformat(),
        "invalide": "pas-une-date",
    }
    pruned = cn.prune_seen(seen, max_age_days=30, now=NOW)
    assert set(pruned) == {"recent"}


# --- enrichissement KEV -----------------------------------------------------

def test_mark_kev_articles_boosts_score():
    article = make_article(cves=["CVE-2026-0001", "CVE-2026-0002"], score=10)
    cn.mark_kev_articles([article], {"CVE-2026-0001"})
    assert article["kev"] == ["CVE-2026-0001"]
    assert article["score"] == 20


# --- rendu HTML -------------------------------------------------------------

def test_html_escapes_external_content():
    evil = make_article(
        title="<script>alert(1)</script>",
        link='https://x.com/?"><img src=x>',
        description="<b>injected</b>",
        cves=["CVE-2026-0001"],
        kev=["CVE-2026-0001"],
    )
    html = cn.format_email_content([evil], days=1)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>injected</b>" not in html
    assert "KEV" in html  # badge exploitation active


def test_html_includes_ai_brief_and_summary():
    article = make_article(ai_summary="Résumé <test> en français")
    html = cn.format_email_content([article], days=1,
                                   ai_brief=["Point clé <important>"])
    assert "Synthèse IA" in html
    assert "Point clé &lt;important&gt;" in html
    assert "Résumé &lt;test&gt; en français" in html


def test_html_empty_digest():
    html = cn.format_email_content([], days=1)
    assert "Aucune nouvelle actualité" in html


# --- flux RSS sortant -------------------------------------------------------

def test_generate_rss_escapes_xml():
    article = make_article(title="Faille <critique> & grave",
                           link="https://a.com/x?a=1&b=2")
    rss = cn.generate_rss([article], site_url="https://example.github.io/Cybernews")
    assert "<rss version=" in rss
    assert "Faille &lt;critique&gt; &amp; grave" in rss
    assert "<link>https://a.com/x?a=1&amp;b=2</link>" in rss
    assert "<script" not in rss


def test_generate_rss_prefers_ai_summary():
    article = make_article(description="Description anglaise",
                           ai_summary="Résumé français")
    rss = cn.generate_rss([article])
    assert "Résumé français" in rss


# --- texte (webhooks) -------------------------------------------------------

def test_text_content_includes_digest_url():
    text = cn.format_text_content([make_article()], top_n=5,
                                  digest_url="https://example.github.io/Cybernews/")
    assert "https://example.github.io/Cybernews/" in text
