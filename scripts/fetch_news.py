#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 新闻抓取脚本 v11.0.0 - 智能去重增强版
- 优化：相似度阈值提升至88%，大幅减少国际新闻重复
- 优化：改进内容指纹算法，提取关键词而非简单截断
- 优化：跨运行持久化去重，查询Notion已有文章
- 新增：恢复街声中国源，增加国内内容量
- 新增：增加更多国内优质源
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from difflib import SequenceMatcher
import feedparser
import requests
from notion_client import Client
from bs4 import BeautifulSoup

# Cloudinary 配置
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

# 日期過濾設定 - 只抓取近15天內的新聞
DAYS_LIMIT = 15

# 内容去重配置 - v11优化：提高阈值到88%
SIMILARITY_THRESHOLD = 0.88  # 从0.75提高到0.88
MIN_CONTENT_LENGTH = 50

# 嚴格搖滾風格分類
MUSIC_GENRES = {
    "PUNK & HARDCORE": {
        "keywords": ["punk", "朋克", "hardcore", "硬核", "emo", "screamo", "post-hardcore", "oi", "crust", "street punk"],
        "weight": 10
    },
    "HEAVY & METAL": {
        "keywords": ["metal", "金屬", "heavy", "thrash", "death metal", "black metal", "doom", "sludge", "stoner", "grindcore", "nu metal"],
        "weight": 10
    },
    "INDIE & ALTERNATIVE": {
        "keywords": ["indie", "獨立", "alternative", "另類", "lo-fi", "shoegaze", "dream pop", "britpop", "grunge", "indie rock"],
        "weight": 9
    },
    "SKA & REGGAE": {
        "keywords": ["ska", "reggae", "雷鬼", "dub", "rocksteady", "ska-punk", "two-tone"],
        "weight": 8
    },
    "GARAGE & PSYCHEDELIC": {
        "keywords": ["garage", "車庫", "psychedelic", "迷幻", "space rock", "krautrock", "acid rock"],
        "weight": 7
    },
    "FOLK & ROOTS ROCK": {
        "keywords": ["folk", "民謠", "roots", "country rock", "americana", "bluegrass", "blues rock", "southern rock"],
        "weight": 7
    },
    "ART & EXPERIMENTAL": {
        "keywords": ["experimental", "實驗", "avant-garde", "noise", "post-rock", "後搖", "math rock", "prog", "progressive"],
        "weight": 6
    },
    "ROCK 通用": {
        "keywords": ["rock", "搖滾", "band", "樂隊", "guitar", "吉他", "bass", "drum", "live", "演出", "concert", "tour"],
        "weight": 5
    }
}

# 嚴格排除所有非搖滾音樂
EXCLUDE_GENRES = [
    "k-pop", "j-pop", "c-pop", "mandopop", "cantopop", 
    "pop music", "teen pop", "synth-pop", "electropop", "bubblegum pop",
    "hip-hop", "rap", "trap", "drill", "r&b", "soul", "funk", "disco", "neo-soul",
    "edm", "electronic", "house", "techno", "trance", "dubstep", 
    "drum and bass", "dnb", "ambient", "idm", "glitch", "synthwave",
    "classical", "opera", "jazz", "new age", "world music", "new wave",
    "acoustic pop", "folk pop", "indie pop"
]

