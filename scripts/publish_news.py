#!/usr/bin/env python3
"""
ChineseRocks 新聞發布系統
從Notion獲取已發布文章，生成前端JSON
"""

import os
import json
import re
from datetime import datetime
from notion_client import Client

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def fetch_published_articles():
    """從Notion獲取已發布的文章"""
    if not NOTION_TOKEN:
        print("❌ 錯誤: NOTION_TOKEN 未設置")
        return []

    notion = Client(auth=NOTION_TOKEN)
    articles = []

    try:
        # 新版API調用方式
        response = notion.databases.query(
            database_id=NEWS_DB_ID,
            filter={"property": "狀態", "status": {"equals": "已發佈"}},
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
            page_size=100
        )

        for page in response.get('results', []):
            props = page.get('properties', {})

            # 提取標籤
            tags = extract_multi_select(props, '標籤')

            # 檢測是否會員專享
            is_premium = (
                '會員專享' in tags or
                extract_checkbox(props, '是否會員專享') or
                '獨家' in tags or
                '独家' in tags
            )

            article = {
                "id": page.get('id'),
                "title": extract_title(props),
                "content": extract_content(props),
                "category": extract_select(props, '類型'),
                "tags": tags,
                "status": extract_status(props, '狀態'),
                "source_url": extract_url(props, '來源'),
                "published_date": extract_date(props, '發布時間'),
                "is_ai_generated": extract_checkbox(props, 'AI生成'),
                "featured": extract_checkbox(props, '頭條'),
                "is_premium": is_premium,
                "cover_image": extract_url(props, '封面圖') or get_default_image(),
                "created_time": page.get('created_time'),
                "last_edited_time": page.get('last_edited_time')
            }

            articles.append(article)
            print(f"  ✓ {article['title'][:40]}...")

        # 處理分頁
        while response.get('has_more'):
            response = notion.databases.query(
                database_id=NEWS_DB_ID,
                filter={"property": "狀態", "status": {"equals": "已發佈"}},
                sorts=[{"timestamp": "created_time", "direction": "descending"}],
                start_cursor=response.get('next_cursor'),
                page_size=100
            )

            for page in response.get('results', []):
                props = page.get('properties', {})
                tags = extract_multi_select(props, '標籤')
                is_premium = '會員專享' in tags or extract_checkbox(props, '是否會員專享')

                article = {
                    "id": page.get('id'),
                    "title": extract_title(props),
                    "content": extract_content(props),
                    "category": extract_select(props, '類型'),
                    "tags": tags,
                    "status": extract_status(props, '狀態'),
                    "source_url": extract_url(props, '來源'),
                    "published_date": extract_date(props, '發布時間'),
                    "is_ai_generated": extract_checkbox(props, 'AI生成'),
                    "featured": extract_checkbox(props, '頭條'),
                    "is_premium": is_premium,
                    "cover_image": extract_url(props, '封面圖') or get_default_image(),
                    "created_time": page.get('created_time'),
                    "last_edited_time": page.get('last_edited_time')
                }
                articles.append(article)
                print(f"  ✓ {article['title'][:40]}...")

    except Exception as e:
        print(f"❌ 獲取文章失敗: {e}")
        return []

    return articles

def extract_title(props):
    try:
        title_prop = props.get('標題', props.get('title', {}))
        if 'title' in title_prop and title_prop['title']:
            return title_prop['title'][0]['text']['content']
    except:
        pass
    return "無標題"

def extract_content(props):
    try:
        content_prop = props.get('內容', props.get('content', {}))
        if 'rich_text' in content_prop and content_prop['rich_text']:
            texts = []
            for rt in content_prop['rich_text']:
                if 'text' in rt and 'content' in rt['text']:
                    texts.append(rt['text']['content'])
            return ' '.join(texts)
    except:
        pass
    return ""

def extract_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'select' in prop and prop['select']:
            return prop['select']['name']
    except:
        pass
    return ""

def extract_status(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'status' in prop and prop['status']:
            return prop['status']['name']
    except:
        pass
    return ""

def extract_multi_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'multi_select' in prop:
            return [tag['name'] for tag in prop['multi_select']]
    except:
        pass
    return []

def extract_url(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'url' in prop:
            return prop['url']
    except:
        pass
    return ""

def extract_date(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'date' in prop and prop['date']:
            return prop['date']['start']
    except:
        pass
    return datetime.now().isoformat()

def extract_checkbox(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'checkbox' in prop:
            return prop['checkbox']
    except:
        pass
    return False

def get_default_image():
    return "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

def save_to_json(articles):
    """保存到JSON文件"""

    # 分類整理
    hero = articles[:3] if len(articles) >= 3 else articles
    featured = [a for a in articles if a.get('featured') or a.get('is_premium')][:4]

    # 按分類整理
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

        if cat == '獨家' or '獨家' in tags or '独家' in tags:
            by_category['獨家'].append(article)
        elif cat == '現場' or '現場' in tags or '现场' in tags:
            by_category['現場'].append(article)
        elif cat == '專題' or '專題' in tags or '专题' in tags:
            by_category['專題'].append(article)
        elif cat == '國際' or '國際' in tags or '国际' in tags:
            by_category['國際'].append(article)
        elif cat == '新發行' or '新發行' in tags or '新发行' in tags:
            by_category['新發行'].append(article)

    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(articles),
        "data": {
            "all": articles,
            "hero": hero,
            "featured": featured,
            "latest": articles,
            "by_category": by_category
        }
    }

    os.makedirs('data', exist_ok=True)

    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已保存 {len(articles)} 篇文章到 data/news.json")

def main():
    print("\n" + "="*70)
    print("🎸 ChineseRocks 新聞發布系統")
    print(f" 時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    print("\n📡 從Notion獲取已發布文章...")
    articles = fetch_published_articles()

    if not articles:
        print("⚠️ 沒有已發布的文章")
        # 創建空文件
        save_to_json([])
        return

    print(f"\n✅ 獲取到 {len(articles)} 篇已發布文章")

    print("\n💾 保存到JSON文件...")
    save_to_json(articles)

    print("\n" + "="*70)
    print("📊 發布統計")
    print("="*70)
    print(f" 總文章數: {len(articles)} 篇")
    print(f" 頭條文章: {min(3, len(articles))} 篇")
    print("="*70)
    print("\n✅ 發布完成！前端將自動讀取 data/news.json")

if __name__ == "__main__":
    main()
