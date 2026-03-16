#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 审核发布脚本 - API修復版
使用新版 notion-client API
"""

import os
import json
from datetime import datetime
from notion_client import Client

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def fetch_published_articles():
    """从Notion获取已发布的文章"""
    notion = Client(auth=NOTION_TOKEN)

    articles = []

    try:
        print("正在查询Notion数据库...")

        # 修復：使用新版API調用方式
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

        print(f"查询成功，获取到 {len(response['results'])} 篇文章")

        for page in response['results']:
            try:
                props = page['properties']

                # 提取字段
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

                # 檢查是否會員專享
                if '會員專享' in article['tags'] or '獨家' in article['tags']:
                    article['is_premium'] = True

                articles.append(article)
                print(f"  ✓ {article['title'][:40]}...")

            except Exception as e:
                print(f"  ✗ 處理文章失敗: {e}")
                continue

    except Exception as e:
        print(f"獲取文章失敗: {e}")
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
    return "無標題"

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

def categorize_articles(articles):
    """分类文章"""
    categorized = {
        "hero": [],
        "featured": [],
        "latest": [],
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

        # 头条文章（前3篇）
        if article.get('featured') and len(categorized['hero']) < 3:
            categorized['hero'].append(article)
            continue

        # 精选文章
        if article.get('is_premium') and len(categorized['featured']) < 4:
            categorized['featured'].append(article)

        # 按分类归档
        if '獨家' in tags or category == '獨家':
            categorized['by_category']['獨家'].append(article)
        elif '現場' in tags or category in ['演出预告', '現場']:
            categorized['by_category']['現場'].append(article)
        elif '專題' in tags or category in ['专访', '專題']:
            categorized['by_category']['專題'].append(article)
        elif '國際' in tags:
            categorized['by_category']['國際'].append(article)
        elif '新發行' in tags or category in ['乐评', '新發行']:
            categorized['by_category']['新發行'].append(article)

        categorized['latest'].append(article)

    # 如果hero不够3篇，从latest补充
    while len(categorized['hero']) < 3 and categorized['latest']:
        for article in categorized['latest']:
            if article not in categorized['hero']:
                categorized['hero'].append(article)
                if len(categorized['hero']) >= 3:
                    break

    return categorized

def save_to_json(data):
    """保存到JSON文件"""
    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(data.get('latest', [])),
        "data": data
    }

    os.makedirs('data', exist_ok=True)

    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n已保存 {output['total_count']} 篇文章到 data/news.json")

def main():
    print("\n" + "="*70)
    print("ChineseRocks 审核发布系统")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    if not NOTION_TOKEN:
        print("错误: NOTION_TOKEN 未设置")
        return

    print("\n从Notion获取已发布文章...")
    articles = fetch_published_articles()

    if not articles:
        print("没有已发布的文章")
        # 創建空文件
        empty_data = {
            "hero": [],
            "featured": [],
            "latest": [],
            "by_category": {"全部": [], "獨家": [], "現場": [], "專題": [], "國際": [], "新發行": []}
        }
        save_to_json(empty_data)
        return

    print(f"\n获取到 {len(articles)} 篇已发布文章")

    print("\n分类整理文章...")
    categorized = categorize_articles(articles)

    print("\n保存到JSON文件...")
    save_to_json(categorized)

    print("\n" + "="*70)
    print("发布统计")
    print("="*70)
    print(f"头条文章: {len(categorized['hero'])} 篇")
    print(f"精选文章: {len(categorized['featured'])} 篇")
    print(f"最新文章: {len(categorized['latest'])} 篇")
    print(f"獨家: {len(categorized['by_category']['獨家'])} 篇")
    print(f"現場: {len(categorized['by_category']['現場'])} 篇")
    print(f"專題: {len(categorized['by_category']['專題'])} 篇")
    print(f"國際: {len(categorized['by_category']['國際'])} 篇")
    print(f"新發行: {len(categorized['by_category']['新發行'])} 篇")
    print("="*70)
    print("\n发布完成！前端将自动读取 data/news.json")

if __name__ == "__main__":
    main()
