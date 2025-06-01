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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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

# Configuration des timeouts et retries pour les requêtes
TIMEOUT = 5  # Timeout réduit à 5 secondes
MAX_RETRIES = 2  # Nombre maximum de tentatives réduit à 2

# Configuration de la session requests avec retry
session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Headers pour éviter les blocages
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# Sources RSS de cybersécurité
RSS_FEEDS = [
    # Cybersécurité internationale
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "logo": "https://thehackernews.com/favicon.ico", "max_articles": 10},
    {"name": "WeLiveSecurity", "url": "https://www.welivesecurity.com/en/rss/feed/", "logo": "https://www.welivesecurity.com/wp-content/themes/wls-new/images/favicon.ico", "max_articles": 10},
    {"name": "Security Magazine", "url": "https://www.securitymagazine.com/rss/topic/2236-cybersecurity", "logo": "https://www.securitymagazine.com/favicon.ico", "max_articles": 10},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "logo": "https://krebsonsecurity.com/favicon.ico", "max_articles": 10},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "logo": "https://www.darkreading.com/favicon.ico", "max_articles": 10},
    {"name": "SANS Internet Storm Center", "url": "https://isc.sans.edu/rssfeed.xml", "logo": "https://isc.sans.edu/favicon.ico", "max_articles": 10},
    {"name": "Infosecurity Magazine", "url": "https://www.infosecurity-magazine.com/rss/news/", "logo": "https://www.infosecurity-magazine.com/favicon.ico", "max_articles": 10},
    {"name": "CERT-FR", "url": "https://www.cert.ssi.gouv.fr/feed/", "logo": "https://www.cert.ssi.gouv.fr/favicon.ico", "max_articles": 10},
    {"name": "Security Affairs", "url": "https://securityaffairs.com/feed", "logo": "https://securityaffairs.com/favicon.ico", "max_articles": 10},
    {"name": "ZDNet Security", "url": "https://www.zdnet.com/topic/security/rss.xml", "logo": "https://www.zdnet.com/favicon.ico", "max_articles": 10},
    {"name": "ZATAZ Magazine", "url": "https://www.zataz.com/feed/", "logo": "https://www.zataz.com/favicon.ico", "max_articles": 10},
    {"name": "Exploit-DB RSS", "url": "https://www.exploit-db.com/rss.xml", "logo": "https://www.exploit-db.com/favicon.ico", "max_articles": 10},
    {"name": "UnderNews", "url": "https://www.undernews.fr/feed", "logo": "https://www.undernews.fr/favicon.ico", "max_articles": 10},
    {"name": "Ars Technica Security", "url": "https://arstechnica.com/tag/security/feed/", "logo": "https://arstechnica.com/favicon.ico", "max_articles": 10},
    {"name": "The Register Security", "url": "https://www.theregister.com/security/headlines.atom", "logo": "https://www.theregister.com/favicon.ico", "max_articles": 10},
    {"name": "Microsoft Security Blog", "url": "https://api.msrc.microsoft.com/update-guide/rss", "logo": "https://www.microsoft.com/favicon.ico", "max_articles": 10},
    {"name": "Google Security Blog", "url": "https://security.googleblog.com/feeds/posts/default", "logo": "https://security.googleblog.com/favicon.ico", "max_articles": 10},
    {"name": "AWS Security Blog", "url": "https://aws.amazon.com/blogs/security/feed/", "logo": "https://aws.amazon.com/favicon.ico", "max_articles": 10},
    {"name": "Cisco Talos Blog", "url": "https://blog.talosintelligence.com/feeds/posts/default", "logo": "https://www.cisco.com/favicon.ico", "max_articles": 10},
    {"name": "Bitdefender Labs", "url": "https://www.bitdefender.com/blog/labs/feed/", "logo": "https://www.bitdefender.com/favicon.ico", "max_articles": 10},
    # Blogs et portails spécialisés
    {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "logo": "https://www.bleepingcomputer.com/favicon.ico", "max_articles": 10},
    {"name": "Malwarebytes Labs", "url": "https://blog.malwarebytes.com/feed/", "logo": "https://blog.malwarebytes.com/favicon.ico", "max_articles": 10},
    {"name": "ESET WeLiveSecurity FR", "url": "https://www.welivesecurity.com/fr/feed/", "logo": "https://www.welivesecurity.com/favicon.ico", "max_articles": 10},
    {"name": "Naked Security by Sophos", "url": "https://nakedsecurity.sophos.com/feed/", "logo": "https://nakedsecurity.sophos.com/favicon.ico", "max_articles": 10},
    {"name": "Kaspersky Daily", "url": "https://www.kaspersky.com/blog/feed/", "logo": "https://www.kaspersky.com/favicon.ico", "max_articles": 10},
    {"name": "Palo Alto Networks Blog FR", "url": "https://www.paloaltonetworks.fr/blog/feed", "logo": "https://www.paloaltonetworks.fr/favicon.ico", "max_articles": 10},
    {"name": "Tenable Blog", "url": "https://fr.tenable.com/blog/feed", "logo": "https://fr.tenable.com/favicon.ico", "max_articles": 10},
    {"name": "Rapid7 Blog", "url": "https://www.rapid7.com/blog/feed/", "logo": "https://www.rapid7.com/favicon.ico", "max_articles": 10},
    {"name": "Qualys Blog", "url": "https://blog.qualys.com/feed", "logo": "https://blog.qualys.com/favicon.ico", "max_articles": 10},
    {"name": "Akamai Blog", "url": "https://blogs.akamai.com/security/index.xml", "logo": "https://www.akamai.com/favicon.ico", "max_articles": 10},
    {"name": "Proofpoint Blog", "url": "https://www.proofpoint.com/us/rss.xml", "logo": "https://www.proofpoint.com/favicon.ico", "max_articles": 10},
    {"name": "CrowdStrike Blog", "url": "https://www.crowdstrike.com/blog/feed/", "logo": "https://www.crowdstrike.com/favicon.ico", "max_articles": 10},
    {"name": "Fortinet Blog EN", "url": "https://www.fortinet.com/blog/threat-research/feed", "logo": "https://www.fortinet.com/favicon.ico", "max_articles": 10},
    {"name": "Check Point Blog EN", "url": "https://blog.checkpoint.com/feed/", "logo": "https://blog.checkpoint.com/favicon.ico", "max_articles": 10},
    {"name": "Symantec Enterprise Blogs", "url": "https://symantec-enterprise-blogs.security.com/blogs/feed", "logo": "https://symantec-enterprise-blogs.security.com/favicon.ico", "max_articles": 10},
    {"name": "Trend Micro Simply Security", "url": "https://www.trendmicro.com/en_us/research/rss.xml", "logo": "https://www.trendmicro.com/favicon.ico", "max_articles": 10},
    {"name": "McAfee Blog FR", "url": "https://www.mcafee.com/blogs/fr/feed/", "logo": "https://www.mcafee.com/favicon.ico", "max_articles": 10},
    {"name": "CERT-EU", "url": "https://cert.europa.eu/rss.xml", "logo": "https://cert.europa.eu/favicon.ico", "max_articles": 10},
    {"name": "ENISA News", "url": "https://www.enisa.europa.eu/news/enisa-news/RSS", "logo": "https://www.enisa.europa.eu/favicon.ico", "max_articles": 10},
    {"name": "US-CERT", "url": "https://www.cisa.gov/uscert/ncas/all.xml", "logo": "https://www.cisa.gov/favicon.ico", "max_articles": 10},
    # IA et Tech
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "logo": "https://venturebeat.com/favicon.ico", "max_articles": 10},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "logo": "https://www.technologyreview.com/favicon.ico", "max_articles": 10},
    {"name": "Science AI", "url": "https://www.science.org/rss/news_current.xml", "logo": "https://www.science.org/favicon.ico", "max_articles": 10},
    {"name": "IEEE Spectrum AI", "url": "https://spectrum.ieee.org/rss/artificial-intelligence/fulltext", "logo": "https://spectrum.ieee.org/favicon.ico", "max_articles": 10},
    {"name": "ZDNet AI", "url": "https://www.zdnet.com/topic/artificial-intelligence/rss.xml", "logo": "https://www.zdnet.com/favicon.ico", "max_articles": 10},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/tag/artificial-intelligence/feed/", "logo": "https://techcrunch.com/favicon.ico", "max_articles": 10},
    {"name": "Synced AI", "url": "https://syncedreview.com/feed/", "logo": "https://syncedreview.com/favicon.ico", "max_articles": 10},
    {"name": "AI Alignment Forum", "url": "https://www.alignmentforum.org/feed.xml", "logo": "https://www.alignmentforum.org/favicon.ico", "max_articles": 10},
    {"name": "Open Data Science", "url": "https://opendatascience.com/feed/", "logo": "https://opendatascience.com/favicon.ico", "max_articles": 10},
    {"name": "Analytics Vidhya", "url": "https://www.analyticsvidhya.com/blog/feed/", "logo": "https://www.analyticsvidhya.com/favicon.ico", "max_articles": 10}
]

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
            
            # Récupération du contenu avec timeout
            response = session.get(feed_source['url'], headers=DEFAULT_HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            
            # Parse du contenu RSS
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                articles = []
                for entry in feed.entries[:feed_source['max_articles']]:
                    try:
                        # Extraire la date de publication
                        pub_date = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            pub_date = datetime(*entry.updated_parsed[:6])
                        elif hasattr(entry, 'pubDate'):
                            try:
                                pub_date = datetime.strptime(entry.pubDate, "%a, %d %b %Y %H:%M:%S %z")
                            except:
                                pub_date = datetime.now()
                        else:
                            pub_date = datetime.now()
                        
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
                        
                        # Nettoyer la description
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
                        
                        articles.append(article)
                    except Exception as e:
                        print(f"Erreur lors du traitement d'un article de {feed_source['name']}: {str(e)}")
                        continue
                
                all_articles.extend(articles)
                print(f"✓ {len(articles)} articles récupérés de {feed_source['name']}")
            else:
                print(f"✗ Aucun article trouvé dans {feed_source['name']}")
                
        except Exception as e:
            print(f"Erreur lors de l'analyse du flux RSS de {feed_source['name']}: {str(e)}")
            continue
    
    # Trier les articles par date de publication
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
