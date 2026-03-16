#!/usr/bin/env python3
"""
ChineseRocks 新聞發布腳本
從 Notion 獲取已發布新聞，生成 news.json
使用標準庫 urllib，無需額外安裝 requests
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

def notion_api_call(url, data=None):
    """調用 Notion API"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers=headers,
        method='POST' if data else 'GET'
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"❌ API 錯誤: {e.code}")
        print(e.read().decode('utf-8'))
        return None

def get_published_news():
    """獲取所有已發布的新聞"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    data = {
        "filter": {
            "property": "狀態",
            "select": {"equals": "已發佈"}
        },
        "sorts": [
            {
                "property": "發布時間",
                "direction": "descending"
            }
        ]
    }

    result = notion_api_call(url, data)
    if not result:
        return []

    results = result.get("results", [])
    print(f"✅ 找到 {len(results)} 條已發布新聞")

    news_list = []
    for page in results:
        props = page.get("properties", {})

        # 提取標題
        title = ""
        title_prop = props.get("標題", {})
        if title_prop.get("title"):
            title = "".join([t.get("plain_text", "") for t in title_prop["title"]])

        # 提取內容
        content = ""
        content_prop = props.get("內容", {})
        if content_prop.get("rich_text"):
            content = "".join([t.get("plain_text", "") for t in content_prop["rich_text"]])

        # 提取類型
        category = "新聞"
        type_prop = props.get("類型", {})
        if type_prop.get("select"):
            category = type_prop["select"].get("name", "新聞")

        # 提取標籤
        tags = []
        tags_prop = props.get("標籤", {})
        if tags_prop.get("multi_select"):
            tags = [t.get("name", "") for t in tags_prop["multi_select"]]

        # 提取封面圖
        cover_image = None
        cover_prop = props.get("封面圖", {})
        if cover_prop.get("files") and len(cover_prop["files"]) > 0:
            file = cover_prop["files"][0]
            if file.get("type") == "external":
                cover_image = file.get("external", {}).get("url")
            elif file.get("type") == "file":
                cover_image = file.get("file", {}).get("url")

        if not cover_image:
            cover_image = "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

        # 提取來源 URL
        source_url = None
        source_prop = props.get("來源", {}) or props.get("原文連結", {})
        if source_prop.get("type") == "url":
            source_url = source_prop.get("url")

        # 提取發布日期
        published_date = None
        date_prop = props.get("發布時間", {}) or props.get("發布日期", {})
        if date_prop.get("date"):
            published_date = date_prop["date"].get("start")

        # 是否會員專享
        is_premium = False
        premium_prop = props.get("是否會員專享", {})
        if premium_prop.get("checkbox"):
            is_premium = premium_prop["checkbox"]

        news_item = {
            "id": page.get("id"),
            "title": title or "無標題",
            "content": content,
            "category": category,
            "tags": tags,
            "cover_image": cover_image,
            "source_url": source_url,
            "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
            "is_premium": is_premium,
            "status": "已發佈"
        }

        news_list.append(news_item)
        print(f"  ✓ {title[:50]}...")

    return news_list

def main():
    print("=" * 60)
    print("ChineseRocks 新聞發布系統")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not NOTION_TOKEN or not DATABASE_ID:
        print("❌ 錯誤: 缺少環境變量")
        return

    news = get_published_news()

    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(news),
        "data": {
            "all": news,
            "latest": news[:10],
            "hero": news[:1] if news else [],
            "by_category": {
                "全部": news,
                "獨家": [n for n in news if n["category"] == "獨家"],
                "現場": [n for n in news if n["category"] == "現場"],
                "專題": [n for n in news if n["category"] == "專題"],
                "國際": [n for n in news if n["category"] == "國際"],
                "新發行": [n for n in news if n["category"] == "新發行"]
            }
        }
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存 {len(news)} 條新聞到 data/news.json")
    print("✅ 完成!")

if __name__ == "__main__":
    main()
