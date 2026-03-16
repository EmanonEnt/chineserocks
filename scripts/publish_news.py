#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks News Publisher - ASCII Version
"""

import os
import json
from datetime import datetime
from notion_client import Client

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def fetch_published_articles():
    """Fetch published articles from Notion"""
    notion = Client(auth=NOTION_TOKEN)
    articles = []

    try:
        print("Fetching from Notion...")

        response = notion.databases.query(
            database_id=NEWS_DB_ID,
            filter={
                "property": "狀態",
                "select": {"equals": "已發佈"}
            },
            sorts=[{
                "property": "發布時間",
                "direction": "descending"
            }]
        )

        print(f"Found {len(response['results'])} articles")

        for page in response['results']:
            try:
                props = page['properties']

                article = {
                    "id": page['id'],
                    "title": extract_title(props),
                    "content": extract_content(props),
                    "category": extract_select(props, '類型'),
                    "tags": extract_multi_select(props, '標籤'),
                    "status": extract_select(props, '狀態'),
                    "source_url": extract_url(props, '來源'),
                    "published_date": extract_date(props, '發布時間'),
                    "is_ai_generated": extract_checkbox(props, 'AI生成'),
                    "featured": extract_checkbox(props, '頭條'),
                    "is_premium": False,
                    "cover_image": extract_url(props, '封面圖') or get_default_image()
                }

                if '會員專享' in article['tags'] or '獨家' in article['tags']:
                    article['is_premium'] = True

                articles.append(article)
                print(f"  OK: {article['title'][:40]}...")

            except Exception as e:
                print(f"  Error: {e}")
                continue

    except Exception as e:
        print(f"Fetch failed: {e}")
        import traceback
        traceback.print_exc()

    return articles

def extract_title(props):
    try:
        title_prop = props.get('標題', {})
        if title_prop.get('title'):
            return title_prop['title'][0]['text']['content']
    except:
        pass
    return "No Title"

def extract_content(props):
    try:
        content_prop = props.get('內容', {})
        if content_prop.get('rich_text'):
            return content_prop['rich_text'][0]['text']['content']
    except:
        pass
    return ""

def extract_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if prop.get('select'):
            return prop['select']['name']
    except:
        pass
    return ""

def extract_multi_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if prop.get('multi_select'):
            return [tag['name'] for tag in prop['multi_select']]
    except:
        pass
    return []

def extract_url(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        return prop.get('url', '')
    except:
        pass
    return ""

def extract_date(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if prop.get('date'):
            return prop['date']['start']
    except:
        pass
    return datetime.now().isoformat()

def extract_checkbox(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        return prop.get('checkbox', False)
    except:
        pass
    return False

def get_default_image():
    return "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

def generate_news_json(articles):
    """Generate news.json"""

    articles.sort(key=lambda x: x.get('published_date', ''), reverse=True)

    hero = articles[:3] if articles else []
    featured = [a for a in articles if a.get('featured') or a.get('is_premium')][:4]
    latest = articles[:12]

    by_category = {
        "全部": articles,
        "獨家": [],
        "現場": [],
        "專題": [],
        "國際": [],
        "新發行": []
    }

    for article in articles:
        cat = article.get('category', '')
        tags = article.get('tags', [])

        if '獨家' in tags or cat == '獨家':
            by_category['獨家'].append(article)
        elif '現場' in tags or cat in ['演出预告', '現場']:
            by_category['現場'].append(article)
        elif '專題' in tags or cat in ['专访', '專題']:
            by_category['專題'].append(article)
        elif '國際' in tags:
            by_category['國際'].append(article)
        elif '新發行' in tags or cat in ['乐评', '新發行']:
            by_category['新發行'].append(article)

    news_data = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(articles),
        "data": {
            "all": articles,
            "hero": hero,
            "featured": featured,
            "latest": latest,
            "by_category": by_category
        }
    }

    return news_data

def save_to_json(news_data):
    """Save to JSON file"""
    os.makedirs('data', exist_ok=True)

    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {news_data['total_count']} articles to data/news.json")

def main():
    print("\n" + "="*70)
    print("ChineseRocks News Publisher")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN not set")
        return

    print("\nFetching published articles...")
    articles = fetch_published_articles()

    if not articles:
        print("No published articles found")
        empty_data = {
            "updated_at": datetime.now().isoformat(),
            "total_count": 0,
            "data": {
                "all": [],
                "hero": [],
                "featured": [],
                "latest": [],
                "by_category": {
                    "全部": [],
                    "獨家": [],
                    "現場": [],
                    "專題": [],
                    "國際": [],
                    "新發行": []
                }
            }
        }
        save_to_json(empty_data)
        return

    print(f"\nFound {len(articles)} published articles")

    print("\nGenerating news.json...")
    news_data = generate_news_json(articles)

    print("\nSaving to file...")
    save_to_json(news_data)

    print("\n" + "="*70)
    print("Publish Stats")
    print("="*70)
    print(f"Total: {news_data['total_count']}")
    print(f"Hero: {len(news_data['data']['hero'])}")
    print(f"Featured: {len(news_data['data']['featured'])}")
    print(f"Latest: {len(news_data['data']['latest'])}")
    print("="*70)
    print("\nDone!")

if __name__ == "__main__":
    main()
