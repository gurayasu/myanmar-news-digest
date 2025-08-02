import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date, timezone
from dateutil.parser import parse as parse_date
import re
# Chat GPT
# from openai import OpenAI, OpenAIError
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import sys
from email import policy  # ← 追加
from email.header import Header  # ← 追加必要
from email.message import EmailMessage
from email.policy import SMTPUTF8
from email.utils import formataddr
import unicodedata
from google import genai
from google.api_core.exceptions import GoogleAPICallError
from collections import defaultdict

# Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Chat GPT
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ミャンマー標準時 (UTC+6:30)
MMT = timezone(timedelta(hours=6, minutes=30))

def get_yesterday_date_mmt():
    now_mmt = datetime.now(MMT)
    yesterday_mmt = now_mmt - timedelta(days=1)
    return yesterday_mmt.date()

def clean_html_content(html: str) -> str:
    html = html.replace("\xa0", " ").replace("&nbsp;", " ")
    # 制御文字（カテゴリC）を除外、可視Unicodeはそのまま
    return ''.join(c for c in html if unicodedata.category(c)[0] != 'C')

def clean_text(text: str) -> str:
    import unicodedata
    if not text:
        return ""
    return ''.join(
        c if (unicodedata.category(c)[0] != 'C' and c != '\xa0') else ' '
        for c in text
    )

def get_frontier_articles_for(date_obj):
    base_url = "https://www.frontiermyanmar.net"
    list_url = base_url + "/en/news"
    res = requests.get(list_url, timeout=10)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("div.teaser a")
    article_urls = [base_url + a["href"] for a in links if a.get("href", "").startswith("/")]

    filtered_articles = []
    for url in article_urls:
        try:
            res_article = requests.get(url, timeout=10)
            soup_article = BeautifulSoup(res_article.content, "html.parser")
            time_tag = soup_article.find("time")
            if not time_tag:
                continue
            date_str = time_tag.get("datetime", "")
            if not date_str:
                continue
            article_date = datetime.fromisoformat(date_str).date()
            if article_date == date_obj:
                title = soup_article.find("h1").get_text(strip=True)
                filtered_articles.append({
                    "url": url,
                    "title": title,
                    "date": article_date.isoformat()
                })
        except Exception:
            continue

    return filtered_articles

def get_mizzima_articles_for(date_obj, seen_urls):
    base_url = "https://eng.mizzima.com"
    list_url = base_url
    res = requests.get(list_url, timeout=10)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.find_all("a", href=True)

    date_pattern = re.compile(r"/\d{4}/\d{2}/\d{2}/")
    article_urls = [a["href"] for a in links if date_pattern.search(a["href"])]

    target_date_str = date_obj.strftime("%Y/%m/%d")
    keywords = ["မြန်မာ", "ဗမာ", "အောင်ဆန်းစုကြည်", "မင်းအောင်လှိုင်", "Myanmar", "Burma"]

    filtered_articles = []
    for url in article_urls:
        full_url = url if url.startswith("http") else base_url + url
        if full_url in seen_urls:
            continue  # 重複URL排除
        seen_urls.add(full_url)

        if target_date_str not in full_url:
            continue

        try:
            res_article = requests.get(full_url, timeout=10)
            soup_article = BeautifulSoup(res_article.content, "html.parser")
            title_tag = soup_article.find("h1")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            paragraphs = soup_article.select("div.entry-content p")
            body_text = "\n".join(p.get_text(strip=True) for p in paragraphs)

            if not any(keyword in title or keyword in body_text for keyword in keywords):
                continue

            filtered_articles.append({
                "url": full_url,
                "title": title,
                "date": date_obj.isoformat()
            })

        except Exception:
            continue

    return filtered_articles

def get_vom_articles_for(date_obj):
    base_url = "https://voiceofmyanmarnews.com"
    list_url = base_url + "/?cat=1"
    res = requests.get(list_url, timeout=10)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("h2.entry-title a")
    article_urls = [a["href"] for a in links if a.get("href", "").startswith("https://")]

    filtered_articles = []
    for url in article_urls:
        try:
            res_article = requests.get(url, timeout=10)
            soup_article = BeautifulSoup(res_article.content, "html.parser")
            date_div = soup_article.select_one("time.entry-date")
            if not date_div:
                continue
            date_text = date_div.get_text(strip=True)
            # 例: "July 25, 2025" をパース
            try:
                article_date = datetime.strptime(date_text, "%B %d, %Y").date()
            except ValueError:
                continue
            if article_date == date_obj:
                title = soup_article.find("h1").get_text(strip=True)
                filtered_articles.append({
                    "url": url,
                    "title": title,
                    "date": article_date.isoformat()
                })
        except Exception:
            continue

    return filtered_articles

