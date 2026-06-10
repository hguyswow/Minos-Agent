"""
morning_brief_tentacle.py (v3 -   )
  IT/      RSS   .
       .
"""
import os
import sys
import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

#  
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
HISTORY_FILE = os.path.join(DATA_DIR, "news_history.json") #    

# 
# 1.    (  IT/  )
# 
RSS_FEEDS = [
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko", # IT
    "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=ko&gl=KR&ceid=KR:ko",    # 
]

def get_latest_news(limit=5):
    all_items = []
    
    #    
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []

    for url in RSS_FEEDS:
        try:
            res = requests.get(url, timeout=10)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pub_date = item.find('pubDate').text
                
                #  ( ) 
                if title in history:
                    continue
                
                all_items.append({
                    "title": title,
                    "link": link,
                    "date": pub_date
                })
        except Exception as e:
            print(f"[ERROR] RSS   ({url}): {e}")

    #    (RSS    )
    #       (: " - ")
    unique_news = []
    for news in all_items:
        clean_title = news['title'].split(' - ')[0] #   
        if any(clean_title in u['title'] for u in unique_news):
            continue
        unique_news.append(news)
        if len(unique_news) >= limit:
            break
            
    #   ( 100 )
    new_history = [n['title'] for n in unique_news] + history
    new_history = new_history[:100]
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
        
    return unique_news

# 
# 2.  
# 
now = datetime.now()

#      ( )
COOLDOWN_FILE = os.path.join(DATA_DIR, "morning_brief_cooldown.txt")
if os.path.exists(COOLDOWN_FILE):
    with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
        last_date = f.read().strip()
    if last_date == now.strftime("%Y-%m-%d"):
        print("[INFO]    .")
        sys.exit(0) #        

#  
news_list = get_latest_news(5)

if not news_list:
    print("[INFO]   .")
    sys.exit(0)

#  
msg_parts = ["[SPARKLES] ** IT/  ** [SPARKLES]\n"]
for i, news in enumerate(news_list, 1):
    #    
    title = news['title']
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    msg_parts.append(f"{i}. **{title}**")

msg_parts.append("\n,        ! [SMILE]")
full_message = "\n".join(msg_parts)

#  
try:
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
    signals = {}
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                signals = json.load(f)
        except:
            signals = {}
            
    signals["morning_brief_tentacle.py"] = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "message": full_message
    }
    
    with open(SIGNAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=4, ensure_ascii=False)
        
    #  
    with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(now.strftime("%Y-%m-%d"))
        
    print(f"[SUCCESS]    :\n{full_message}")
except Exception as e:
    print(f"[ERROR]    : {e}")
