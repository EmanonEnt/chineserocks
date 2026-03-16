#!/usr/bin/env python3
"""
ChineseRocks 新闻抓取脚本 v4.2
支持多种翻译 API，修复 Notion API 兼容性问题
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
from bs4 import BeautifulSoup

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

# 尝试导入 notion_client
try:
    from notion_client import Client
    NOTION_CLIENT_AVAILABLE = True
except ImportError:
    NOTION_CLIENT_AVAILABLE = False
    print("⚠️ notion-client 未安装，将使用 requests 直接调用 API")

# 翻译 API 配置
TRANSLATION_APIS = {
    "libretranslate": {
        "enabled": True,
        "url": "https://libretranslate.de/translate",
        "api_key": os.getenv("LIBRETRANSLATE_API_KEY", ""),
    },
    "mymemory": {
        "enabled": True,
        "url": "https://api.mymemory.translated.net/get",
        "api_key": os.getenv("MYMEMORY_API_KEY", ""),
    }
}

SOURCES = {
    "china": [
        {"name": "豆瓣音乐", "url": "https://www.douban.com/feed/review/music", "enabled": True},
        {"name": "秀动", "url": "https://www.showstart.com/rss", "enabled": True},
        {"name": "LiveGigsAsia", "url": "https://www.livegigsasia.com/feed", "enabled": True},
    ],
    "international": [
        {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/feed/", "enabled": True},
        {"name": "NME", "url": "https://www.nme.com/news/music/feed", "enabled": True},
        {"name": "Pitchfork", "url": "https://pitchfork.com/rss/news", "enabled": True},
    ]
}

CHINA_KEYWORDS = [
    "中国", "China", "Chinese", "北京", "上海", "广州", "深圳", "成都", "西安",
    "台北", "香港", "澳門", "台灣", "崔健", "唐朝", "黑豹", "万能青年旅店",
    "草东没有派对", "新裤子", "五条人", "痛仰", "草莓音乐节", "迷笛音乐节",
]

class NotionAPI:
    """Notion API 封装"""

    def __init__(self):
        self.token = NOTION_TOKEN
        if NOTION_CLIENT_AVAILABLE:
            self.client = Client(auth=self.token)
            self.mode = "sdk"
        else:
            self.client = None
            self.mode = "requests"

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def query_database(self, database_id, **kwargs):
        """查询数据库"""
        if self.mode == "sdk":
            try:
                return self.client.databases.query(database_id=database_id, **kwargs)
            except AttributeError:
                # 如果 SDK 失敗，切換到 requests
                self.mode = "requests"

        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        response = requests.post(url, headers=self.headers, json=kwargs)
        response.raise_for_status()
        return response.json()

    def create_page(self, **kwargs):
        """创建页面"""
        if self.mode == "sdk":
            return self.client.pages.create(**kwargs)

        url = "https://api.notion.com/v1/pages"
        response = requests.post(url, headers=self.headers, json=kwargs)
        response.raise_for_status()
        return response.json()


class Translator:
    def __init__(self):
        self.stats = {"libretranslate": 0, "mymemory": 0, "failed": 0}
        self.apis = TRANSLATION_APIS

    def translate(self, text):
        if not text or len(text.strip()) < 5:
            return None

        if self.apis["libretranslate"]["enabled"]:
            result = self._translate_libretranslate(text)
            if result:
                self.stats["libretranslate"] += 1
                return result

        if self.apis["mymemory"]["enabled"]:
            result = self._translate_mymemory(text)
            if result:
                self.stats["mymemory"] += 1
                return result

        self.stats["failed"] += 1
        return None

    def _translate_libretranslate(self, text):
        try:
            url = self.apis["libretranslate"]["url"]
            params = {"q": text[:500], "source": "en", "target": "zh", "format": "text"}
            response = requests.post(url, data=params, timeout=15)
            if response.status_code == 200:
                result = response.json()
                translated = result.get("translatedText", "").strip()
                if translated and translated.lower() != text.lower():
                    return translated
        except Exception as e:
            print(f"      ⚠️ LibreTranslate 失败: {e}")
        return None

    def _translate_mymemory(self, text):
        try:
            url = self.apis["mymemory"]["url"]
            params = {"q": text[:500], "langpair": "en|zh"}
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                result = response.json()
                translated = result.get("responseData", {}).get("translatedText", "").strip()
                if translated and "MYMEMORY" not in translated:
                    return translated
        except Exception as e:
            print(f"      ⚠️ MyMemory 失败: {e}")
        return None


class NewsFetcher:
    def __init__(self, source_type="china", limit=15):
        self.notion = NotionAPI()
        self.translator = Translator()
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0}
        self.articles = []

    def fetch_all(self):
        print("\n" + "="*70)
        print("🎸 ChineseRocks 新闻抓取系统 v4.2")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   模式: {self.source_type.upper()} | API模式: {self.notion.mode}")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
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

            print(f"   ✅ 获取 {count} 条")

        except Exception as e:
            print(f"   ❌ 失败: {e}")

    def _parse_entry(self, entry, source):
        published = entry.get('published', entry.get('updated', datetime.now().isoformat()))
        summary = entry.get('summary', entry.get('description', ''))

        # 清理 HTML
        if summary:
            soup = BeautifulSoup(summary, 'html.parser')
            summary = soup.get_text()
            summary = re.sub(r'\s+', ' ', summary).strip()

        return {
            "title": entry.get('title', ''),
            "link": entry.get('link', ''),
            "summary": summary[:1000],
            "published": published,
            "source_name": source['name'],
            "is_domestic": self.source_type == "china",
            "source_url": source['url']
        }

    def classify_and_filter(self):
        print("\n🔍 智能分类 & 翻译")
        print("-"*50)

        filtered = []
        for article in self.articles:
            result = self._classify(article)
            if result["keep"]:
                article["category"] = result["category"]
                article["tags"] = result["tags"]
                article["processed_title"] = self._process_title(article)
                filtered.append(article)
                print(f"   ✅ [{result['category']}] {article['title'][:45]}...")
            else:
                self.stats["skipped"] += 1

        self.articles = filtered
        print(f"\n   通过过滤: {len(filtered)} 条")
        return filtered

    def _classify(self, article):
        text = f"{article['title']} {article['summary']}".lower()
        is_domestic = article['is_domestic']

        if is_domestic:
            tags = self._auto_tag(text)
            return {"keep": True, "category": "DOMESTIC", "tags": tags}

        if any(kw.lower() in text for kw in ["china tour", "中国巡演"]):
            tags = self._auto_tag(text, is_tour=True)
            return {"keep": True, "category": "CHINA_TOUR", "tags": tags}

        if any(kw.lower() in text for kw in [k.lower() for k in CHINA_KEYWORDS]):
            tags = self._auto_tag(text)
            return {"keep": True, "category": "CHINA_RELATED", "tags": tags}

        return {"keep": False, "category": "FILTERED", "tags": []}

    def _auto_tag(self, text, is_tour=False):
        tags = []
        if is_tour:
            tags.append("来华演出")

        if any(w in text for w in ['朋克', 'punk']): tags.append("朋克")
        if any(w in text for w in ['独立', 'indie']): tags.append("独立")
        if any(w in text for w in ['金属', 'metal']): tags.append("金属")
        if any(w in text for w in ['民谣', 'folk']): tags.append("民谣")
        if any(w in text for w in ['音乐节', 'festival']): tags.append("音乐节")
        elif any(w in text for w in ['巡演', 'tour']): tags.append("巡演")
        elif any(w in text for w in ['专辑', 'album']): tags.append("新专辑")

        if not tags:
            tags.append("摇滚")

        return tags[:5]

    def _process_title(self, article):
        title = article['title'].strip()
        if article['is_domestic']:
            return title

        print(f"   🌐 翻译: {title[:40]}...")
        subtitle = self.translator.translate(title)
        if subtitle:
            return f"{title} | {subtitle}"
        return title

    def sync_to_notion(self):
        print("\n💾 同步到 Notion")
        print("-"*50)

        added = 0
        exists = 0

        for article in self.articles:
            article_id = hashlib.md5(article['link'].encode()).hexdigest()[:16]

            if self._check_exists(article_id):
                print(f"   ⏭️ 已存在: {article['title'][:40]}...")
                exists += 1
                continue

            if self._add_to_notion(article, article_id):
                added += 1
                print(f"   ✅ 新增: {article['title'][:40]}...")
            else:
                print(f"   ❌ 失败: {article['title'][:40]}...")

        self.stats["added"] = added
        self.stats["exists"] = exists
        return added

    def _check_exists(self, article_id):
        try:
            response = self.notion.query_database(
                NEWS_DB_ID,
                filter={"property": "来源", "url": {"contains": article_id}}
            )
            return len(response.get('results', [])) > 0
        except Exception as e:
            print(f"   ⚠️ 检查存在性失败: {e}")
            return False

    def _add_to_notion(self, article, article_id):
        try:
            prefixes = {"CHINA_TOUR": "【来华】", "DOMESTIC": "", "CHINA_RELATED": ""}
            prefix = prefixes.get(article['category'], "")
            title = f"{prefix}{article['processed_title']}"[:150]

            type_map = {"CHINA_TOUR": "演出预告", "DOMESTIC": "新闻", "CHINA_RELATED": "新闻"}

            self.notion.create_page(
                parent={"database_id": NEWS_DB_ID},
                properties={
                    "标题": {"title": [{"text": {"content": title}}]},
                    "内容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                    "标签": {"multi_select": [{"name": tag} for tag in article['tags']]},
                    "状态": {"status": {"name": "待审核"}},  # 使用 status 类型
                    "类型": {"select": {"name": type_map.get(article['category'], "新闻")}},
                    "来源": {"url": article['link']},
                    "发布时间": {"date": {"start": datetime.now().isoformat()}},
                    "AI生成": {"checkbox": False}
                }
            )
            return True
        except Exception as e:
            print(f"   ❌ Notion API 错误: {e}")
            return False

    def print_report(self):
        print("\n" + "="*70)
        print("📈 执行报告")
        print("="*70)
        print(f"   总抓取:     {len(self.articles)} 条")
        print(f"   新增入库:   {self.stats['added']} 条")
        print(f"   已存在:     {self.stats['exists']} 条")
        print(f"   丢弃:       {self.stats['skipped']} 条")
        print("="*70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='china', choices=['china', 'international'])
    parser.add_argument('--limit', type=int, default=15)
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
