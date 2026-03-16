#!/usr/bin/env python3
"""
ChineseRocks 審核發佈腳本 v4.2
檢查Notion中狀態為"已發佈"的文章，更新到前端JSON文件
使用繁體中文屬性名稱
"""

import os
import json
import sys
from datetime import datetime
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def debug_print(msg):
    """調試輸出"""
    print(f"[DEBUG] {msg}")

def notion_api_request(method, endpoint, json_data=None):
    """使用 requests 直接調用 Notion API"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    url = f"https://api.notion.com/v1{endpoint}"

    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")

        if response.status_code != 200:
            debug_print(f"API 錯誤: {response.status_code}")
            debug_print(f"響應內容: {response.text}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        debug_print(f"API 請求失敗: {e}")
        raise

def fetch_published_articles():
    """從Notion獲取已發佈的文章"""
    articles = []
    cursor = None

    debug_print(f"數據庫ID: {NEWS_DB_ID}")

    while True:
        try:
            # 構建查詢參數 - 使用繁體中文
            query_data = {
                "page_size": 100
            }

            # 使用繁體中文"狀態"
            query_data["filter"] = {
                "property": "狀態",
                "select": {
                    "equals": "已發佈"
                }
            }

            query_data["sorts"] = [
                {
                    "timestamp": "created_time",
                    "direction": "descending"
                }
            ]

            if cursor:
                query_data["start_cursor"] = cursor

            debug_print(f"查詢數據: {json.dumps(query_data, ensure_ascii=False)}")

            response = notion_api_request(
                "POST", 
                f"/databases/{NEWS_DB_ID}/query", 
                json_data=query_data
            )

            results = response.get('results', [])
            debug_print(f"獲取到 {len(results)} 條結果")

            for page in results:
                props = page.get('properties', {})

                if len(articles) == 0:
                    debug_print(f"第一個結果的屬性鍵: {list(props.keys())}")

                article = process_page(page, props)
                if article:
                    articles.append(article)
                    debug_print(f"處理文章: {article['title'][:30]}...")

            if not response.get('has_more'):
                break
            cursor = response.get('next_cursor')

        except Exception as e:
            debug_print(f"獲取文章失敗: {e}")
            import traceback
            traceback.print_exc()
            break

    return articles

def process_page(page, props):
    """處理單個頁面數據 - 使用繁體中文屬性名"""
    try:
        title = extract_title(props)
        tags = extract_multi_select(props, '標籤')  # 繁體

        is_premium = (
            '會員專享' in tags or
            extract_checkbox(props, '是否會員專享') or  # 繁體
            '獨家' in tags
        )

        return {
            "id": page['id'],
            "title": title,
            "content": extract_content(props),
            "category": extract_select(props, '類型'),  # 繁體
            "tags": tags,
            "status": extract_status(props),
            "source_url": extract_url(props, '來源'),  # 繁體
            "published_date": extract_date(props, '發布時間'),  # 繁體
            "is_ai_generated": extract_checkbox(props, 'AI生成'),  # 繁體
            "featured": extract_checkbox(props, '頭條'),  # 繁體
            "is_premium": is_premium,
            "cover_image": extract_url(props, '封面圖') or get_default_image(),  # 繁體
            "created_time": page.get('created_time', ''),
            "last_edited_time": page.get('last_edited_time', '')
        }
    except Exception as e:
        debug_print(f"處理頁面失敗: {e}")
        return None

def extract_title(props):
    """提取標題 - 繁體"""
    try:
        title_prop = props.get('標題', props.get('title', {}))  # 繁體
        if 'title' in title_prop and title_prop['title']:
            return title_prop['title'][0]['text']['content']
    except:
        pass
    return "無標題"

def extract_content(props):
    """提取內容 - 繁體"""
    try:
        content_prop = props.get('內容', props.get('content', {}))  # 繁體
        if 'rich_text' in content_prop and content_prop['rich_text']:
            return content_prop['rich_text'][0]['text']['content']
    except:
        pass
    return ""

def extract_select(props, prop_name):
    """提取單選屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'select' in prop and prop['select']:
            return prop['select']['name']
    except:
        pass
    return ""

def extract_status(props):
    """提取狀態屬性 - 繁體"""
    try:
        prop = props.get('狀態', {})  # 繁體
        if 'status' in prop and prop['status']:
            return prop['status']['name']
        if 'select' in prop and prop['select']:
            return prop['select']['name']
    except:
        pass
    return ""

def extract_multi_select(props, prop_name):
    """提取多選屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'multi_select' in prop:
            return [tag['name'] for tag in prop['multi_select']]
    except:
        pass
    return []

def extract_url(props, prop_name):
    """提取 URL 屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'url' in prop:
            return prop['url']
    except:
        pass
    return ""

def extract_date(props, prop_name):
    """提取日期屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'date' in prop and prop['date']:
            return prop['date']['start']
    except:
        pass
    return datetime.now().isoformat()

def extract_checkbox(props, prop_name):
    """提取複選框屬性"""
    try:
        prop = props.get(prop_name, {})
        if 'checkbox' in prop:
            return prop['checkbox']
    except:
        pass
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
        "latest": articles[:20],
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

        if article.get('featured') or len(categorized['hero']) < 3:
            if len(categorized['hero']) < 3:
                categorized['hero'].append(article)
                continue

        if article.get('is_premium') or '獨家' in tags:
            if len(categorized['featured']) < 4:
                categorized['featured'].append(article)

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
    print("🎸 ChineseRocks 審核發佈系統 v4.2")
    print(f" 時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    if not NOTION_TOKEN:
        print("❌ 錯誤: NOTION_TOKEN 未設置")
        sys.exit(1)

    print(f"\n📡 從Notion獲取已發佈文章...")

    try:
        articles = fetch_published_articles()

        if not articles:
            print("⚠️ 沒有已發佈的文章")
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

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 
