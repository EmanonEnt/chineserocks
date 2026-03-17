#!/usr/bin/env python3
"""
ChineseRocks 新聞發布系統
從 Notion 獲取已審核文章並發布到網站
"""

import os
import json
import urllib.request
from datetime import datetime

# 數據庫 ID 和 Token
NEWS_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')

def fetch_published_articles():
    """從 Notion 獲取已發布狀態的文章"""
    articles = []

    try:
        results = query_database_http()
        print(f"成功獲取 {len(results)} 篇文章")

        for page in results:
            article = parse_article(page)
            if article:
                articles.append(article)

    except Exception as e:
        print(f"獲取文章失敗: {str(e)}")
        import traceback
        traceback.print_exc()

    return articles

def query_database_http():
    """使用 HTTP API 直接查詢數據庫"""
    url = f"https://api.notion.com/v1/databases/{NEWS_DATABASE_ID}/query"

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # 修正：狀態是 Select 類型，使用 select.equals
    data = {
        "filter": {
            "property": "狀態",
            "select": {
                "equals": "已發佈"
            }
        },
        "sorts": [
            {
                "property": "發布時間",
                "direction": "descending"
            }
        ]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result.get('results', [])

def parse_article(page):
    """解析 Notion 頁面數據為文章對象"""
    try:
        props = page.get('properties', {})

        # 標題
        title = ""
        if '標題' in props:
            title_data = props['標題']
            if title_data.get('title'):
                title = title_data['title'][0].get('plain_text', '')

        # 內容
        content = ""
        if '內容' in props:
            content_data = props['內容']
            if content_data.get('rich_text'):
                content = content_data['rich_text'][0].get('plain_text', '')

        # 類型/分類
        category = ""
        if '類型' in props:
            type_data = props['類型']
            if type_data.get('select'):
                category = type_data['select'].get('name', '')

        # 標籤
        tags = []
        if '標籤' in props:
            tags_data = props['標籤']
            if tags_data.get('multi_select'):
                tags = [tag['name'] for tag in tags_data['multi_select']]

        # 封面圖
        cover_image = ""
        if '封面圖' in props:
            cover_data = props['封面圖']
            if cover_data.get('files'):
                files = cover_data['files']
                if files:
                    if files[0].get('external'):
                        cover_image = files[0]['external'].get('url', '')
                    elif files[0].get('file'):
                        cover_image = files[0]['file'].get('url', '')

        # 來源鏈接
        source_url = ""
        if '來源' in props:
            source_data = props['來源']
            if source_data.get('url'):
                source_url = source_data['url']

        # 發布時間
        published_date = ""
        if '發布時間' in props:
            date_data = props['發布時間']
            if date_data.get('date'):
                published_date = date_data['date'].get('start', '')

        # 是否會員專享 - Checkbox 類型
        is_premium = False
        if '是否會員專享' in props:
            premium_data = props['是否會員專享']
            if premium_data.get('checkbox') is not None:
                is_premium = premium_data['checkbox']

        # 如果沒有 Checkbox，檢查標籤中是否有「會員專享」
        if not is_premium and '會員專享' in tags:
            is_premium = True

        # 編輯精選標記
        featured = '編輯精選' in tags or '编辑精选' in tags

        # 首頁精選標記 (Home Featured) - Checkbox 類型
        home_featured = False
        if 'Home Featured' in props:
            home_featured_data = props['Home Featured']
            if home_featured_data.get('checkbox') is not None:
                home_featured = home_featured_data['checkbox']

        # 顯示順序 (Display Order) - Number 類型
        display_order = 999
        if 'Display Order' in props:
            order_data = props['Display Order']
            if order_data.get('number') is not None:
                display_order = int(order_data['number'])

        return {
            "id": page['id'],
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "cover_image": cover_image,
            "source_url": source_url,
            "published_date": published_date or datetime.now().isoformat(),
            "is_premium": is_premium,
            "featured": featured,
            "homeFeatured": home_featured,
            "displayOrder": display_order,
            "created_time": page.get('created_time', ''),
            "last_edited_time": page.get('last_edited_time', '')
        }

    except Exception as e:
        print(f"解析文章 {page.get('id')} 失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def save_to_json(articles):
    """保存文章到 JSON 文件"""
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'news.json')

    data = {
        "last_updated": datetime.now().isoformat(),
        "total_count": len(articles),
        "data": {
            "all": articles,
            "latest": articles[:10] if len(articles) >= 10 else articles
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已保存 {len(articles)} 篇文章到 {output_file}")
    return output_file

def main():
    print("=" * 60)
    print("ChineseRocks 新聞發布系統")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 檢查環境變量
    if not NOTION_TOKEN:
        print("錯誤: 未設置 NOTION_TOKEN")
        return

    if not NEWS_DATABASE_ID:
        print("錯誤: 未設置 NOTION_DATABASE_ID")
        return

    print(f"數據庫 ID: {NEWS_DATABASE_ID[:8]}...{NEWS_DATABASE_ID[-4:]}")

    # 獲取已發布文章
    print("從 Notion 獲取已發布文章...")
    articles = fetch_published_articles()

    if not articles:
        print("沒有已發布的文章")
        save_to_json([])
        return

    print(f"獲取到 {len(articles)} 篇文章:")
    for i, article in enumerate(articles[:5], 1):
        premium_mark = "【會員】" if article['is_premium'] else ""
        print(f"   {i}. {article['title'][:40]}... {premium_mark}")

    if len(articles) > 5:
        print(f"   ... 還有 {len(articles) - 5} 篇")

    # 保存到 JSON
    print("保存到 JSON 文件...")
    save_to_json(articles)

    print("發布完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()
