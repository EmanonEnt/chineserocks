#!/usr/bin/env python3
"""
ChineseRocks 新聞發布腳本 - 修復版
從Notion數據庫讀取已審核的文章，生成 news.json
"""

import os
import json
from datetime import datetime, timezone
from notion_client import Client

# Notion配置
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID') or os.environ.get('NEWS_DB_ID')

# 分類映射表 - 支持多種寫法
CATEGORY_MAP = {
    '獨家': '獨家',
    '独家': '獨家', 
    'EXCLUSIVE': '獨家',
    'exclusive': '獨家',
    '獨家 EXCLUSIVE': '獨家',
    '現場': '現場',
    '现场': '現場',
    'LIVE': '現場',
    'live': '現場',
    '現場 LIVE': '現場',
    '專題': '專題',
    '专题': '專題',
    'FEATURE': '專題',
    'feature': '專題',
    '專題 FEATURE': '專題',
    '國際': '國際',
    '国际': '國際',
    'INTERNATIONAL': '國際',
    'international': '國際',
    '國際 INTERNATIONAL': '國際',
    '新發行': '新發行',
    '新发行': '新發行',
    'RELEASES': '新發行',
    'releases': '新發行',
    '新發行 RELEASES': '新發行',
}

def fetch_notion_articles():
    """從Notion獲取已發佈的文章"""
    notion = Client(auth=NOTION_TOKEN)

    try:
        print(f"正在查詢數據庫: {DATABASE_ID}")

        # 查詢數據庫 - 獲取已發佈的文章
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "property": "狀態",
                "status": {
                    "equals": "已發佈"
                }
            },
            sorts=[
                {
                    "property": "發布日期", 
                    "direction": "descending"
                }
            ]
        )

        articles = []
        print(f"找到 {len(response.get('results', []))} 篇文章")

        for page in response.get('results', []):
            try:
                props = page.get('properties', {})

                # 提取標題
                title_prop = props.get('標題', {}).get('title', [])
                title = title_prop[0].get('text', {}).get('content', '') if title_prop else ''

                # 提取內容
                content_prop = props.get('內容', {}).get('rich_text', [])
                content = content_prop[0].get('text', {}).get('content', '') if content_prop else ''

                # 提取分類 - 修復：使用select屬性
                category_select = props.get('分類', {}).get('select')
                category_raw = category_select.get('name', '全部') if category_select else '全部'
                # 標準化分類名稱
                category = CATEGORY_MAP.get(category_raw, category_raw)

                print(f"  文章: {title[:30]}... | 原始分類: {category_raw} -> 映射: {category}")

                # 提取標籤 - 修復：使用multi_select屬性
                tags_multi = props.get('標籤', {}).get('multi_select', [])
                tags = [tag.get('name', '') for tag in tags_multi]

                # 提取封面圖
                cover = props.get('封面圖', {}).get('url', '')

                # 提取發布日期
                date_prop = props.get('發布日期', {}).get('date', {})
                published_date = date_prop.get('start', '') if date_prop else ''

                # 提取會員專屬標記
                is_premium = any(t in tags for t in ['會員專享', '会员专享', 'PREMIUM', 'premium'])

                # 提取頭條標記
                is_featured = any(t in tags for t in ['頭條', '头条', 'FEATURED', 'featured', 'HOT'])

                if title:
                    articles.append({
                        'id': page.get('id'),
                        'title': title,
                        'content': content,
                        'category': category,
                        'tags': tags,
                        'cover_image': cover,
                        'published_date': published_date,
                        'is_premium': is_premium,
                        'is_featured': is_featured,
                        'created_time': page.get('created_time'),
                        'last_edited_time': page.get('last_edited_time')
                    })
            except Exception as e:
                print(f"處理文章時出錯: {e}")
                import traceback
                traceback.print_exc()
                continue

        return articles
    except Exception as e:
        print(f"獲取Notion數據失敗: {e}")
        import traceback
        traceback.print_exc()
        return []

def generate_news_json(articles):
    """生成 news.json 文件"""

    # 按日期排序
    articles.sort(key=lambda x: x.get('published_date', ''), reverse=True)

    # 頭條文章（最新的1-3篇，或有頭條標記的）
    featured_articles = [a for a in articles if a.get('is_featured')]
    if featured_articles:
        hero = featured_articles[:3]
    else:
        hero = articles[:3]

    # 精選文章（有頭條標記的，最多4篇）
    featured = featured_articles[:4]

    # 最新文章（最多12篇）
    latest = articles[:12]

    # 按分類分組 - 修復：確保所有分類都被正確填充
    by_category = {
        '全部': articles,
        '獨家': [],
        '現場': [],
        '專題': [],
        '國際': [],
        '新發行': []
    }

    for article in articles:
        cat = article.get('category', '全部')
        if cat in by_category:
            by_category[cat].append(article)
            print(f"  分類歸檔: {article['title'][:20]}... -> {cat}")
        else:
            print(f"  警告: 未知分類 '{cat}' - 文章: {article['title'][:30]}")

    news_data = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'total_count': len(articles),
        'data': {
            'all': articles,
            'hero': hero,
            'featured': featured,
            'latest': latest,
            'by_category': by_category
        }
    }

    return news_data

def save_json(data, filepath='data/news.json'):
    """保存JSON文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {filepath}")

def main():
    print("="*50)
    print("ChineseRocks 新聞發布腳本")
    print("="*50)

    if not NOTION_TOKEN:
        print("錯誤: 未設置 NOTION_TOKEN")
        return
    if not DATABASE_ID:
        print("錯誤: 未設置數據庫ID")
        return

    print(f"數據庫ID: {DATABASE_ID}")
    print("-"*50)

    articles = fetch_notion_articles()
    print(f"\n獲取到 {len(articles)} 篇文章")

    if articles:
        news_data = generate_news_json(articles)
        save_json(news_data)
        print(f"\n生成完成!")
        print(f"總數: {news_data['total_count']} 篇")
        print(f"頭條: {len(news_data['data']['hero'])} 篇")
        print(f"精選: {len(news_data['data']['featured'])} 篇")
        print("\n分類統計:")
        for cat, items in news_data['data']['by_category'].items():
            print(f"  - {cat}: {len(items)} 篇")
    else:
        print("\n沒有找到已發佈的文章")

if __name__ == '__main__':
    main()