def get_ludu_articles_for(date_obj):
    base_url = "https://ludunwayoo.com"
    list_url = base_url + "/en/news"
    res = requests.get(list_url, timeout=10)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("h2.entry-title a")
    article_urls = [a["href"] for a in links if a.get("href", "").startswith("http")]

    filtered_articles = []
    for url in article_urls:
        try:
            res_article = requests.get(url, timeout=10)
            soup_article = BeautifulSoup(res_article.content, "html.parser")
            time_tag = soup_article.find("time")
            if not time_tag:
                continue
            date_str = time_tag.get("datetime", "")
            if not date_str:
                continue
            article_date = datetime.fromisoformat(date_str).date()
            if article_date == date_obj:
                title = soup_article.find("h1").get_text(strip=True)
                filtered_articles.append({
                    "url": url,
                    "title": title,
                    "date": article_date.isoformat()
                })
        except Exception:
            continue

    return filtered_articles

# BCCはRSSあるのでそれ使う
def get_bbc_burmese_articles_for(target_date_mmt):
    rss_url = "https://feeds.bbci.co.uk/burmese/rss.xml"
    res = requests.get(rss_url, timeout=10)
    soup = BeautifulSoup(res.content, "xml")

    keywords = ["မြန်မာ", "ဗမာ", "အောင်ဆန်းစုကြည်", "မင်းအောင်လှိုင်", "Myanmar", "Burma"]

    articles = []
    for item in soup.find_all("item"):
        pub_date_tag = item.find("pubDate")
        if not pub_date_tag:
            continue

        try:
            pub_date = parse_date(pub_date_tag.text)  # RSSはUTC基準
            pub_date_mmt = pub_date.astimezone(MMT).date()  # ← MMTに変換して日付抽出
        except Exception as e:
            print(f"❌ pubDate parse error: {e}")
            continue

        if pub_date_mmt != target_date_mmt:
            continue  # 昨日(MMT基準)の日付と一致しない記事はスキップ

        title = item.find("title").text.strip()
        link = item.find("link").text.strip()

        try:
            article_res = requests.get(link, timeout=10)
            article_soup = BeautifulSoup(article_res.content, "html.parser")
            paragraphs = article_soup.find_all("p")
            body_text = "\n".join(p.get_text(strip=True) for p in paragraphs)

            if not any(keyword in title or keyword in body_text for keyword in keywords):
                continue  # キーワードが含まれていなければ除外

            print(f"✅ 抽出記事: {title} ({link})")  # ログ出力で抽出記事確認
            articles.append({
                "title": title,
                "url": link,
                "date": pub_date_mmt.isoformat()
            })

        except Exception as e:
            print(f"❌ 記事取得エラー: {e}")
            continue

    return articles

# def get_bbc_burmese_articles_for(date_obj):
#     base_url = "https://www.bbc.com"
#     list_url = base_url + "/burmese"
#     res = requests.get(list_url, timeout=10)
#     soup = BeautifulSoup(res.content, "html.parser")
#     links = soup.select("a[href^='/burmese/']")
#     article_urls = [
#         base_url + a["href"]
#         for a in links
#         if any(part in a["href"] for part in ["articles", "media"])
#     ]

#     seen = set()
#     filtered_articles = []
#     for url in article_urls:
#         if url in seen:
#             continue
#         seen.add(url)
#         try:
#             res_article = requests.get(url, timeout=10)
#             soup_article = BeautifulSoup(res_article.content, "html.parser")
#             time_tag = soup_article.find("time")
#             if not time_tag:
#                 continue
#             date_str = time_tag.get("datetime", "")
#             if not date_str:
#                 continue
#             article_date = datetime.fromisoformat(date_str).date()
#             if article_date == date_obj:
#                 title = soup_article.find("h1").get_text(strip=True)
#                 filtered_articles.append({
#                     "url": url,
#                     "title": title,
#                     "date": article_date.isoformat()
#                 })
#         except Exception:
#             continue

#     return filtered_articles

