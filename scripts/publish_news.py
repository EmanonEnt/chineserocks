#!/usr/bin/env python3
"""
ChineseRocks 審核發佈腳本 v3.0
檢查Notion中狀態為"已發佈"的文章，更新到前端JSON文件
"""

import os
import json
import sys
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def debug_print(msg):
    """調試輸出"""
    print(f"[DEBUG] {msg}")

def get_notion_client():
    """獲取Notion客戶端，處理版本兼容性"""
    try:
        from notion_client import Client
        client = Client(auth=NOTION_TOKEN)
        debug_print("notion-client 加載成功")
        return client, "sdk"
    except ImportError as e:
        debug_print(f"notion_client 導入失敗: {e}")
        return None, "requests"

def notion_api_request(method, endpoint, **kwargs):
    """使用 requests 直接調用 Notion API"""
    import requests

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    url = f"https://api.notion.com/v1{endpoint}"

    if method == "POST":
        response = requests.post(url, headers=headers, json=kwargs.get('json', {}))
    elif method == "GET":
        response = requests.get(url, headers=headers, params=kwargs.get('params', {}))
    else:
        raise ValueError(f"不支持的 HTTP 方法: {method}")

    response.raise_for_status()
    return response.json()

def fetch_published_articles():
    """從Notion獲取已發佈的文章"""
    notion, client_type = get_notion_client()

    articles = []
    cursor = None

    debug_print(f"使用客戶端類型: {client_type}")
    debug_print(f"數據庫ID: {NEWS_DB_ID}")

    while True:
        try:
            # 構建查詢參數 - 查詢狀態為"已發佈"的文章
            query_params = {
                "database_id": NEWS_DB_ID,
                "filter": {
                    "property": "狀態",
                    "status": {
                        "equals": "已發佈"
                    }
                },
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
                "page_size": 100
            }

            if cursor:
                query_params["start_cursor"] = cursor

            debug_print(f"查詢參數: {json.dumps(query_params, ensure_ascii=False)}")

            # 根據客戶端類型調用 API
            if client_type == "sdk":
                try:
                    response = notion.databases.query(**query_params)
                    debug_print("SDK 查詢成功")
                except AttributeError as e:
                    debug_print(f"SDK 調用失敗: {e}, 切換到 requests 模式")
                    client_type = "requests"
                    response = notion_api_request("POST", f"/databases/{NEWS_DB_ID}/query", json=query_params)
            else:
                response = notion_api_request("POST", f"/databases/{NEWS_DB_ID}/query", json=query_params)
                debug_print("Requests 查詢成功")

            results = response.get('results', [])
            debug_print(f"獲取到 {len(results)} 條結果")

            for page in results:
                props = page.get('properties', {})

                # 調試：打印第一個結果的屬性
                if len(articles) == 0:
                    debug_print(f"第一個結果的屬性鍵: {list(props.keys())}")

                # 檢測是否會員專享
                tags = extract_multi_select(props, '標籤')
                is_premium = (
                    '會員專享' in tags or
                    extract_checkbox(props, '是否會員專享') or
                    '獨家' in tags
                )

                article = {
                    "id": page['id'],
                    "title": extract_title(props),
                    "content": extract_content(props),
                    "category": extract_select(props, '類型'),
                    "tags": tags,
                    "status": extract_status(props),  # 使用專門的函數提取狀態
                    "source_url": extract_url(props, '來源'),
                    "published_date": extract_date(props, '發布時間'),
                    "is_ai_generated": extract_checkbox(props, 'AI生成'),
                    "featured": extract_checkbox(props, '頭條'),
                    "is_premium": is_premium,
                    "cover_image": extract_url(props, '封面圖') or get_default_image(),
                    "created_time": page.get('created_time', ''),
                    "last_edited_time": page.get('last_edited_time', '')
                }

                articles.append(article)
                debug_print(f"處理文章: {article['title'][:30]}... 狀態: {article['status']}")

            if not response.get('has_more'):
                break
            cursor = response.get('next_cursor')

        except Exception as e:
            debug_print(f"獲取文章失敗: {e}")
            import traceback
            traceback.print_exc()
            break

    return articles

def extract_title(props):
    """提取標題"""
    try:
        title_prop = props.get('標題', props.get('title', {}))
        if 'title' in title_prop and title_prop['title']:
            return title_prop['title'][0]['text']['content']
    except Exception as e:
        debug_print(f"提取標題失敗: {e}")
    return "無標題"

def extract_content(props):
    """提取內容"""
    try:
        content_prop = props.get('內容', props.get('content', {}))
        if 'rich_text' in content_prop and content_prop['rich_text']:
            return content_prop['rich_text'][0]['text']['content']
    except Exception as e:
        debug_print(f"提取內容失敗: {e}")
    return ""

