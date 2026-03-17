#!/usr/bin/env python3
"""
ChineseRocks 新聞發布系統
從 Notion 獲取已審核文章並發布到網站
"""

import os
import json
import requests
from datetime import datetime
from notion_client import Client

# 初始化 Notion 客戶端
notion = Client(auth=os.environ.get('NOTION_TOKEN'))

# 數據庫 ID
NEWS_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

def fetch_published_articles():
    """從 Notion 獲取已發布狀態的文章"""
    articles = []

    try:
        # 使用新版 API 查詢數據庫 - 修正 filter 語法
        query_params = {
            "database_id": NEWS_DATABASE_ID,
            "filter": {
                "property": "狀態",
                "status": {
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

        print(f"查詢參數: {json.dumps(query_params['filter'], ensure_ascii=False)}")

        # 新版 notion-client 使用正確的調用方式
        response = notion.databases.query(**query_params)

        print(f"成功獲取 {len(response['results'])} 篇文章")

        for page in response['results']:
            article = parse_article(page)
            if article:
                articles.append(article)

    except Exception as e:
        print(f"獲取文章失敗: {str(e)}")
        import traceback
        traceback.print_exc()

    return articles

def parse_article(page):
    """解析 Notion 頁面數據為文章對象"""
    try:
        props = page.get('properties', {})

        # 標題
        title = ""
        if '標題' in props and props['標題'].get('title'):
            title = props['標題']['title'][0].get('plain_text', '')
        elif 'title' in props and props['title'].get('title'):
            title = props['title']['title'][0].get('plain_text', '')

        # 內容
        content = ""
        if '內容' in props and props['內容'].get('rich_text'):
            content = props['內容']['rich_text'][0].get('plain_text', '')
        elif 'content' in props and props['content'].get('rich_text'):
            content = props['content']['rich_text'][0].get('plain_text', '')

        # 類型/分類
        category = ""
        if '類型' in props and props['類型'].get('select'):
            category = props['類型']['select'].get('name', '')
        elif 'category' in props and props['category'].get('select'):
            category = props['category']['select'].get('name', '')

        # 標籤
        tags = []
        if '標籤' in props and props['標籤'].get('multi_select'):
            tags = [tag['name'] for tag in props['標籤']['multi_select']]
        elif 'tags' in props and props['tags'].get('multi_select'):
            tags = [tag['name'] for tag in props['tags']['multi_select']]

        # 封面圖
        cover_image = ""
        if '封面圖' in props and props['封面圖'].get('files'):
            files = props['封面圖']['files']
            if files:
                cover_image = files[0].get('external', {}).get('url', '') or files[0].get('file', {}).get('url', '')
        elif 'cover_image' in props and props['cover_image'].get('files'):
            files = props['cover_image']['files']
            if files:
                cover_image = files[0].get('external', {}).get('url', '') or files[0].get('file', {}).get('url', '')

        # 來源鏈接
        source_url = ""
        if '來源' in props and props['來源'].get('url'):
            source_url = props['來源']['url']
        elif 'source' in props and props['source'].get('url'):
            source_url = props['source']['url']

        # 發布時間
        published_date = ""
        if '發布時間' in props and props['發布時間'].get('date'):
            published_date = props['發布時間']['date'].get('start', '')
        elif 'published_date' in props and props['published_date'].get('date'):
            published_date = props['published_date']['date'].get('start', '')

        # 是否會員專享
        is_premium = False
        if '標籤' in props and props['標籤'].get('multi_select'):
            is_premium = any(tag['name'] == '會員專享' for tag in props['標籤']['multi_select'])

        # 特色標記
        featured = False
        if '標籤' in props and props['標籤'].get('multi_select'):
            featured = any(tag['name'] in ['編輯精選', '編輯精選'] for tag in props['標籤']['multi_select'])

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
            "created_time": page.get('created_time', ''),
            "last_edited_time": page.get('last_edited_time', '')
        }

    except Exception as e:
        print(f"解析文章 {page.get('id')} 失敗: {str(e)}")
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
    if not os.environ.get('NOTION_TOKEN'):
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
        premium_mark = "會員" if article['is_premium'] else ""
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