# v11.0.0 优化版 RSS 源配置
# 变更：
# 1. 恢复街声中国源（低优先级）
# 2. 增加新的国内源
# 3. 国际源保持精简，依赖高阈值去重
SOURCES = {
    "china": [
        # ✅ 核心源1：豆瓣音乐-乐评
        {
            "name": "豆瓣音樂-樂評", 
            "url": "https://rsshub.app/douban/music/latest", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 9
        },
        # ✅ 核心源2：Live China Music
        {
            "name": "Live China Music-獨立音樂現場", 
            "url": "https://livechinamusic.com/feed", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 9
        },
        # ✅ 核心源3：Wooozy
        {
            "name": "Wooozy-地下音樂", 
            "url": "https://wooozy.cn/feed", 
            "enabled": True, 
            "category": "新聞",
            "priority": 2,
            "quality_score": 8
        },
        # ✅ 恢复：街声中国（低优先级，不与台湾重复）
        {
            "name": "街聲-中國獨立音樂", 
            "url": "https://streetvoice.cn/feed/", 
            "enabled": True,
            "category": "新聞",
            "priority": 3,
            "quality_score": 6
        },
        # ⚠️ 降级：摩登天空
        {
            "name": "摩登天空-網易號", 
            "url": "https://rsshub.app/163/dy/T1509089140270", 
            "enabled": True, 
            "category": "新聞",
            "priority": 3,
            "quality_score": 6
        },
        # 🆕 新增：知乎摇滚乐话题
        {
            "name": "知乎-搖滾樂話題", 
            "url": "https://rsshub.app/zhihu/topic/19550718", 
            "enabled": True,
            "category": "新聞",
            "priority": 3,
            "quality_score": 6
        },
        # 🆕 新增：知乎独立音乐话题
        {
            "name": "知乎-獨立音樂話題", 
            "url": "https://rsshub.app/zhihu/topic/19550408", 
            "enabled": True,
            "category": "新聞",
            "priority": 3,
            "quality_score": 6
        },
        # 🆕 新增： solidot 文化板块（摇滚相关内容）
        {
            "name": "Solidot-文化", 
            "url": "https://rsshub.app/solidot/culture", 
            "enabled": True,
            "category": "新聞",
            "priority": 4,
            "quality_score": 5
        },
        # ❌ 禁用：音乐财经 - 待验证
        {
            "name": "音樂財經-產業新聞", 
            "url": "https://rsshub.app/musicbusinessworldwide", 
            "enabled": False,
            "category": "新聞",
            "priority": 3,
            "quality_score": 7
        },
    ],

    "taiwan": [
        # ✅ 核心源1：深晨 DOPM
        {
            "name": "深晨DOPM", 
            "url": "https://deepperfectmorning.com/blog?format=rss", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 10
        },
        # ✅ 核心源2：Blow 吹音樂-人物
        {
            "name": "Blow吹音樂-人物", 
            "url": "https://blow.streetvoice.com/c/people/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 9
        },
        # ✅ 核心源3：Blow 吹音樂-議題
        {
            "name": "Blow吹音樂-議題", 
            "url": "https://blow.streetvoice.com/c/issue/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 2,
            "quality_score": 8
        },
        # ⚠️ 降级：小明拆台
        {
            "name": "小明拆台MingStrike", 
            "url": "https://mingstrike.com/feed/audio.xml", 
            "enabled": True, 
            "category": "新聞",
            "priority": 3,
            "quality_score": 7
        },
    ],

    "hongkong": [
        # ⚠️ 香港源较少
        {
            "name": "HKFP-文化", 
            "url": "https://hongkongfp.com/culture/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 2,
            "quality_score": 6
        },
    ],

    "international": [
        # ✅ Tier 1：Pitchfork
        {
            "name": "Pitchfork", 
            "url": "https://pitchfork.com/rss/news", 
            "enabled": True, 
            "category": "國際",
            "priority": 1,
            "quality_score": 10
        },
        # ✅ Tier 1：Rolling Stone
        {
            "name": "Rolling Stone", 
            "url": "https://www.rollingstone.com/music/feed/", 
            "enabled": True, 
            "category": "國際",
            "priority": 1,
            "quality_score": 9
        },
        # ✅ Tier 2：NME
        {
            "name": "NME", 
            "url": "https://www.nme.com/news/music/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 2,
            "quality_score": 8
        },
        # ✅ Tier 2：Kerrang
        {
            "name": "Kerrang", 
            "url": "https://www.kerrang.com/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 2,
            "quality_score": 9
        },
        # ⚠️ 降级：Stereogum
        {
            "name": "Stereogum", 
            "url": "https://www.stereogum.com/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 3,
            "quality_score": 8
        },
    ],

    "test": [
        # 測試模式使用獨立源
        {
            "name": "深晨DOPM-測試", 
            "url": "https://deepperfectmorning.com/blog?format=rss", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 10
        },
    ]
}


