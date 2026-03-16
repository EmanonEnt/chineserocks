#!/usr/bin/env python3
"""
ChineseRocks 新闻抓取脚本 v4.1
支持多种翻译 API：LibreTranslate / MyMemory / Google / DeepL
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

# 翻译 API 配置（优先级排序）
TRANSLATION_APIS = {
    "libretranslate": {
        "enabled": True,
        "url": "https://libretranslate.de/translate",  # 公用实例
        "api_key": os.getenv("LIBRETRANSLATE_API_KEY", ""),  # 可选
    },
    "mymemory": {
        "enabled": True,
        "url": "https://api.mymemory.translated.net/get",
        "api_key": os.getenv("MYMEMORY_API_KEY", ""),  # 可选，提高限额
    },
    "google": {
        "enabled": False,  # 需要 GOOGLE_API_KEY
        "api_key": os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
    },
    "deepl": {
        "enabled": False,  # 需要 DEEPL_API_KEY
        "api_key": os.getenv("DEEPL_API_KEY", ""),
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
        {"name": "Kerrang", "url": "https://www.kerrang.com/feed", "enabled": True},
    ]
}

CHINA_KEYWORDS = [
    "中国", "China", "Chinese", "北京", "上海", "广州", "深圳", "成都", "西安",
    "台北", "香港", "澳門", "台灣", "Hong Kong", "Taiwan",
    "崔健", "唐朝", "黑豹", "窦唯", "张楚", "何勇",
    "万能青年旅店", "万青", "草东没有派对", "草東沒有派對", "新裤子", "五条人",
    "脑浊", "腦濁", "痛仰", "夜叉", "窒息", "二手玫瑰",
    "刺猬", "刺蝟", "后海大鲨鱼", "盘尼西林", "落日飞车",
    "中国摇滚", "中国乐队", "Chinese rock", "Chinese punk",
    "草莓音乐节", "迷笛音乐节", "仙人掌音乐节",
    "Livehouse", "MAO", "Modern Sky", "巡演", "tour",
]

TOUR_KEYWORDS = [
    "中国巡演", "China tour", "中国站", "China dates", "Asia tour",
    "北京站", "上海站", "广州站", "深圳站",
    "coming to China", "first China show", "mainland China",
]

MAJOR_ARTISTS = [
    "Radiohead", "Rage Against the Machine", "Red Hot Chili Peppers",
    "Foo Fighters", "Nirvana", "Metallica", "Iron Maiden",
    "The Rolling Stones", "The Beatles", "Led Zeppelin",
    "U2", "Coldplay", "Muse", "Arctic Monkeys",
    "Green Day", "Linkin Park", "System of a Down",
    "Nine Inch Nails", "Tool", "David Bowie", "Bob Dylan",
    "Oasis", "Blur", "AC/DC", "Guns N Roses", "Queen",
    "Kraftwerk", "The Cure", "The Clash", "Ramones",
    "Sonic Youth", "Pixies", "R.E.M.", "Arcade Fire",
    "Tame Impala", "Kendrick Lamar", "Tyler the Creator",
]

SKIP_KEYWORDS = [
    "美国巡演", "US tour", "Europe tour", "UK tour", "Japan tour",
    "除非", "可能", "传闻", "rumor", " reportedly",
]


class Translator:
    """多翻译源管理器"""

    def __init__(self):
        self.stats = {"libretranslate": 0, "mymemory": 0, "google": 0, "deepl": 0, "failed": 0}
        self.apis = TRANSLATION_APIS

    def translate(self, text):
        """尝试多个翻译源，直到成功"""
        if not text or len(text.strip()) < 5:
            return None

        # 1. 尝试 LibreTranslate（免费，推荐）
        if self.apis["libretranslate"]["enabled"]:
            result = self._translate_libretranslate(text)
            if result:
                self.stats["libretranslate"] += 1
                return result

        # 2. 尝试 MyMemory（免费，免注册）
        if self.apis["mymemory"]["enabled"]:
            result = self._translate_mymemory(text)
            if result:
                self.stats["mymemory"] += 1
                return result

        # 3. 尝试 Google（需要 API Key）
        if self.apis["google"]["enabled"] and self.apis["google"]["api_key"]:
            result = self._translate_google(text)
            if result:
                self.stats["google"] += 1
                return result

        # 4. 尝试 DeepL（需要 API Key）
        if self.apis["deepl"]["enabled"] and self.apis["deepl"]["api_key"]:
            result = self._translate_deepl(text)
            if result:
                self.stats["deepl"] += 1
                return result

        self.stats["failed"] += 1
        return None

    def _translate_libretranslate(self, text):
        """LibreTranslate - 免费开源翻译"""
        try:
            url = self.apis["libretranslate"]["url"]
            params = {
                "q": text[:500],
                "source": "en",
                "target": "zh",
                "format": "text"
            }
            if self.apis["libretranslate"]["api_key"]:
                params["api_key"] = self.apis["libretranslate"]["api_key"]

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
        """MyMemory - 免费翻译 API"""
        try:
            url = self.apis["mymemory"]["url"]
            params = {
                "q": text[:500],
                "langpair": "en|zh"
            }
            if self.apis["mymemory"]["api_key"]:
                params["key"] = self.apis["mymemory"]["api_key"]

            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                result = response.json()
                translated = result.get("responseData", {}).get("translatedText", "").strip()
                # MyMemory 有时返回错误信息
                if translated and "MYMEMORY" not in translated and translated.lower() != text.lower():
                    return translated
        except Exception as e:
            print(f"      ⚠️ MyMemory 失败: {e}")
        return None

    def _translate_google(self, text):
        """Google Cloud Translation"""
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "q": text[:500],
                "target": "zh-TW",
                "key": self.apis["google"]["api_key"]
            }
            response = requests.post(url, data=params, timeout=15)
            if response.status_code == 200:
                translated = response.json()["data"]["translations"][0]["translatedText"]
                translated = translated.strip()
                if translated.lower() != text.lower():
                    return translated
        except Exception as e:
            print(f"      ⚠️ Google 失败: {e}")
        return None

    def _translate_deepl(self, text):
        """DeepL Translation"""
        try:
            url = "https://api-free.deepl.com/v2/translate"
            headers = {"Authorization": f"DeepL-Auth-Key {self.apis['deepl']['api_key']}"}
            data = {
                "text": text[:500],
                "target_lang": "ZH",
                "source_lang": "EN"
            }
            response = requests.post(url, headers=headers, data=data, timeout=15)
            if response.status_code == 200:
                translated = response.json()["translations"][0]["text"].strip()
                if translated.lower() != text.lower():
                    return translated
        except Exception as e:
            print(f"      ⚠️ DeepL 失败: {e}")
        return None


class NewsFetcher:
    def __init__(self, source_type="china", limit=15):
        self.notion = Client(auth=NOTION_TOKEN)
        self.translator = Translator()
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0}
        self.articles = []

    def fetch_all(self):
        print("\n" + "="*70)
        print("🎸 ChineseRocks 新闻抓取系统 v4.1")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   模式: {self.source_type.upper()} | 限制: {self.limit} 条/源")
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

            if hasattr(feed, 'status') and feed.status != 200:
                print(f"   ⚠️ HTTP {feed.status}")
                return

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
        summary = self._clean_html(summary)

        is_domestic = self.source_type == "china"

        return {
            "title": entry.get('title', ''),
            "link": entry.get('link', ''),
            "summary": summary[:1000],
            "published": published,
            "source_name": source['name'],
            "is_domestic": is_domestic,
            "source_url": source['url']
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
        title = article['title'].lower()
        is_domestic = article['is_domestic']

        if any(kw.lower() in text for kw in SKIP_KEYWORDS):
            return {"keep": False, "category": "SKIP", "tags": []}

        if is_domestic:
            tags = self._auto_tag(text)
            return {"keep": True, "category": "DOMESTIC", "tags": tags}

        if any(kw.lower() in text for kw in TOUR_KEYWORDS):
            tags = self._auto_tag(text, is_tour=True)
            return {"keep": True, "category": "CHINA_TOUR", "tags": tags}

        if any(kw.lower() in text for kw in [k.lower() for k in CHINA_KEYWORDS]):
            tags = self._auto_tag(text)
            return {"keep": True, "category": "CHINA_RELATED", "tags": tags}

        for artist in MAJOR_ARTISTS:
            if artist.lower() in title:
                if any(kw in text for kw in ['asia', 'asian', 'world', 'global', 'tour']):
                    tags = self._auto_tag(text, is_major=True)
                    return {"keep": True, "category": "MAJOR_ARTIST", "tags": tags}
                break

        return {"keep": False, "category": "FILTERED", "tags": []}

    def _auto_tag(self, text, is_tour=False, is_major=False):
        tags = []
        if is_tour:
            tags.append("来华演出")

        if any(w in text for w in ['朋克', 'punk']): tags.append("朋克")
        if any(w in text for w in ['独立', 'indie']): tags.append("独立")
        if any(w in text for w in ['金属', 'metal']): tags.append("金属")
        if any(w in text for w in ['民谣', 'folk']): tags.append("民谣")
        if any(w in text for w in ['电子', 'electronic']): tags.append("电子")
        if any(w in text for w in ['后摇', 'post-rock']): tags.append("后摇")
        if any(w in text for w in ['实验', 'experimental']): tags.append("实验")

        if any(w in text for w in ['音乐节', 'festival']): tags.append("音乐节")
        elif any(w in text for w in ['巡演', 'tour']): tags.append("巡演")
        elif any(w in text for w in ['专辑', 'album', 'ep']): tags.append("新专辑")
        elif any(w in text for w in ['专访', 'interview']): tags.append("专访")

        cities = ["北京", "上海", "广州", "深圳", "成都", "西安", "杭州", "南京", "武汉"]
        for city in cities:
            if city in text:
                tags.append(city)
                break

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
            article_id = self._generate_id(article['link'])

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

    def _generate_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()[:16]

    def _check_exists(self, article_id):
        try:
            response = self.notion.databases.query(
                database_id=NEWS_DB_ID,
                filter={"property": "来源", "url": {"contains": article_id}}
            )
            return len(response['results']) > 0
        except Exception as e:
            print(f"   ⚠️ 检查存在性失败: {e}")
            return False

    def _add_to_notion(self, article, article_id):
        try:
            prefixes = {
                "CHINA_TOUR": "【来华】",
                "MAJOR_ARTIST": "【国际】",
                "DOMESTIC": "",
                "CHINA_RELATED": ""
            }
            prefix = prefixes.get(article['category'], "")
            title = f"{prefix}{article['processed_title']}"[:150]

            type_map = {
                "CHINA_TOUR": "演出预告",
                "DOMESTIC": "新闻",
                "CHINA_RELATED": "新闻",
                "MAJOR_ARTIST": "新闻"
            }

            self.notion.pages.create(
                parent={"database_id": NEWS_DB_ID},
                properties={
                    "标题": {"title": [{"text": {"content": title}}]},
                    "内容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                    "标签": {"multi_select": [{"name": tag} for tag in article['tags']]},
                    "状态": {"select": {"name": "待审核"}},
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
        if self.source_type == "international":
            print("-"*70)
            print(f"   翻译统计:")
            for api, count in self.translator.stats.items():
                if count > 0:
                    print(f"     {api}: {count} 次")
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
        "translation": fetcher.translator.stats if args.source == "international" else {},
        "timestamp": datetime.now().isoformat()
    }
    with open("fetch_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已保存到 fetch_result.json")


if __name__ == "__main__":
    main()