def get_yktnews_articles_for(date_obj, seen_urls):
    base_url = "https://yktnews.com"
    list_url = base_url + "/category/news/"
    res = requests.get(list_url, timeout=10)
    soup = BeautifulSoup(res.content, "html.parser")
    links = soup.select("h3.entry-title a")
    article_urls = [a["href"] for a in links if a.get("href", "").startswith("http")]

    target_month_str = date_obj.strftime("%Y/%m")
    keywords = ["မြန်မာ", "ဗမာ", "အောင်ဆန်းစုကြည်", "မင်းအောင်လှိုင်", "Myanmar", "Burma"]

    filtered_articles = []
    for url in article_urls:
        match = re.search(r"https?://[^/]+/(\d{4}/\d{2})/", url)
        if not match:
            continue
        url_month_str = match.group(1)
        if url_month_str != target_month_str:
            continue

        if url in seen_urls:
            continue  # 重複URLスキップ
        seen_urls.add(url)

        try:
            res_article = requests.get(url, timeout=10)
            soup_article = BeautifulSoup(res_article.content, "html.parser")
            time_tag = soup_article.find("time", class_="entry-date updated td-module-date")
            if not time_tag:
                continue
            date_str = time_tag.get("datetime", "")
            if not date_str:
                continue
            article_date = datetime.fromisoformat(date_str).date()
            if article_date != date_obj:
                continue

            title_tag = soup_article.find("h1")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            entry_content_div = soup_article.find("div", class_="entry-content")
            if not entry_content_div:
                continue

            for unwanted in entry_content_div.select(".site-footer-top, .related-posts, .ads-section"):
                unwanted.decompose()

            body_text = entry_content_div.get_text(separator="\n", strip=True)

            if not any(keyword in title or keyword in body_text for keyword in keywords):
                continue

            filtered_articles.append({
                "url": url,
                "title": title,
                "date": date_obj.isoformat()
            })

        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue

    return filtered_articles

# タイトル翻訳のみ、GeminiAPIを使う場合
def translate_text_only(text: str) -> str:
    if not text or not text.strip():
        return "（翻訳に失敗しました）"

    prompt = (
        "以下はbbc burmeseの記事のタイトルです。日本語に訳してください。\n\n"
        "レスポンスではタイトルの日本語訳のみを返してください、それ以外の文言は不要です。\n\n"
        "###\n\n"
        f"{text.strip()}\n\n"
        "###"
    )

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return resp.text.strip()
    except Exception as e:
        print(f"🛑 タイトル翻訳エラー: {e}")
        return "（翻訳に失敗しました）"

# 本文翻訳＆要約、GeminiAPIを使う場合
def translate_and_summarize(text: str) -> str:
    print(text)
    
    if not text or not text.strip():
        print("⚠️ 入力テキストが空です")
        return "（翻訳・要約に失敗しました）"

    prompt = (
        "以下の記事の本文について重要なポイントをまとめ具体的に要約してください。自然な日本語に訳してください。\n\n"
        "個別記事の本文の要約のみとしてください。メディアの説明やページ全体の解説は不要です。\n\n"
        "レスポンスでは要約のみを返してください、それ以外の文言は不要です。\n\n"
        "以下、出力の条件です\n\n"
        "- 改行や箇条書きを適切に使って見やすく整理してください。\n\n"
        "- 見出しや箇条書きにはマークダウン記号（#, *, - など）は使わず、単純なテキストとして出力してください。\n\n"
        "- 全体をHTMLで送るわけではないので、特殊記号は使わないでください。\n\n"
        "- 箇条書きは「・」を使ってください。\n\n"
        "- 文字数は最大500文字としてください。\n\n"
        "###\n\n"
        f"{text[:2000]}\n\n"
        "###"
    )

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        print(resp.text.strip())
        
        return resp.text.strip()

    except Exception as e:
        print(f"🛑 Gemini API エラー: {e}")
        return "（翻訳・要約に失敗しました）"


# Chat GPT使う場合
# def translate_and_summarize(text: str) -> str:
#     if not text or not text.strip():
#         print("⚠️ 入力テキストが空です。")
#         return "（翻訳・要約に失敗しました）"

#     prompt = (
#         "以下の記事の内容について重要なポイントをまとめ、具体的に要約してください。" 
#         "文字数は800文字までとします。自然な日本語に訳してください。\n\n"
#         f"{text[:2000]}"  # 入力長を適切に制限（APIの入力トークン制限を超えないように）
#     )

#     try:
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}]
#         )
#         return response.choices[0].message.content.strip()

#     except OpenAIError as api_err:
#         # OpenAI全体の例外を網羅
#         print(f"🛑 OpenAI API エラー: {api_err}")
#         return "（翻訳・要約に失敗しました）"
#     except Exception as e:
#         # その他の予期しない例外
#         print(f"予期せぬエラー: {e}")
#         return "（翻訳・要約に失敗しました）"

