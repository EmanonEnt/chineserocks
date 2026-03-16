#!/usr/bin/env python3
"""
ChineseRocks 新聞發布腳本
從 Notion 數據庫獲取已審核的新聞，生成 news.json
"""

import os
import json
import requests
from datetime import datetime

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

def query_database():
    """查詢 Notion 數據庫獲取所有已發布新聞"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    all_results = []
    has_more = True
    start_cursor = None

    while has_more:
        data = {
            "filter": {
                "property": "狀態",
                "select": {
                    "equals": "已發佈"
                }
            },
            "page_size": 100
        }

        if start_cursor:
            data["start_cursor"] = start_cursor

        print(f"📡 發送請求... (cursor: {start_cursor})")
        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"❌ API 錯誤: {response.status_code}")
            print(f"響應: {response.text}")
            return None

        result = response.json()
        results = result.get("results", [])
        all_results.extend(results)

        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

        print(f"✅ 本頁獲取 {len(results)} 條，累計 {len(all_results)} 條")

    return all_results

def extract_property(properties, prop_name):
    """從 properties 中提取值"""
    prop = properties.get(prop_name)
    if not prop:
        return None

    prop_type = prop.get("type")

    if prop_type == "title":
        items = prop.get("title", [])
        return "".join([item.get("plain_text", "") for item in items])

    elif prop_type == "rich_text":
        items = prop.get("rich_text", [])
        return "".join([item.get("plain_text", "") for item in items])

    elif prop_type == "select":
        select = prop.get("select")
        return select.get("name") if select else None

    elif prop_type == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", [])]

    elif prop_type == "url":
        return prop.get("url")

    elif prop_type == "files":
        files = prop.get("files", [])
        if files:
            file = files[0]
            if file.get("type") == "external":
                return file.get("external", {}).get("url")
            elif file.get("type") == "file":
                return file.get("file", {}).get("url")
        return None

    elif prop_type == "date":
        date = prop.get("date")
        return date.get("start") if date else None

    return None

def process_news(pages):
    """處理新聞數據"""
    news_list = []

    for page in pages:
        props = page.get("properties", {})

        news = {
            "id": page.get("id"),
            "title": extract_property(props, "標題") or "無標題",
            "content": extract_property(props, "內容") or "",
            "category": extract_property(props, "類型") or "新聞",
            "tags": extract_property(props, "標籤") or [],
            "cover_image": extract_property(props, "封面圖"),
            "source_url": extract_property(props, "來源") or extract_property(props, "原文連結"),
            "published_date": extract_property(props, "發布時間") or extract_property(props, "發布日期"),
            "status": "已發佈",
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time")
        }

        # 默認圖片
        if not news["cover_image"]:
            news["cover_image"] = "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

        news_list.append(news)
        print(f"  ✓ {news['title'][:40]}...")

    # 按發布日期排序（新的在前）
    news_list.sort(key=lambda x: x["published_date"] or "", reverse=True)

    return news_list

def main():
    print("=" * 60)
    print("ChineseRocks 新聞發布系統")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("❌ 缺少環境變量")
        return

    # 獲取數據
    pages = query_database()
    if pages is None:
        print("❌ 查詢失敗")
        return

    print(f"\n📊 總共獲取 {len(pages)} 條已發布新聞")

    # 處理數據
    news_list = process_news(pages)

    # 構建輸出
    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(news_list),
        "data": {
            "all": news_list,
            "hero": news_list[:1] if news_list else [],
            "featured": [],
            "latest": news_list[:5],
            "by_category": {
                "全部": news_list,
                "獨家": [n for n in news_list if n["category"] == "獨家"],
                "現場": [n for n in news_list if n["category"] == "現場"],
                "專題": [n for n in news_list if n["category"] == "專題"],
                "國際": [n for n in news_list if n["category"] == "國際"],
                "新發行": [n for n in news_list if n["category"] == "新發行"]
            }
        }
    }

    # 保存
    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存: data/news.json")
    print(f"📰 總計: {len(news_list)} 條新聞")
    print("\n✅ 完成!")

if __name__ == "__main__":
    main()
