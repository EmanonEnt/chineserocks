#!/usr/bin/env python3
"""
ChineseRocks 新闻抓取脚本 v4.2 - 繁體字段修復版
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime
from urllib.parse import urlparse
import feedparser
import requests
from notion_client import Client
from bs4 import BeautifulSoup

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

SOURCES = {
    "china": [
        {"name": "豆瓣音乐", "url": "https://www.douban.com/feed/review/music", "enabled": True},
        {"name": "秀动", "url": "https://www.showstart.com/rss", "enabled": False},
        {"name": "LiveGigsAsia", "url": "https://www.livegigsasia.com/feed", "enabled": False},
    ],
    "international": [
        {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/feed/", "enabled": False},
        {"name": "NME", "url": "https://www.nme.com/news/music/feed", "enabled": False},
    ]
}

class NewsFetcher:
    def __init__(self, source_type="china", limit=15):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0}
        self.articles = []

    def fetch_all(self):
        print("\n" + "="*70)
        print("🎸 ChineseRocks 新闻抓取系统 v4.2")
        print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f" 模式: {self.source_type.upper()} | API模式: sdk")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
        if not sources:
            print(f"❌ 未知的源类型: {self.source_type}")
            return []

        print(f"\n📡 抓取 {len([s for s in sources if s['enabled']])} 个源")
        print("-"*50)

        for source in sources:
            if source["enabled"]:
                self._fetch_source(source)

        print(f"\n📊 抓取完成: 共 {len(self.articles)} 条")
        return self.articles

    def _fetch_source(self, source):
        try:
            print(f"📡 [{source['name']}]")
            feed = feedparser.parse(source['url'])

            count = 0
            for entry in feed.entries[:self.limit]:
                article = self._parse_entry(entry, source)
                if article:
                    self.articles.append(article)
                    count += 1

            print(f" ✅ 获取 {count} 条")

        except Exception as e:
            print(f" ❌ 失败: {e}")

    def _parse_entry(self, entry, source):
        summary = entry.get('summary', entry.get('description', ''))
        summary = self._clean_html(summary)

        return {
            "title": entry.get('title', ''),
            "link": entry.get('link', ''),
            "summary": summary[:1000],
            "published": entry.get('published', datetime.now().isoformat()),
            "source_name": source['name'],
            "is_domestic": self.source_type == "china"
        }

    def _clean_html(self, html):
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def classify_and_filter(self):
        print("\n🔍 智能分类 & 翻译")
        print("-"*50)

        filtered = []
        for article in self.articles:
            # 简单分类
            category = "DOMESTIC" if article['is_domestic'] else "INTERNATIONAL"
            tags = ["摇滚", "新闻"]

            article["category"] = category
            article["tags"] = tags
            filtered.append(article)
            print(f" ✅ [{category}] {article['title'][:45]}...")

        self.articles = filtered
        print(f"\n 通过过滤: {len(filtered)} 条")
        return filtered

    def sync_to_notion(self):
        print("\n💾 同步到 Notion")
        print("-"*50)

        added = 0
        exists = 0

        for article in self.articles:
            article_id = self._generate_id(article['link'])

            if self._check_exists(article_id):
                print(f" ⏭️ 已存在: {article['title'][:40]}...")
                exists += 1
                continue

            if self._add_to_notion(article, article_id):
                added += 1
                print(f" ✅ 新增: {article['title'][:40]}...")
            else:
                print(f" ❌ 失败: {article['title'][:40]}...")

        self.stats["added"] = added
        self.stats["exists"] = exists
        return added

    def _generate_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()[:16]

    def _check_exists(self, article_id):
        try:
            # 修復：使用正確的繁體字段名"來源"
            response = self.notion.databases.query(
                database_id=NEWS_DB_ID,
                filter={
                    "property": "來源",
                    "url": {"contains": article_id}
                }
            )
            return len(response['results']) > 0
        except Exception as e:
            print(f" ⚠️ 检查存在性失败: {e}")
            return False

    def _add_to_notion(self, article, article_id):
        try:
            title = article['title'][:150]

            # 修復：使用繁體字段名
            properties = {
                "標題": {"title": [{"text": {"content": title}}]},
                "內容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                "標籤": {"multi_select": [{"name": tag} for tag in article['tags']]},
                "狀態": {"status": {"name": "待審核"}},  # 修復：使用status類型
                "分類": {"select": {"name": "新聞"}},  # 修復：使用"分類"而不是"類型"
                "來源": {"url": article['link']},
                "發布日期": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
                "AI生成": {"checkbox": False}
            }

            # 可選：封面圖（如果有）
            # "封面圖": {"url": "https://..."}

            self.notion.pages.create(
                parent={"database_id": NEWS_DB_ID},
                properties=properties
            )
            return True
        except Exception as e:
            print(f" ❌ Notion API 错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_report(self):
        print("\n" + "="*70)
        print("📈 执行报告")
        print("="*70)
        print(f" 总抓取: {len(self.articles)} 条")
        print(f" 新增入库: {self.stats['added']} 条")
        print(f" 已存在: {self.stats['exists']} 条")
        print(f" 丢弃: {self.stats['skipped']} 条")
        print("="*70)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='china', choices=['china', 'international'], help='抓取源类型')
    parser.add_argument('--limit', type=int, default=15, help='每源抓取数量')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("❌ 错误: NOTION_TOKEN 未设置")
        sys.exit(1)

    fetcher = NewsFetcher(source_type=args.source, limit=args.limit)
    fetcher.fetch_all()
    fetcher.classify_and_filter()

    if fetcher.articles:
        fetcher.sync_to_notion()

    fetcher.print_report()

    result = {
        **fetcher.stats,
        "source": args.source,
        "timestamp": datetime.now().isoformat()
    }
    with open("fetch_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已保存到 fetch_result.json")

if __name__ == "__main__":
    main()