def process_and_summarize_articles(articles, source_name, seen_urls=None):    
    if seen_urls is None:
        seen_urls = set()

    results = []
    for art in articles:
        if art['url'] in seen_urls:
            continue  # 重複URLはスキップ
        seen_urls.add(art['url'])

        print(art['url'])

        try:
            res = requests.get(art['url'], timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs)

            translated_title = translate_text_only(art["title"])  # タイトル翻訳
            summary = translate_and_summarize(text)  # 本文要約・翻訳
            
            # 改行を <br> に置換
            summary_html = summary.replace("\n", "<br>")
            # summary_html = markdown_to_html(summary)  # HTML整形

            results.append({
                "source": source_name,
                "url": art["url"],
                "title": translated_title,
                "summary": summary_html,
            })
        except Exception as e:
            print(f"❌ Error processing article: {art['url']}")
            print(f"Exception: {e}")
            continue
    return results

def send_email_digest(summaries):
    sender_email = "yasu.23721740311@gmail.com"
    sender_pass = "sfqy saao bhhj dlwu"
    # sender_pass = "mwdr ewpr ncfk vuuw"
    recipient_emails = ["yasu.23721740311@gmail.com"]
    # sender_email = os.getenv("EMAIL_SENDER")
    # sender_pass = os.getenv("GMAIL_APP_PASSWORD")
    # recipient_emails = os.getenv("EMAIL_RECIPIENTS", "").split(",")

    # ✅ 昨日の日付を取得してフォーマット
    digest_date = get_yesterday_date_mmt()
    date_str = digest_date.strftime("%Y年%-m月%-d日") + "分"

    # メディアごとにまとめる
    media_grouped = defaultdict(list)
    for item in summaries:
        media_grouped[item["source"]].append(item)

    # メールタイトル
    subject = "ミャンマー関連ニュース【" + date_str + "】"

    # メール本文のHTML生成
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #ffffff; color: #333333;">
    """

    for media, articles in media_grouped.items():
        html_content += f"<h3 style='color: #2a2a2a; margin-top: 30px;'>{media} からのニュース</h3>"

        for item in articles:
            title_jp = "タイトル: " + item["title"]
            url = item["url"]

            summary_html = item["summary"]  # すでにHTML整形済みをそのまま使う
            html_content += (
                f"<div style='margin-bottom: 20px;'>"
                f"<h4 style='margin-bottom: 5px;'>{title_jp}</h4>"
                f"<p><a href='{url}' style='color: #1a0dab;'>本文を読む</a></p>"
                f"<div style='background-color: #f9f9f9; padding: 10px; border-radius: 8px;'>"
                f"{summary_html}"
                f"</div></div><hr style='border-top: 1px solid #cccccc;'>"
            )

    html_content += "</body></html>"
    html_content = clean_html_content(html_content)

    from_display_name = "Myanmar News Digest"

    msg = EmailMessage(policy=SMTPUTF8)
    msg["Subject"] = subject
    msg["From"] = formataddr((from_display_name, sender_email))
    msg["To"] = ", ".join(recipient_emails)
    msg.set_content("HTMLメールを開ける環境でご確認ください。", charset="utf-8")
    msg.add_alternative(html_content, subtype="html", charset="utf-8")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.send_message(msg)
            print("✅ メール送信完了")
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    yesterday_mmt = get_yesterday_date_mmt()
    seen_urls = set()  # ← 追加: 共通のURL重複排除セット
    
    # articles = get_frontier_articles_for(yesterday)
    # for art in articles:
    #     print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    print("=== Mizzima ===")
    articles3 = get_mizzima_articles_for(yesterday_mmt, seen_urls)
    for art in articles3:
        print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    # print("=== Voice of Myanmar ===")
    # articles4 = get_vom_articles_for(yesterday)
    # for art in articles4:
    #     print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    # print("=== Ludu Wayoo ===")
    # articles5 = get_ludu_articles_for(yesterday)
    # for art in articles5:
    #     print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    print("=== BBC Burmese ===")
    articles6 = get_bbc_burmese_articles_for(yesterday_mmt)
    for art in articles6:
        print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    print("=== YKT News ===")
    articles7 = get_yktnews_articles_for(yesterday_mmt, seen_urls)
    for art in articles7:
        print(f"{art['date']} - {art['title']}\n{art['url']}\n")

    all_summaries = []
    # all_summaries += process_and_summarize_articles(get_frontier_articles_for(yesterday), "Frontier Myanmar")
    all_summaries += process_and_summarize_articles(articles3, "Mizzima", seen_urls)
    # all_summaries += process_and_summarize_articles(get_vom_articles_for(yesterday), "Voice of Myanmar")
    # all_summaries += process_and_summarize_articles(get_ludu_articles_for(yesterday), "Ludu Wayoo")
    all_summaries += process_and_summarize_articles(articles6, "BBC Burmese", seen_urls)
    all_summaries += process_and_summarize_articles(articles7, "YKT News", seen_urls)

    send_email_digest(all_summaries)
