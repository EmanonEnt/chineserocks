#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

def get_all_news():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # 查詢所有已發布的新聞
    data = {
        "filter": {
            "property": "狀態",
            "select": {"equals": "已發佈"}
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print(f"❌ API 錯誤: {response.status_code}")
        print(response.text)
        return []

    results = response.json().get("results", [])
    print(f"✅ 從 Notion 獲取 {len(results)} 條已發布新聞")

    news_list = []
    for page in results:
        props = page.get("properties", {})

        # 提取標題
        title_prop = props.get("標題", {})
        title = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])])

        # 提取內容
        content_prop = props.get("內容", {})
        content = "".join([t.get("plain_text", "") for t in content_prop.get("rich_text", [])])

        # 提取類型
        type_prop = props.get("類型", {})
        category = type_prop.get("select", {}).get("name", "新聞") if type_prop.get("select") else "新聞"

        # 提取封面圖
        cover_prop = props.get("封面圖", {})
        cover_image = None
        if cover_prop.get("files"):
            file = cover_prop["files"][0]
            if file.get("type") == "external":
                cover_image = file.get("external", {}).get("url")
            elif file.get("type") == "file":
                cover_image = file.get("file", {}).get("url")

        if not cover_image:
            cover_image = "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

        # 提取來源
        source_prop = props.get("來源", {}) or props.get("原文連結", {})
        source_url = source_prop.get("url") if source_prop.get("type") == "url" else None

        news = {
            "id": page.get("id"),
            "title": title or "無標題",
            "content": content,
            "category": category,
            "cover_image": cover_image,
            "source_url": source_url,
            "published_date": props.get("發布時間", {}).get("date", {}).get("start") if props.get("發布時間") else None,
            "status": "已發佈"
        }

        news_list.append(news)
        print(f"  - {title[:40]}...")

    return news_list

def main():
    print("=" * 50)
    print("ChineseRocks 新聞發布")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    news = get_all_news()

    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(news),
        "data": {
            "all": news,
            "latest": news[:5],
            "hero": news[:1] if news else []
        }
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存 {len(news)} 條新聞到 data/news.json")

if __name__ == "__main__":
    main()