def extract_select(props, prop_name):
    """提取單選屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'select' in prop and prop['select']:
            return prop['select']['name']
    except Exception as e:
        debug_print(f"提取 {prop_name} 失敗: {e}")
    return ""

def extract_status(props):
    """提取狀態屬性（新版 Notion 使用 status 類型）"""
    try:
        # 先嘗試舊版 select 類型
        prop = props.get('狀態', {})
        if 'select' in prop and prop['select']:
            return prop['select']['name']
        # 再嘗試新版 status 類型
        if 'status' in prop and prop['status']:
            return prop['status']['name']
    except Exception as e:
        debug_print(f"提取狀態失敗: {e}")
    return ""

def extract_multi_select(props, prop_name):
    """提取多選屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'multi_select' in prop:
            return [tag['name'] for tag in prop['multi_select']]
    except Exception as e:
        debug_print(f"提取 {prop_name} 失敗: {e}")
    return []

def extract_url(props, prop_name):
    """提取 URL 屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'url' in prop:
            return prop['url']
    except Exception as e:
        debug_print(f"提取 {prop_name} 失敗: {e}")
    return ""

def extract_date(props, prop_name):
    """提取日期屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'date' in prop and prop['date']:
            return prop['date']['start']
    except Exception as e:
        debug_print(f"提取 {prop_name} 失敗: {e}")
    return datetime.now().isoformat()

def extract_checkbox(props, prop_name):
    """提取複選框屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'checkbox' in prop:
            return prop['checkbox']
    except Exception as e:
        debug_print(f"提取 {prop_name} 失敗: {e}")
    return False

def get_default_image():
    """獲取默認圖片"""
    return "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

def categorize_articles(articles):
    """分類文章"""
    categorized = {
        "all": articles,
        "hero": [],
        "featured": [],
        "latest": articles[:20],  # 最新20篇
        "by_category": {
            "全部": articles,
            "獨家": [],
            "現場": [],
            "專題": [],
            "國際": [],
            "新發行": []
        }
    }

    for article in articles:
        tags = article.get('tags', [])
        category = article.get('category', '')

        # 頭條文章（前3篇）
        if article.get('featured') or len(categorized['hero']) < 3:
            if len(categorized['hero']) < 3:
                categorized['hero'].append(article)
                continue

        # 精選文章（會員專享或獨家）
        if article.get('is_premium') or '獨家' in tags:
            if len(categorized['featured']) < 4:
                categorized['featured'].append(article)

        # 按分類歸檔
        if '獨家' in tags or category == '獨家':
            categorized['by_category']['獨家'].append(article)
        elif '現場' in tags or category in ['演出預告', '現場']:
            categorized['by_category']['現場'].append(article)
        elif '專題' in tags or category in ['專訪', '專題']:
            categorized['by_category']['專題'].append(article)
        elif '國際' in tags:
            categorized['by_category']['國際'].append(article)
        elif '新發行' in tags or category in ['樂評', '新發行']:
            categorized['by_category']['新發行'].append(article)

    return categorized

def save_to_json(data):
    """保存到JSON文件"""
    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(data.get('all', [])),
        "data": data
    }

    os.makedirs('data', exist_ok=True)

    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 已保存 {output['total_count']} 篇文章到 data/news.json")

def main():
    print("\n" + "="*70)
    print("🎸 ChineseRocks 審核發佈系統 v3.0")
    print(f" 時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    if not NOTION_TOKEN:
        print("❌ 錯誤: NOTION_TOKEN 未設置")
        sys.exit(1)

    print(f"\n📡 從Notion獲取已發佈文章...")

    articles = fetch_published_articles()

    if not articles:
        print("⚠️ 沒有已發佈的文章")
        # 創建空的 news.json
        save_to_json({"all": [], "hero": [], "featured": [], "latest": [], "by_category": {}})
        return

    print(f"✅ 獲取到 {len(articles)} 篇已發佈文章")

    print("\n📂 分類整理文章...")
    categorized = categorize_articles(articles)

    print("\n💾 保存到JSON文件...")
    save_to_json(categorized)

    print("\n" + "="*70)
    print("📊 發佈統計")
    print("="*70)
    print(f" 頭條文章: {len(categorized['hero'])} 篇")
    print(f" 精選文章: {len(categorized['featured'])} 篇")
    print(f" 最新文章: {len(categorized['latest'])} 篇")
    print(f" 獨家: {len(categorized['by_category']['獨家'])} 篇")
    print(f" 現場: {len(categorized['by_category']['現場'])} 篇")
    print(f" 專題: {len(categorized['by_category']['專題'])} 篇")
    print(f" 國際: {len(categorized['by_category']['國際'])} 篇")
    print(f" 新發行: {len(categorized['by_category']['新發行'])} 篇")
    print("="*70)
    print("\n✅ 發佈完成！前端將自動讀取 data/news.json")

if __name__ == "__main__":
    main()