class ContentDeduplicator:
    """v11优化版内容去重器 - 88%阈值 + 关键词指纹 + 持久化去重"""

    def __init__(self, threshold=SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self.seen_contents = []
        self.seen_urls = set()
        self.existing_titles = set()  # 从Notion加载的已有标题

    def normalize_url(self, url):
        """URL正規化"""
        if not url:
            return ""
        url = re.sub(r'[?&](utm_source|utm_medium|utm_campaign|utm_content|fbclid|gclid)=[^&]*', '', url)
        url = url.rstrip('?')
        url = url.replace('http://', 'https://')
        url = url.replace('https://www.', 'https://')
        return url.lower().strip()

    def create_fingerprint(self, title, summary):
        """v11优化：提取关键词而非简单截断"""
        text = f"{title} {summary}".lower()

        # 提取中文词汇（2-6字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
        # 提取英文单词（4字母以上）
        english_words = re.findall(r'\b[a-z]{4,}\b', text)

        # 组合关键词并去重，取前30个
        keywords = list(dict.fromkeys(chinese_words + english_words))
        return ' '.join(keywords[:30])

    def calculate_similarity(self, text1, text2):
        """计算两段文本的相似度"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def is_duplicate(self, title, summary, url):
        """v11优化：多层次去重检测"""
        # 1. URL去重
        normalized_url = self.normalize_url(url)
        if normalized_url and normalized_url in self.seen_urls:
            return True, "URL重复"

        # 2. 标题快速匹配（去除标点）
        clean_title = re.sub(r'[^\w\u4e00-\u9fa5]', '', title.lower())
        if clean_title in self.existing_titles:
            return True, "Notion中已存在"

        # 3. 内容指纹去重（88%阈值）
        fingerprint = self.create_fingerprint(title, summary)

        for seen_fp, seen_title in self.seen_contents:
            # 标题完全匹配
            if title.lower().strip() == seen_title.lower().strip():
                return True, "标题完全匹配"

            # 指纹相似度检测
            similarity = self.calculate_similarity(fingerprint, seen_fp)
            if similarity >= self.threshold:
                return True, f"内容相似度{similarity:.0%}"

        return False, None

    def add_content(self, title, summary, url):
        """添加内容到已见集合"""
        fingerprint = self.create_fingerprint(title, summary)
        self.seen_contents.append((fingerprint, title))
        normalized_url = self.normalize_url(url)
        if normalized_url:
            self.seen_urls.add(normalized_url)

    def load_existing_from_notion(self, notion_client, db_id, days=7):
        """v11新增：从Notion加载最近N天的文章标题用于去重"""
        try:
            from datetime import datetime, timedelta
            seven_days_ago = (datetime.now() - timedelta(days=days)).isoformat()

            response = notion_client.databases.query(
                database_id=db_id,
                filter={
                    "property": "發布時間",
                    "date": {"after": seven_days_ago}
                }
            )

            for page in response['results']:
                try:
                    title = page['properties']['標題']['title'][0]['text']['content']
                    clean_title = re.sub(r'[^\w\u4e00-\u9fa5]', '', title.lower())
                    self.existing_titles.add(clean_title)
                except:
                    continue

            print(f"  📚 从Notion加载了 {len(self.existing_titles)} 条已有标题用于去重")
            return len(self.existing_titles)
        except Exception as e:
            print(f"  ⚠️ 加载Notion已有标题失败: {e}")
            return 0


class NewsFetcher:
    def __init__(self, source_type="china", limit=5):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {
            "total": 0, "added": 0, "skipped": 0, "exists": 0, 
            "failed": 0, "image_uploaded": 0, "filtered": 0,
            "too_old": 0, "duplicate_content": 0, "low_quality": 0,
            "notion_duplicate": 0  # v11新增：Notion中已存在的数量
        }
        self.articles = []
        self.cloudinary_enabled = all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ])
        self.cutoff_date = datetime.now() - timedelta(days=DAYS_LIMIT)
        self.deduplicator = ContentDeduplicator()

    def fetch_all(self):
        print("\n" + "="*70)
        print("ChineseRocks 新闻抓取系统 v11.0.0 - 智能去重增强版")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"模式: {self.source_type}")
        print(f"每源限制: {self.limit} 条")
        print(f"日期限制: 近{DAYS_LIMIT}天內 (截止: {self.cutoff_date.strftime('%Y-%m-%d')})")
        print(f"相似度阈值: {SIMILARITY_THRESHOLD:.0%} (v11优化)")
        print(f"Cloudinary: {'已啟用' if self.cloudinary_enabled else '未啟用'}")
        print("="*70)

        # v11新增：加载Notion已有标题进行跨运行去重
        if NOTION_TOKEN:
            self.deduplicator.load_existing_from_notion(self.notion, NEWS_DB_ID, days=7)

        sources = SOURCES.get(self.source_type, [])
        enabled_sources = [s for s in sources if s["enabled"]]
        enabled_sources.sort(key=lambda x: x.get("priority", 99))

        print(f"\n抓取 {len(enabled_sources)} 個精選搖滾音樂源 (已按优先级排序)")
        print("-"*50)

        for source in sources:
            if not source["enabled"]:
                reason = source.get("reason", "已禁用")
                print(f"[{source['name']}] ⚠️ {reason}")
                continue
            self._fetch_source(source)

        print(f"\n抓取完成: 共 {len(self.articles)} 条")
        print(f"  - 内容去重过滤: {self.stats['duplicate_content']} 条")
        print(f"  - Notion已存在: {self.stats['notion_duplicate']} 条")
        print(f"  - 低质量过滤: {self.stats['low_quality']} 条")
        print(f"  - 非搖滾过滤: {self.stats['filtered']} 条")
        print(f"  - 過期文章(>{DAYS_LIMIT}天): {self.stats['too_old']} 条")
        return self.articles

    def _fetch_source(self, source):
        try:
            priority = source.get("priority", 3)
            quality = source.get("quality_score", 5)
            print(f"[{source['name']}] (优先级:{priority}, 质量分:{quality})")

            feed = feedparser.parse(source['url'])

            if not feed.entries:
                print(f"  ⚠️ 無法獲取 RSS 內容或源無效")
                return

            count = 0
            filtered_count = 0
            too_old_count = 0
            duplicate_count = 0
            notion_dup_count = 0
            low_quality_count = 0

            for entry in feed.entries:
                if count >= self.limit:
                    break

                # 檢查日期
                published_date = self._parse_date(entry)
                if published_date:
                    try:
                        pub_dt = datetime.strptime(published_date, "%Y-%m-%d")
                        if pub_dt < self.cutoff_date:
                            too_old_count += 1
                            continue
                    except:
                        pass

                # 内容质量检查
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                summary = self._clean_html(summary)

                if len(summary) < MIN_CONTENT_LENGTH:
                    low_quality_count += 1
                    continue

                # v11优化：多层次去重检查
                link = entry.get('link', '')
                is_dup, dup_reason = self.deduplicator.is_duplicate(title, summary, link)
                if is_dup:
                    if "Notion中已存在" in dup_reason:
                        notion_dup_count += 1
                    else:
                        duplicate_count += 1
                    print(f"    🔄 跳过重复: {dup_reason} - {title[:30]}...")
                    continue

                # 摇滚风格检测
                genres = self._detect_genres(entry)
                if not genres:
                    filtered_count += 1
                    continue

                article = self._parse_entry(entry, source, genres)
                if article:
                    self.deduplicator.add_content(
                        article['title'], 
                        article['summary'], 
                        article['link']
                    )
                    self.articles.append(article)
                    count += 1

            print(f"  ✅ 成功獲取 {count} 条 (去重 {duplicate_count}, Notion已存在 {notion_dup_count}, 低质量 {low_quality_count}, 风格过滤 {filtered_count}, 过期 {too_old_count})")
            self.stats["duplicate_content"] += duplicate_count
            self.stats["notion_duplicate"] += notion_dup_count
            self.stats["low_quality"] += low_quality_count
            self.stats["filtered"] += filtered_count
            self.stats["too_old"] += too_old_count

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            self.stats["failed"] += 1

    def _detect_genres(self, entry):
        """嚴格檢測文章音樂風格"""
        title = entry.get('title', '').lower()
        summary = entry.get('summary', entry.get('description', '')).lower()
        text = f"{title} {summary}"

        for exclude in EXCLUDE_GENRES:
            if exclude in text:
                return []

        matched_genres = []
        for genre_name, genre_info in MUSIC_GENRES.items():
            for keyword in genre_info["keywords"]:
                if keyword.lower() in text:
                    matched_genres.append((genre_name, genre_info["weight"]))
                    break

        matched_genres.sort(key=lambda x: x[1], reverse=True)
        return [g[0] for g in matched_genres[:3]]

    def _parse_entry(self, entry, source, genres):
        try:
            summary = entry.get('summary', entry.get('description', ''))
            summary = self._clean_html(summary)

            published = self._parse_date(entry)
            image = self._extract_image_improved(entry, source)

            if image and self.cloudinary_enabled:
                print(f"    📤 上傳圖片...")
                image = self._upload_to_cloudinary(image, source['name'])
                if image:
                    self.stats["image_uploaded"] += 1

            unique_id = hashlib.md5(
                f"{source['name']}_{entry.get('title', '')}".encode()
            ).hexdigest()[:12]

            return {
                "id": unique_id,
                "title": entry.get('title', '')[:200],
                "link": entry.get('link', ''),
                "summary": summary[:1000],
                "source_name": source['name'],
                "category": source.get('category', '新聞'),
                "published": published,
                "image": image,
                "genres": genres
            }
        except Exception as e:
            print(f"    解析條目失敗: {e}")
            return None

    def _extract_image_improved(self, entry, source):
        """優化圖片提取邏輯"""
        try:
            if 'media_content' in entry:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        return media.get('url', '')
                    if media.get('url'):
                        return media['url']

            if 'media_thumbnail' in entry and entry.media_thumbnail:
                return entry.media_thumbnail[0].get('url', '')

            if 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image/'):
                        return enc.get('href', '')

            content = entry.get('content', [{}])[0].get('value', '') if 'content' in entry else                       entry.get('summary', entry.get('description', ''))

            if content:
                soup = BeautifulSoup(content, 'html.parser')
                img = soup.find('img')
                if img:
                    img_url = img.get('src', '')
                    if img_url and img_url.startswith('/'):
                        link = entry.get('link', '')
                        if link:
                            from urllib.parse import urljoin
                            img_url = urljoin(link, img_url)
                    return img_url

            source_name = source.get('name', '').lower()
            if 'blow' in source_name or 'dopm' in source_name or '深晨' in source_name:
                if 'description' in entry:
                    soup = BeautifulSoup(entry.description, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        return img['src']

        except Exception as e:
            print(f"    圖片提取失敗: {e}")

        return ''

    def _upload_to_cloudinary(self, image_url, source_name):
        try:
            image_url = image_url.strip()
            if not image_url.startswith(('http://', 'https://')):
                return None

            public_id = f"chineserocks/{source_name}_{hashlib.md5(image_url.encode()).hexdigest()[:12]}"

            result = cloudinary.uploader.upload(
                image_url,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                folder="chineserocks"
            )

            print(f"    ✅ 上傳成功")
            return result['secure_url']

        except Exception as e:
            print(f"    ⚠️ 上傳失敗: {e}")
            return image_url

    def _parse_date(self, entry):
        try:
            date_str = entry.get('published', entry.get('updated', entry.get('pubDate', '')))
            if date_str:
                dt = date_parser.parse(date_str)
                return dt.strftime("%Y-%m-%d")
            else:
                return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")

    def _clean_html(self, html):
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def sync_to_notion(self):
        if not self.articles:
            print("\n沒有文章需要同步")
            return 0

        print("\n同步到 Notion")
        print("-"*50)

        added = 0
        exists = 0
        failed = 0

        for article in self.articles:
            result = self._add_to_notion(article)
            if result == "added":
                added += 1
                print(f"  ✅ {article['title'][:40]}... [{', '.join(article['genres'][:2])}]")
            elif result == "exists":
                exists += 1
                print(f"  ⏭️ 已存在: {article['title'][:30]}...")
            else:
                failed += 1
                print(f"  ❌ 失敗: {article['title'][:30]}...")

        self.stats["added"] = added
        self.stats["exists"] = exists
        self.stats["failed"] = failed
        return added

    def _add_to_notion(self, article):
        try:
            if self._check_exists_http(article['title']):
                return "exists"

            tags = [{"name": "新聞"}, {"name": article['source_name']}]

            for genre in article.get('genres', []):
                if genre != "ROCK 通用":
                    tags.append({"name": genre})

            if article['category'] == "國際":
                tags.append({"name": "國際"})

            properties = {
                "標題": {"title": [{"text": {"content": article['title'][:150]}}]},
                "內容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                "狀態": {"select": {"name": "待審核"}},
                "類型": {"select": {"name": article['category']}},
                "標籤": {"multi_select": tags},
                "來源": {"url": article['link']} if article['link'] else {"url": None},
                "發布時間": {"date": {"start": article['published']}},
                "AI生成": {"checkbox": False},
                "是否會員專享": {"checkbox": False},
            }

            if article['image']:
                properties["封面圖"] = {
                    "files": [{"name": "cover", "external": {"url": article['image']}}]
                }

            self.notion.pages.create(
                parent={"database_id": NEWS_DB_ID},
                properties=properties
            )
            return "added"

        except Exception as e:
            error_msg = str(e)
            if "token" in error_msg.lower() or "unauthorized" in error_msg.lower():
                print(f"    🔴 Notion API Token 無效，請檢查 Secrets 設置")
            else:
                print(f"    錯誤: {e}")
            return "failed"

    def _check_exists_http(self, title):
        try:
            import urllib.request
            url = f"https://api.notion.com/v1/databases/{NEWS_DB_ID}/query"
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            data = {"filter": {"property": "標題", "title": {"equals": title[:100]}}}
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return len(result.get('results', [])) > 0
        except:
            return False

    def print_report(self):
        print("\n" + "="*70)
        print("執行報告")
        print("="*70)
        print(f"總抓取: {len(self.articles)} 条")
        print(f"圖片上傳: {self.stats['image_uploaded']} 张")
        print(f"新增入庫: {self.stats['added']} 条")
        print(f"已存在: {self.stats['exists']} 条")
        print(f"失敗: {self.stats['failed']} 条")
        print("-"*70)
        print(f"过滤统计:")
        print(f"  - 内容去重: {self.stats['duplicate_content']} 条")
        print(f"  - Notion已存在: {self.stats['notion_duplicate']} 条")
        print(f"  - 低质量: {self.stats['low_quality']} 条")
        print(f"  - 非搖滾: {self.stats['filtered']} 条")
        print(f"  - 過期(>{DAYS_LIMIT}天): {self.stats['too_old']} 条")
        print("="*70)

        if self.articles:
            print("\n風格分佈:")
            genre_count = {}
            for article in self.articles:
                for genre in article.get('genres', []):
                    genre_count[genre] = genre_count.get(genre, 0) + 1
            for genre, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  {genre}: {count} 条")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='test', 
                       choices=['china', 'taiwan', 'hongkong', 'international', 'test'])
    parser.add_argument('--limit', type=int, default=5, help='每源抓取數量')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("🔴 錯誤: NOTION_TOKEN 未設置")
        print("請在 GitHub Secrets 中設置 NOTION_TOKEN")
        sys.exit(1)

    fetcher = NewsFetcher(source_type=args.source, limit=args.limit)
    fetcher.fetch_all()

    if fetcher.articles:
        fetcher.sync_to_notion()

    fetcher.print_report()


if __name__ == "__main__":
    main()
