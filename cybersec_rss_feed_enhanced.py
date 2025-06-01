#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'extraction des nouveautés en cybersécurité depuis des flux RSS
Ce script récupère les dernières actualités en cybersécurité à partir de sources RSS fiables
et les envoie par email à l'adresse spécifiée.
"""

import sys
import os
import json
import smtplib
import ssl
import feedparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from html import unescape
import re

from dotenv import load_dotenv
load_dotenv()

# Charger les variables d'environnement
load_dotenv()

# Configuration des paramètres
RECIPIENT_EMAIL = os.getenv("EMAIL_RECIPIENT", "")
SENDER_EMAIL = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "Actualités en Cybersécurité - ")

# Sources RSS de cybersécurité
RSS_FEEDS = [
    {
        "name": "The Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "logo": "https://thehackernews.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "WeLiveSecurity",
        "url": "https://www.welivesecurity.com/en/rss/feed/",
        "logo": "https://www.welivesecurity.com/wp-content/themes/wls-new/images/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CyberAlerts.io",
        "url": "https://cyberalerts.io/rss/latest-public",
        "logo": "https://cyberalerts.io/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Security Magazine",
        "url": "https://www.securitymagazine.com/rss/topic/2236-cybersecurity",
        "logo": "https://www.securitymagazine.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "NCSC UK",
        "url": "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml",
        "logo": "https://www.ncsc.gov.uk/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Krebs on Security",
        "url": "https://krebsonsecurity.com/feed/",
        "logo": "https://krebsonsecurity.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Dark Reading",
        "url": "https://www.darkreading.com/rss.xml",
        "logo": "https://www.darkreading.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Bleeping Computer",
        "url": "https://www.bleepingcomputer.com/feed/",
        "logo": "https://www.bleepingcomputer.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ANSSI",
        "url": "https://www.ssi.gouv.fr/feed/actualite/",
        "logo": "https://www.ssi.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SC Magazine",
        "url": "https://www.scmagazine.com/feed",
        "logo": "https://www.scmagazine.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Internet Storm Center",
        "url": "https://isc.sans.edu/rssfeed.xml",
        "logo": "https://isc.sans.edu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "LinkedIn Security",
        "url": "https://www.linkedin.com/feed/news/topic/cybersecurity/rss",
        "logo": "https://www.linkedin.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "VirusTotal Blog",
        "url": "https://blog.virustotal.com/feeds/posts/default",
        "logo": "https://www.virustotal.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Recorded Future",
        "url": "https://www.recordedfuture.com/feed",
        "logo": "https://www.recordedfuture.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SecurityWeek",
        "url": "https://feeds.feedburner.com/SecurityWeek",
        "logo": "https://www.securityweek.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Infosecurity Magazine",
        "url": "https://www.infosecurity-magazine.com/rss/news/",
        "logo": "https://www.infosecurity-magazine.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Pirate Magazine",
        "url": "https://www.pirates-magazine.com/feed/",
        "logo": "https://www.pirates-magazine.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "MITRE ATT&CK",
        "url": "https://medium.com/feed/mitre-attack",
        "logo": "https://attack.mitre.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Maltego Blog",
        "url": "https://www.maltego.com/blog/feed/",
        "logo": "https://www.maltego.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SecTools.org",
        "url": "https://sectools.org/feed/",
        "logo": "https://sectools.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CERT-FR",
        "url": "https://www.cert.ssi.gouv.fr/feed/",
        "logo": "https://www.cert.ssi.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Naked Security",
        "url": "https://nakedsecurity.sophos.com/feed",
        "logo": "https://nakedsecurity.sophos.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Security Affairs",
        "url": "https://securityaffairs.com/feed",
        "logo": "https://securityaffairs.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ZDNet Security",
        "url": "https://www.zdnet.com/topic/security/rss.xml",
        "logo": "https://www.zdnet.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ThreatPost",
        "url": "https://threatpost.com/feed/",
        "logo": "https://threatpost.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Packet Storm Security",
        "url": "https://rss.packetstormsecurity.com/news/",
        "logo": "https://packetstormsecurity.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CERT-FR Alertes",
        "url": "https://cert.ssi.gouv.fr/alerte/feed/",
        "logo": "https://cert.ssi.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CERT-FR Avis",
        "url": "https://cert.ssi.gouv.fr/avis/feed/",
        "logo": "https://cert.ssi.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Le Journal du Hack",
        "url": "https://www.journalduhack.com/feed/",
        "logo": "https://www.journalduhack.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ZATAZ Magazine",
        "url": "https://www.zataz.com/feed/",
        "logo": "https://www.zataz.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CVE Details",
        "url": "https://www.cvedetails.com/vulnerability-feed.php",
        "logo": "https://www.cvedetails.com/favicon.ico",
        "max_articles": 10
    },
    {
        "name": "NVD Recent Vulnerabilities",
        "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",
        "logo": "https://nvd.nist.gov/favicon.ico",
        "max_articles": 10
    },
    {
        "name": "Exploit-DB RSS",
        "url": "https://www.exploit-db.com/rss.xml",
        "logo": "https://www.exploit-db.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Cybersécurité.gouv.fr",
        "url": "https://www.cybermalveillance.gouv.fr/feed/",
        "logo": "https://www.cybermalveillance.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "MISC Magazine",
        "url": "https://connect.ed-diamond.com/misc/rss",
        "logo": "https://connect.ed-diamond.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "LeHack",
        "url": "https://lehack.org/feed",
        "logo": "https://lehack.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "UnderNews",
        "url": "https://www.undernews.fr/feed",
        "logo": "https://www.undernews.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "IT-Connect Sécurité",
        "url": "https://www.it-connect.fr/categorie/securite-et-hacking/feed",
        "logo": "https://www.it-connect.fr/favicon.ico",
        "max_articles": 5
    }
]

RSS_FEEDS.extend([
    {
        "name": "DarkReading Dark Web",
        "url": "https://www.darkreading.com/dark-web/rss.xml",
        "logo": "https://www.darkreading.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "HackRead Dark Web News",
        "url": "https://www.hackread.com/category/dark-web/feed/",
        "logo": "https://www.hackread.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Intelligence X",
        "url": "https://intelx.io/feed",
        "logo": "https://intelx.io/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Flashpoint Intel",
        "url": "https://www.flashpoint.io/blog/feed/",
        "logo": "https://www.flashpoint.io/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Digital Shadows",
        "url": "https://www.digitalshadows.com/blog-and-research/feed/",
        "logo": "https://www.digitalshadows.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "RiskIQ Dark Web",
        "url": "https://www.riskiq.com/feed/",
        "logo": "https://www.riskiq.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "PhishLabs Blog",
        "url": "https://www.phishlabs.com/feed/",
        "logo": "https://www.phishlabs.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Group-IB Blog",
        "url": "https://www.group-ib.com/blog/feed/",
        "logo": "https://www.group-ib.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Darknet Live",
        "url": "https://darknetlive.com/feed/",
        "logo": "https://darknetlive.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Recorded Future Dark Web",
        "url": "https://www.recordedfuture.com/category/dark-web/feed",
        "logo": "https://www.recordedfuture.com/favicon.ico",
        "max_articles": 5
    }
])

# Sources supplémentaires pour la cybersécurité et le Dark Web
RSS_FEEDS.extend([
    {
        "name": "HackerCombat",
        "url": "https://hackercombat.com/feed/",
        "logo": "https://hackercombat.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "GBHackers On Security",
        "url": "https://gbhackers.com/feed/",
        "logo": "https://gbhackers.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Hackaday",
        "url": "https://hackaday.com/blog/feed/",
        "logo": "https://hackaday.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CyberDefense Magazine",
        "url": "https://www.cyberdefensemagazine.com/feed/",
        "logo": "https://www.cyberdefensemagazine.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "DataBreaches.net",
        "url": "https://www.databreaches.net/feed/",
        "logo": "https://www.databreaches.net/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Darknet Market News",
        "url": "https://darknetdaily.com/feed/",
        "logo": "https://darknetdaily.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Privacy Affairs Dark Web",
        "url": "https://www.privacyaffairs.com/dark-web/feed/",
        "logo": "https://www.privacyaffairs.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "OSINT Curious Project",
        "url": "https://osintcurio.us/feed/",
        "logo": "https://osintcurio.us/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Cyber War Zone",
        "url": "https://cyberwarzone.com/feed/",
        "logo": "https://cyberwarzone.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "The CyberWire",
        "url": "https://thecyberwire.com/feeds/rss.xml",
        "logo": "https://thecyberwire.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Security Boulevard",
        "url": "https://securityboulevard.com/feed/",
        "logo": "https://securityboulevard.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Helpnet Security",
        "url": "https://www.helpnetsecurity.com/feed/",
        "logo": "https://www.helpnetsecurity.com/favicon.ico",
        "max_articles": 5
    }
])

RSS_FEEDS.extend([
    {
        "name": "AI Trends",
        "url": "https://www.aitrends.com/feed/",
        "logo": "https://www.aitrends.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Business",
        "url": "https://aibusiness.com/feed/",
        "logo": "https://aibusiness.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "logo": "https://www.artificialintelligence-news.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Weekly",
        "url": "https://aiweekly.co/feed/",
        "logo": "https://aiweekly.co/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Synced",
        "url": "https://syncedreview.com/feed/",
        "logo": "https://syncedreview.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Time Journal",
        "url": "https://www.aitimejournal.com/feed/",
        "logo": "https://www.aitimejournal.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Trends France",
        "url": "https://www.aitrends.fr/feed/",
        "logo": "https://www.aitrends.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Intelligence Artificielle France",
        "url": "https://www.intelligence-artificielle-france.fr/feed/",
        "logo": "https://www.intelligence-artificielle-france.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Healthcare",
        "url": "https://www.aiin.healthcare/feed/",
        "logo": "https://www.aiin.healthcare/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Ethics",
        "url": "https://aiethics.princeton.edu/feed/",
        "logo": "https://aiethics.princeton.edu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Alignment",
        "url": "https://www.alignment.org/blog/feed/",
        "logo": "https://www.alignment.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Safety",
        "url": "https://www.safe.ai/feed/",
        "logo": "https://www.safe.ai/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Research",
        "url": "https://www.airesearch.com/feed/",
        "logo": "https://www.airesearch.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Development",
        "url": "https://www.aidevelopment.com/feed/",
        "logo": "https://www.aidevelopment.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Applications",
        "url": "https://www.aiapplications.com/feed/",
        "logo": "https://www.aiapplications.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Industry",
        "url": "https://www.aiindustry.com/feed/",
        "logo": "https://www.aiindustry.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Technology",
        "url": "https://www.aitechnology.com/feed/",
        "logo": "https://www.aitechnology.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Innovation",
        "url": "https://www.aiinnovation.com/feed/",
        "logo": "https://www.aiinnovation.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Future",
        "url": "https://www.aifuture.com/feed/",
        "logo": "https://www.aifuture.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Society",
        "url": "https://www.aisociety.com/feed/",
        "logo": "https://www.aisociety.com/favicon.ico",
        "max_articles": 5
    }
])

RSS_FEEDS.extend([
    {
        "name": "AI in Finance",
        "url": "https://www.aifinance.com/feed/",
        "logo": "https://www.aifinance.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Manufacturing",
        "url": "https://www.aimanufacturing.com/feed/",
        "logo": "https://www.aimanufacturing.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Education",
        "url": "https://www.aieducation.com/feed/",
        "logo": "https://www.aieducation.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Transportation",
        "url": "https://www.aitransportation.com/feed/",
        "logo": "https://www.aitransportation.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Retail",
        "url": "https://www.airetail.com/feed/",
        "logo": "https://www.airetail.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Agriculture",
        "url": "https://www.aiagriculture.com/feed/",
        "logo": "https://www.aiagriculture.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Energy",
        "url": "https://www.aienergy.com/feed/",
        "logo": "https://www.aienergy.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Defense",
        "url": "https://www.aidefense.com/feed/",
        "logo": "https://www.aidefense.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Space",
        "url": "https://www.aispace.com/feed/",
        "logo": "https://www.aispace.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Gaming",
        "url": "https://www.aigaming.com/feed/",
        "logo": "https://www.aigaming.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Robotics",
        "url": "https://www.airobotics.com/feed/",
        "logo": "https://www.airobotics.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Marketing",
        "url": "https://www.aimarketing.com/feed/",
        "logo": "https://www.aimarketing.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in HR",
        "url": "https://www.aihr.com/feed/",
        "logo": "https://www.aihr.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Legal",
        "url": "https://www.ailegal.com/feed/",
        "logo": "https://www.ailegal.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Media",
        "url": "https://www.aimedia.com/feed/",
        "logo": "https://www.aimedia.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Sports",
        "url": "https://www.aisports.com/feed/",
        "logo": "https://www.aisports.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Music",
        "url": "https://www.aimusic.com/feed/",
        "logo": "https://www.aimusic.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Art",
        "url": "https://www.aiart.com/feed/",
        "logo": "https://www.aiart.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Fashion",
        "url": "https://www.aifashion.com/feed/",
        "logo": "https://www.aifashion.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Architecture",
        "url": "https://www.aiarchitecture.com/feed/",
        "logo": "https://www.aiarchitecture.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Construction",
        "url": "https://www.aiconstruction.com/feed/",
        "logo": "https://www.aiconstruction.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Real Estate",
        "url": "https://www.airealestate.com/feed/",
        "logo": "https://www.airealestate.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Insurance",
        "url": "https://www.aiinsurance.com/feed/",
        "logo": "https://www.aiinsurance.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Banking",
        "url": "https://www.aibanking.com/feed/",
        "logo": "https://www.aibanking.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI in Telecom",
        "url": "https://www.aitelecom.com/feed/",
        "logo": "https://www.aitelecom.com/favicon.ico",
        "max_articles": 5
    }
])

# Sources vérifiées en IA et Cybersécurité
RSS_FEEDS.extend([
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "logo": "https://www.technologyreview.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Nature Machine Intelligence",
        "url": "https://www.nature.com/nmachintell.rss",
        "logo": "https://www.nature.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Science AI",
        "url": "https://www.science.org/rss/news_current.xml",
        "logo": "https://www.science.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "IEEE Spectrum AI",
        "url": "https://spectrum.ieee.org/rss/artificial-intelligence/fulltext",
        "logo": "https://spectrum.ieee.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ACM TechNews",
        "url": "https://technews.acm.org/feed/",
        "logo": "https://technews.acm.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "logo": "https://venturebeat.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ZDNet AI",
        "url": "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "logo": "https://www.zdnet.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/tag/artificial-intelligence/feed/",
        "logo": "https://techcrunch.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/tag/artificial-intelligence/feed/",
        "logo": "https://www.wired.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "logo": "https://www.theverge.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Ars Technica Security",
        "url": "https://arstechnica.com/tag/security/feed/",
        "logo": "https://arstechnica.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "The Register Security",
        "url": "https://www.theregister.com/security/headlines.atom",
        "logo": "https://www.theregister.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CSO Online",
        "url": "https://www.csoonline.com/index.rss",
        "logo": "https://www.csoonline.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Network World Security",
        "url": "https://www.networkworld.com/category/security/index.rss",
        "logo": "https://www.networkworld.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "InfoWorld Security",
        "url": "https://www.infoworld.com/category/security/index.rss",
        "logo": "https://www.infoworld.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Business",
        "url": "https://aibusiness.com/feed/",
        "logo": "https://aibusiness.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Trends",
        "url": "https://www.aitrends.com/feed/",
        "logo": "https://www.aitrends.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "logo": "https://www.artificialintelligence-news.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Weekly",
        "url": "https://aiweekly.co/feed/",
        "logo": "https://aiweekly.co/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Synced",
        "url": "https://syncedreview.com/feed/",
        "logo": "https://syncedreview.com/favicon.ico",
        "max_articles": 5
    }
])

# Sources supplémentaires en français pour la cybersécurité
RSS_FEEDS.extend([
    {
        "name": "LeMagIT",
        "url": "https://www.lemagit.fr/rss/security/",
        "logo": "https://www.lemagit.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ITespresso",
        "url": "https://www.itespresso.fr/category/securite/feed/",
        "logo": "https://www.itespresso.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Le Monde Informatique",
        "url": "https://www.lemondeinformatique.fr/rss/securite.xml",
        "logo": "https://www.lemondeinformatique.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Numerama",
        "url": "https://www.numerama.com/categorie/securite/feed/",
        "logo": "https://www.numerama.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Next INpact",
        "url": "https://www.nextinpact.com/rss/securite.xml",
        "logo": "https://www.nextinpact.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "01net",
        "url": "https://www.01net.com/actualites/securite/feed/",
        "logo": "https://www.01net.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ZDNet France",
        "url": "https://www.zdnet.fr/feeds/rss/actualites/securite/",
        "logo": "https://www.zdnet.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Le Journal du Net",
        "url": "https://www.journaldunet.com/rss/securite.xml",
        "logo": "https://www.journaldunet.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Sécurité Informatique",
        "url": "https://www.securite-informatique.gouv.fr/feed/",
        "logo": "https://www.securite-informatique.gouv.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Clubic",
        "url": "https://www.clubic.com/rss/securite.xml",
        "logo": "https://www.clubic.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "L'Informaticien",
        "url": "https://www.linformaticien.com/rss/securite.xml",
        "logo": "https://www.linformaticien.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "IT Pro",
        "url": "https://www.itpro.fr/rss/securite.xml",
        "logo": "https://www.itpro.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Le Monde du PC",
        "url": "https://www.lemondedupc.com/rss/securite.xml",
        "logo": "https://www.lemondedupc.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "PC World",
        "url": "https://www.pcworld.fr/rss/securite.xml",
        "logo": "https://www.pcworld.fr/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CNIL",
        "url": "https://www.cnil.fr/fr/rss/actualites",
        "logo": "https://www.cnil.fr/favicon.ico",
        "max_articles": 5
    }
])

# Sources professionnelles supplémentaires en cybersécurité
RSS_FEEDS.extend([
    {
        "name": "SANS Security Awareness",
        "url": "https://www.sans.org/security-awareness-training/blog/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Penetration Testing",
        "url": "https://www.sans.org/blog/penetration-testing/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "FireEye Threat Research",
        "url": "https://www.trellix.com/en-us/about/newsroom/feeds/threat-research/",
        "logo": "https://www.trellix.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "CrowdStrike Blog",
        "url": "https://www.crowdstrike.com/blog/feed/",
        "logo": "https://www.crowdstrike.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Palo Alto Networks Blog",
        "url": "https://www.paloaltonetworks.com/blog/feed",
        "logo": "https://www.paloaltonetworks.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Fortinet Blog",
        "url": "https://www.fortinet.com/blog/feed",
        "logo": "https://www.fortinet.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Trend Micro Research",
        "url": "https://www.trendmicro.com/en_us/research/feed.html",
        "logo": "https://www.trendmicro.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Kaspersky Daily",
        "url": "https://www.kaspersky.com/blog/feed/",
        "logo": "https://www.kaspersky.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Symantec Blog",
        "url": "https://symantec-enterprise-blogs.security.com/blogs/feed",
        "logo": "https://symantec-enterprise-blogs.security.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "McAfee Blog",
        "url": "https://www.mcafee.com/blogs/feed/",
        "logo": "https://www.mcafee.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Cisco Talos",
        "url": "https://blog.talosintelligence.com/feeds/posts/default",
        "logo": "https://blog.talosintelligence.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Microsoft Security Blog",
        "url": "https://api.msrc.microsoft.com/update-guide/rss",
        "logo": "https://www.microsoft.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Google Security Blog",
        "url": "https://security.googleblog.com/feeds/posts/default",
        "logo": "https://security.googleblog.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AWS Security Blog",
        "url": "https://aws.amazon.com/blogs/security/feed/",
        "logo": "https://aws.amazon.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Cloudflare Blog",
        "url": "https://blog.cloudflare.com/rss/",
        "logo": "https://blog.cloudflare.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Akamai Security Blog",
        "url": "https://www.akamai.com/blog/security/feed",
        "logo": "https://www.akamai.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Rapid7 Blog",
        "url": "https://www.rapid7.com/blog/feed/",
        "logo": "https://www.rapid7.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Tenable Blog",
        "url": "https://www.tenable.com/blog/feed",
        "logo": "https://www.tenable.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Qualys Blog",
        "url": "https://blog.qualys.com/feed",
        "logo": "https://blog.qualys.com/favicon.ico",
        "max_articles": 5
    }
])

# Sources spécialisées supplémentaires en cybersécurité
RSS_FEEDS.extend([
    {
        "name": "CERT-EU",
        "url": "https://cert.europa.eu/static/SecurityAdvisories/feed.xml",
        "logo": "https://cert.europa.eu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "US-CERT",
        "url": "https://www.cisa.gov/uscert/feeds/current-threats.xml",
        "logo": "https://www.cisa.gov/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "ENISA",
        "url": "https://www.enisa.europa.eu/feeds/news/feed",
        "logo": "https://www.enisa.europa.eu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "NIST Cybersecurity",
        "url": "https://www.nist.gov/cyberframework/feed",
        "logo": "https://www.nist.gov/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "OWASP Blog",
        "url": "https://owasp.org/blog/feed/",
        "logo": "https://owasp.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "PortSwigger Web Security",
        "url": "https://portswigger.net/blog/feed",
        "logo": "https://portswigger.net/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "HackerOne Blog",
        "url": "https://www.hackerone.com/blog/feed",
        "logo": "https://www.hackerone.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Bugcrowd Blog",
        "url": "https://www.bugcrowd.com/blog/feed/",
        "logo": "https://www.bugcrowd.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Synack Blog",
        "url": "https://www.synack.com/blog/feed/",
        "logo": "https://www.synack.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Immunity Blog",
        "url": "https://blog.immunityinc.com/feed/",
        "logo": "https://blog.immunityinc.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Offensive Security Blog",
        "url": "https://www.offensive-security.com/blog/feed/",
        "logo": "https://www.offensive-security.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Black Hat Blog",
        "url": "https://www.blackhat.com/blog/feed/",
        "logo": "https://www.blackhat.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "DEF CON Blog",
        "url": "https://defcon.org/blog/feed/",
        "logo": "https://defcon.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "RSA Conference Blog",
        "url": "https://www.rsaconference.com/blog/feed",
        "logo": "https://www.rsaconference.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Infosec Institute",
        "url": "https://resources.infosecinstitute.com/feed/",
        "logo": "https://resources.infosecinstitute.com/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Digital Forensics",
        "url": "https://www.sans.org/blog/digital-forensics/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Malware Analysis",
        "url": "https://www.sans.org/blog/malware-analysis/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Incident Response",
        "url": "https://www.sans.org/blog/incident-response/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "SANS Cloud Security",
        "url": "https://www.sans.org/blog/cloud-security/feed/",
        "logo": "https://www.sans.org/favicon.ico",
        "max_articles": 5
    }
])

# Sources spécialisées IA et Cybersécurité
RSS_FEEDS.extend([
    {
        "name": "AI Security Initiative",
        "url": "https://www.aisi.org/feed/",
        "logo": "https://www.aisi.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "MIT AI Security",
        "url": "https://www.mit.edu/security/feed/",
        "logo": "https://www.mit.edu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "Stanford AI Security",
        "url": "https://ai.stanford.edu/blog/feed/",
        "logo": "https://ai.stanford.edu/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Alliance",
        "url": "https://www.aisecurityalliance.org/feed/",
        "logo": "https://www.aisecurityalliance.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Forum",
        "url": "https://www.aisecurityforum.org/feed/",
        "logo": "https://www.aisecurityforum.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Institute",
        "url": "https://www.aisi.org/feed/",
        "logo": "https://www.aisi.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Lab",
        "url": "https://www.aisl.org/feed/",
        "logo": "https://www.aisl.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Network",
        "url": "https://www.aisn.org/feed/",
        "logo": "https://www.aisn.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Center",
        "url": "https://www.aisc.org/feed/",
        "logo": "https://www.aisc.org/favicon.ico",
        "max_articles": 5
    },
    {
        "name": "AI Security Foundation",
        "url": "https://www.aisf.org/feed/",
        "logo": "https://www.aisf.org/favicon.ico",
        "max_articles": 5
    }
])

def clean_html(html_text):
    """
    Nettoie le texte HTML en supprimant les balises.
    
    Args:
        html_text (str): Texte HTML à nettoyer
        
    Returns:
        str: Texte nettoyé
    """
    if not html_text:
        return ""
    
    # Supprimer les balises CDATA si présentes
    html_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_text, flags=re.DOTALL)
    
    # Supprimer les balises HTML
    html_text = re.sub(r'<[^>]+>', ' ', html_text)
    
    # Remplacer les entités HTML
    html_text = unescape(html_text)
    
    # Supprimer les espaces multiples
    html_text = re.sub(r'\s+', ' ', html_text).strip()
    
    # Limiter la longueur du texte (environ 300 caractères)
    if len(html_text) > 300:
        html_text = html_text[:297] + "..."
    
    return html_text

def get_cybersecurity_news():
    """
    Récupère les dernières actualités en cybersécurité à partir des flux RSS configurés.
    
    Returns:
        list: Liste des articles formatés avec leurs informations
    """
    print("Récupération des actualités en cybersécurité depuis les flux RSS...")
    
    # Date limite pour les articles (7 derniers jours)
    cutoff_date = datetime.now() - timedelta(days=7)
    all_articles = []
    
    for feed_source in RSS_FEEDS:
        try:
            print(f"Analyse du flux RSS de {feed_source['name']}...")
            feed = feedparser.parse(feed_source['url'])
            
            # Vérifier si le flux a été correctement analysé
            if not feed.entries:
                print(f"Aucun article trouvé dans le flux de {feed_source['name']}")
                continue
            
            # Traiter les articles
            count = 0
            for entry in feed.entries:
                if count >= feed_source['max_articles']:
                    break
                
                # Extraire la date de publication
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                elif hasattr(entry, 'pubDate'):
                    try:
                        # Essayer de parser la date au format string
                        pub_date = datetime.strptime(entry.pubDate, "%a, %d %b %Y %H:%M:%S %z")
                    except:
                        pub_date = datetime.now()
                else:
                    pub_date = datetime.now()  # Utiliser la date actuelle si aucune date n'est disponible
                
                # Ignorer les articles trop anciens
                if pub_date < cutoff_date:
                    continue
                
                # Extraire le contenu de l'article
                description = ""
                if hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'summary'):
                    description = entry.summary
                elif hasattr(entry, 'content'):
                    description = entry.content[0].value
                
                # Nettoyer la description (supprimer les balises HTML)
                description = clean_html(description)
                
                # Extraire le titre
                title = entry.title if hasattr(entry, 'title') else "Sans titre"
                
                # Extraire le lien
                link = entry.link if hasattr(entry, 'link') else ""
                
                # Créer l'objet article
                article = {
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': feed_source['name'],
                    'logo': feed_source['logo'],
                    'pub_date': pub_date.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                all_articles.append(article)
                count += 1
            
            print(f"Récupéré {count} articles de {feed_source['name']}")
            
        except Exception as e:
            print(f"Erreur lors de l'analyse du flux RSS de {feed_source['name']}: {str(e)}")
    
    # Trier les articles par date de publication (du plus récent au plus ancien)
    all_articles.sort(key=lambda x: datetime.strptime(x['pub_date'], "%Y-%m-%d %H:%M:%S"), reverse=True)
    
    print(f"Nombre total d'articles récupérés: {len(all_articles)}")
    return all_articles

def format_email_content(articles):
    """
    Formate les articles pour l'envoi par email en HTML.
    
    Args:
        articles (list): Liste des articles à formater
        
    Returns:
        str: Contenu HTML formaté pour l'email
    """
    if not articles:
        return "<p>Aucune actualité en cybersécurité trouvée cette semaine.</p>"
    
    # Regrouper les articles par source
    articles_by_source = {}
    for article in articles:
        source = article.get('source', 'Autre')
        if source not in articles_by_source:
            articles_by_source[source] = []
        articles_by_source[source].append(article)
    
    # Créer le contenu HTML
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #3498db; margin-top: 20px; }}
            .article {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
            .article-title {{ font-weight: bold; font-size: 18px; margin-bottom: 10px; }}
            .article-source {{ display: flex; align-items: center; margin-bottom: 10px; }}
            .source-logo {{ width: 16px; height: 16px; margin-right: 5px; }}
            .source-name {{ font-weight: bold; color: #7f8c8d; }}
            .article-date {{ color: #95a5a6; font-size: 14px; margin-bottom: 10px; }}
            .article-description {{ margin-bottom: 10px; }}
            .article-link {{ color: #3498db; text-decoration: none; }}
            .article-link:hover {{ text-decoration: underline; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; }}
        </style>
    </head>
    <body>
        <h1>Actualités en Cybersécurité - {datetime.now().strftime("%d/%m/%Y")}</h1>
        <p>Voici les dernières actualités en cybersécurité de cette semaine :</p>
    """
    
    # Ajouter les articles par source
    for source, source_articles in articles_by_source.items():
        html += f"<h2>Source : {source}</h2>"
        
        for article in source_articles:
            pub_date = article.get('pub_date', '')
            try:
                # Convertir la date au format plus lisible
                date_obj = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
                pub_date = date_obj.strftime("%d/%m/%Y à %H:%M")
            except:
                pass
            
            html += f"""
            <div class="article">
                <div class="article-title">{article.get('title', '')}</div>
                <div class="article-source">
                    <img src="{article.get('logo', '')}" class="source-logo" alt="{source}" onerror="this.style.display='none'"/>
                    <span class="source-name">{source}</span>
                </div>
                <div class="article-date">Publié le {pub_date}</div>
                <div class="article-description">{article.get('description', '')}</div>
                <a href="{article.get('link', '')}" class="article-link">Lire l'article complet</a>
            </div>
            """
    
    # Ajouter le pied de page
    html += f"""
        <div class="footer">
            <p>Cet email a été généré automatiquement le {datetime.now().strftime("%d/%m/%Y à %H:%M")}.</p>
            <p>Pour vous désabonner, répondez à cet email avec "STOP" dans l'objet.</p>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email(recipient, subject, html_content):
    try:
        # Configuration de l'email
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = recipient
        
        # Ajouter le contenu HTML
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Connexion au serveur SMTP avec debug
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context) as server:
            print(f"Connexion au serveur SMTP: {SMTP_SERVER}")
            print(f"Tentative de connexion avec: {SENDER_EMAIL}")
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            print("Connexion réussie!")
            server.sendmail(SENDER_EMAIL, recipient, message.as_string())
            print(f"Email envoyé avec succès à {recipient}")
        return True
    except Exception as e:
        print(f"Erreur détaillée lors de l'envoi de l'email: {str(e)}")
        return False

def test_smtp_connection():
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context) as server:
            print("Test de connexion SMTP...")
            print(f"Serveur: {SMTP_SERVER}")
            print(f"Port: {465}")
            print(f"Email: {SENDER_EMAIL}")
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            print("✓ Test de connexion SMTP réussi!")
            return True
    except Exception as e:
        print(f"✗ Erreur de connexion SMTP: {str(e)}")
        return False

def send_test_email():
    """
    Envoie un email de test pour vérifier la configuration SMTP.
    """
    subject = f"{EMAIL_SUBJECT_PREFIX}Test Email"
    body = "Ceci est un test d'envoi d'email via Python."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            print("Email de test envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de test : {e}")

def main():
    print("Démarrage du script...")
    
    # Test de la connexion SMTP
    if not test_smtp_connection():
        print("Impossible de se connecter au serveur SMTP. Arrêt du script.")
        sys.exit(1)
    
    # Envoi d'un email de test
    send_test_email()
    
    # Récupérer les articles
    articles = get_cybersecurity_news()
    print(f"Nombre d'articles récupérés: {len(articles)}")
    
    # Formater le contenu de l'email
    email_content = format_email_content(articles)
    
    # Envoyer l'email
    subject = f"{EMAIL_SUBJECT_PREFIX}{datetime.now().strftime('%d/%m/%Y')}"
    success = send_email(RECIPIENT_EMAIL, subject, email_content)
    
    if success:
        print("Email envoyé avec succès!")
    else:
        print("L'email n'a pas été envoyé, mais un aperçu a été sauvegardé.")
    
    # Sauvegarder les articles pour référence
    with open('latest_articles.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print("Script terminé.")

if __name__ == "__main__":
    main()
