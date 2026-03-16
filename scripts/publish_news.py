#!/usr/bin/env python3
"""
ChineseRocks 审核发布脚本
检查Notion中状态为"已发布"的文章，更新到前端JSON文件
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
    cursor = None

    while True:
        try:
            if cursor:
                response = notion.databases.query(
                    database_id=NEWS_DB_ID,
                    filter={"property": "状态", "select": {"equals": "已发布"}},
                    sorts=[{"property": "发布时间", "direction": "descending"}],
                    start_cursor=cursor,
                    page_size=100
                )
            else:
                response = notion.databases.query(
                    database_id=NEWS_DB_ID,
                    filter={"property": "状态", "select": {"equals": "已发布"}},
                    sorts=[{"property": "发布时间", "direction": "descending"}],
                    page_size=100
                )

            for page in response['results']:
                props = page['properties']

                # 检测是否会员专享
                tags = extract_multi_select(props, '标签')
                is_premium = (
                    '会员专享' in tags or
                    extract_checkbox(props, '是否会员专享') or
                    '獨家' in tags or
                    '独家' in tags
                )

                article = {
                    "id": page['id'],
                    "title": extract_title(props),
                    "content": extract_content(props),
                    "category": extract_select(props, '类型'),
                    "tags": tags,
                    "status": extract_select(props, '状态'),
                    "source_url": extract_url(props, '来源'),
                    "published_date": extract_date(props, '发布时间'),
                    "is_ai_generated": extract_checkbox(props, 'AI生成'),
                    "featured": extract_checkbox(props, '头条'),
                    "is_premium": is_premium,
                    "cover_image": extract_url(props, '封面图') or get_default_image()
                }

                articles.append(article)

            if not response['has_more']:
                break
            cursor = response['next_cursor']

        except Exception as e:
            print(f"❌ 获取文章失败: {e}")
            break

    return articles

def extract_title(props):
    try:
        title_prop = props.get('标题', {})
        if 'title' in title_prop and title_prop['title']:
            return title_prop['title'][0]['text']['content']
    except:
        pass
    return "无标题"

def extract_content(props):
    try:
        content_prop = props.get('内容', {})
        if 'rich_text' in content_prop and content_prop['rich_text']:
            return content_prop['rich_text'][0]['text']['content']
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

def categorize_articles(articles):
    """分类文章"""
    categorized = {
        "hero": [],
        "featured": [],
        "latest": [],
        "by_category": {
            "全部": [],
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
        if article.get('featured') or len(categorized['hero']) < 3:
            if len(categorized['hero']) < 3:
                categorized['hero'].append(article)
                continue

        # 精选文章（会员专享或独家）
        if article.get('is_premium') or '独家' in tags or '獨家' in tags:
            if len(categorized['featured']) < 4:
                categorized['featured'].append(article)

        # 按分类归档
        if '獨家' in tags or '独家' in tags or category == '獨家':
            categorized['by_category']['獨家'].append(article)
        elif '現場' in tags or '现场' in tags or category in ['演出预告', '現場']:
            categorized['by_category']['現場'].append(article)
        elif '專題' in tags or '专题' in tags or category in ['专访', '專題']:
            categorized['by_category']['專題'].append(article)
        elif '國際' in tags or '国际' in tags:
            categorized['by_category']['國際'].append(article)
        elif '新發行' in tags or '新发行' in tags or category in ['乐评', '新發行']:
            categorized['by_category']['新發行'].append(article)
        else:
            categorized['by_category']['全部'].append(article)

        categorized['latest'].append(article)

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

    print(f"✅ 已保存 {output['total_count']} 篇文章到 data/news.json")

def main():
    print("\n" + "="*70)
    print("🎸 ChineseRocks 审核发布系统")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    if not NOTION_TOKEN:
        print("❌ 错误: NOTION_TOKEN 未设置")
        return

    print("\n📡 从Notion获取已发布文章...")
    articles = fetch_published_articles()

    if not articles:
        print("⚠️ 没有已发布的文章")
        return

    print(f"✅ 获取到 {len(articles)} 篇已发布文章")

    print("\n📂 分类整理文章...")
    categorized = categorize_articles(articles)

    print("\n💾 保存到JSON文件...")
    save_to_json(categorized)

    print("\n" + "="*70)
    print("📊 发布统计")
    print("="*70)
    print(f" 头条文章: {len(categorized['hero'])} 篇")
    print(f" 精选文章: {len(categorized['featured'])} 篇")
    print(f" 最新文章: {len(categorized['latest'])} 篇")
    print(f" 獨家: {len(categorized['by_category']['獨家'])} 篇")
    print(f" 現場: {len(categorized['by_category']['現場'])} 篇")
    print(f" 專題: {len(categorized['by_category']['專題'])} 篇")
    print(f" 國際: {len(categorized['by_category']['國際'])} 篇")
    print(f" 新發行: {len(categorized['by_category']['新發行'])} 篇")
    print("="*70)
    print("\n✅ 发布完成！前端将自动读取 data/news.json")

if __name__ == "__main__":
    main()
