// news-loader.js - ChineseRocks 新聞加載器 (修復版)
// 功能：從 data/news.json 加載新聞

(function() {
    'use strict';

    const PRIORITY_TAGS = [
        'TheNoname', '無名', '無名樂隊', 'THE NONAME',
        'PUNK', 'Punk', 'punk', 'PUNK & HARDCORE',
        '龐克', '庞克', '硬核', 'Hardcore'
    ];

    const PRIORITY_CLASS = 'priority-tag';
    let newsData = [];
    let allNewsData = null; // 保存完整數據結構

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        console.log('[NewsLoader] 初始化...');
        loadNewsData();
    }

    async function loadNewsData() {
        try {
            // 修復：嘗試多個可能的數據路徑
            const possiblePaths = [
                'data/news.json',
                './data/news.json',
                '../data/news.json',
                '/data/news.json'
            ];

            let response = null;
            let lastError = null;

            for (const path of possiblePaths) {
                try {
                    const timestamp = Date.now();
                    console.log(`[NewsLoader] 嘗試加載: ${path}?t=${timestamp}`);
                    response = await fetch(`${path}?t=${timestamp}`);
                    if (response.ok) {
                        console.log(`[NewsLoader] 成功從 ${path} 加載`);
                        break;
                    }
                } catch (e) {
                    lastError = e;
                    console.log(`[NewsLoader] ${path} 失敗: ${e.message}`);
                }
            }

            if (!response || !response.ok) {
                throw new Error('所有路徑都失敗: ' + (lastError?.message || 'Unknown'));
            }

            const jsonData = await response.json();
            console.log('[NewsLoader] 原始數據結構:', Object.keys(jsonData));

            // 保存完整數據
            allNewsData = jsonData;

            // 修復：支持多種數據格式
            if (jsonData.data) {
                // 新格式: { data: { all: [...], by_category: {...} } }
                newsData = jsonData.data.all || jsonData.data.latest || [];
                console.log('[NewsLoader] 使用 data.all 格式, 數量:', newsData.length);
            } else if (Array.isArray(jsonData)) {
                // 舊格式: 直接數組
                newsData = jsonData;
                console.log('[NewsLoader] 使用數組格式, 數量:', newsData.length);
            } else if (jsonData.all || jsonData.latest) {
                // 混合格式
                newsData = jsonData.all || jsonData.latest;
                console.log('[NewsLoader] 使用混合格式, 數量:', newsData.length);
            } else {
                console.warn('[NewsLoader] 未知的數據格式:', jsonData);
                newsData = [];
            }

            if (newsData.length > 0) {
                processAndRenderNews();
            } else {
                console.warn('[NewsLoader] 沒有新聞數據');
                showNoDataMessage();
            }
        } catch (error) {
            console.error('[NewsLoader] 錯誤:', error);
            showErrorMessage(error.message);
        }
    }

    function processAndRenderNews() {
        console.log('[NewsLoader] 開始渲染, 文章數:', newsData.length);

        // 按优先级排序
        const sortedNews = sortByPriority(newsData);

        // 分离头条和普通新闻
        // 修復：從 allNewsData.data.hero 獲取頭條，如果沒有則使用featured標記
        let heroNews = [];
        if (allNewsData?.data?.hero && allNewsData.data.hero.length > 0) {
            heroNews = allNewsData.data.hero;
            console.log('[NewsLoader] 使用數據中的hero, 數量:', heroNews.length);
        } else {
            heroNews = sortedNews.filter(n => n.featured || n.isHero || n.is_featured).slice(0, 3);
            if (heroNews.length === 0) {
                heroNews = sortedNews.slice(0, 3); // 如果沒有標記，取最新的3篇
            }
            console.log('[NewsLoader] 自動選擇hero, 數量:', heroNews.length);
        }

        const heroIds = heroNews.map(h => h.id);
        const normalNews = sortedNews.filter(n => !heroIds.includes(n.id));

        console.log('[NewsLoader] Hero:', heroNews.length, '篇, Normal:', normalNews.length, '篇');

        // 渲染
        if (heroNews.length > 0) {
            renderHeroSection(heroNews);
        }
        renderNewsList(normalNews);
        generateHotTags(sortedNews);
    }

    function sortByPriority(articles) {
        return [...articles].sort((a, b) => {
            const aPriority = hasPriorityTag(a) ? 1 : 0;
            const bPriority = hasPriorityTag(b) ? 1 : 0;
            if (aPriority !== bPriority) {
                return bPriority - aPriority;
            }
            // 按日期排序
            const dateA = new Date(b.published_date || b.created_time || 0);
            const dateB = new Date(a.published_date || a.created_time || 0);
            return dateA - dateB;
        });
    }

    function hasPriorityTag(article) {
        const text = (article.title + ' ' + (article.tags || []).join(' ')).toLowerCase();
        return PRIORITY_TAGS.some(tag => text.includes(tag.toLowerCase()));
    }

    function renderHeroSection(heroNews) {
        const heroMain = document.querySelector('.hero-main');
        const heroSide = document.querySelector('.hero-side');

        if (!heroMain || !heroSide) {
            console.warn('[NewsLoader] 找不到hero容器');
            return;
        }

        // 主头条
        if (heroNews[0]) {
            const main = heroNews[0];
            const coverImage = main.cover_image || main.cover || 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1280&h=800&fit=crop';

            heroMain.innerHTML = `
                <img src="${coverImage}" alt="${escapeHtml(main.title)}" 
                     onerror="this.src='https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1280&h=800&fit=crop'">
                <div class="hero-overlay">
                    <span class="hero-tag ${main.category || 'exclusive'} ${hasPriorityTag(main) ? PRIORITY_CLASS : ''}">
                        ${main.tags && main.tags[0] ? main.tags[0] : (main.category || '獨家')}
                    </span>
                    <h2 class="hero-title">${escapeHtml(main.title)}</h2>
                    <p class="hero-excerpt">${main.content ? main.content.substring(0, 100) + '...' : ''}</p>
                    <div class="hero-meta">
                        <span>${formatDate(main.published_date)}</span>
                        ${main.is_premium || main.isPremium ? '<span>★ 會員專享</span>' : ''}
                    </div>
                </div>
            `;
            heroMain.onclick = () => handleArticleClick(main);
            console.log('[NewsLoader] 已渲染主頭條:', main.title);
        }

        // 侧边头条
        heroSide.innerHTML = heroNews.slice(1, 3).map(news => {
            const coverImage = news.cover_image || news.cover || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&h=450&fit=crop';
            return `
            <article class="side-card" data-id="${news.id}">
                <img src="${coverImage}" alt="${escapeHtml(news.title)}"
                     onerror="this.src='https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&h=450&fit=crop'">
                <div class="side-overlay">
                    <span class="side-tag ${hasPriorityTag(news) ? PRIORITY_CLASS : ''}">${news.tags && news.tags[0] ? news.tags[0] : (news.category || '新聞')}</span>
                    <h3 class="side-title">${escapeHtml(news.title)}</h3>
                </div>
            </article>
        `}).join('');

        heroSide.querySelectorAll('.side-card').forEach((card, idx) => {
            card.onclick = () => handleArticleClick(heroNews[idx + 1]);
        });
    }

    function renderNewsList(news) {
        const newsList = document.getElementById('newsList');
        if (!newsList) {
            console.warn('[NewsLoader] 找不到newsList容器');
            return;
        }

        // 保留加載更多按鈕
        const loadMore = newsList.querySelector('.load-more');

        // 清除現有新聞卡片（保留加載更多）
        newsList.querySelectorAll('.news-card').forEach(card => card.remove());

        if (news.length === 0) {
            const noData = document.createElement('div');
            noData.className = 'no-data-message';
            noData.innerHTML = '<p style="text-align:center;padding:2rem;color:#666;">暫無新聞</p>';
            newsList.insertBefore(noData, loadMore);
            return;
        }

        news.forEach(item => {
            const card = createNewsCard(item);
            newsList.insertBefore(card, loadMore);
        });

        console.log('[NewsLoader] 已渲染新聞列表:', news.length, '篇');
    }

    function createNewsCard(news) {
        const isPremium = news.is_premium || news.isPremium || news.memberOnly;
        const card = document.createElement('article');
        card.className = `news-card ${isPremium ? 'premium' : ''}`;
        card.dataset.id = news.id;
        card.dataset.category = news.category || 'all';

        const coverImage = news.cover_image || news.cover || 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=560&h=350&fit=crop';

        card.innerHTML = `
            <div class="news-thumb">
                <img src="${coverImage}" alt="${escapeHtml(news.title)}" loading="lazy"
                     onerror="this.src='https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=560&h=350&fit=crop'">
            </div>
            <div class="news-content">
                <span class="news-category ${hasPriorityTag(news) ? PRIORITY_CLASS : ''}">
                    ${news.category || (news.tags && news.tags[0]) || '新聞'}
                    ${hasPriorityTag(news) ? ' ★' : ''}
                </span>
                <h3 class="news-title">${escapeHtml(news.title)}</h3>
                <p class="news-excerpt">${news.content ? news.content.substring(0, 80) + '...' : ''}</p>
                <div class="news-footer">
                    <div class="news-meta">
                        <span>${formatDate(news.published_date)}</span>
                        ${isPremium ? '<span style="color: #B8860B; font-weight: 700;">★ 會員專享</span>' : ''}
                    </div>
                    <div class="news-actions">
                        <button class="action-btn" onclick="event.stopPropagation(); toggleFav(this, '${escapeHtml(news.title)}')">☆</button>
                        <button class="action-btn" onclick="event.stopPropagation(); shareArticle('${escapeHtml(news.title)}')">↗</button>
                    </div>
                </div>
            </div>
        `;

        card.onclick = () => handleArticleClick(news);
        return card;
    }

    function generateHotTags(articles) {
        const tagCloud = document.getElementById('tagCloud');
        if (!tagCloud) return;

        const tagCount = {};
        articles.forEach(article => {
            (article.tags || []).forEach(tag => {
                if (tag) tagCount[tag] = (tagCount[tag] || 0) + 1;
            });
        });

        const hotTags = Object.entries(tagCount)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 12)
            .map(([tag]) => tag);

        const priorityDisplayTags = ['TheNoname無名', '龐克', '迷笛音樂節'];
        const finalTags = [...new Set([...priorityDisplayTags, ...hotTags])].slice(0, 12);

        tagCloud.innerHTML = finalTags.map(tag => {
            const isPriority = PRIORITY_TAGS.some(pt => tag.toLowerCase().includes(pt.toLowerCase()));
            return `<button class="tag-item ${isPriority ? PRIORITY_CLASS : ''}" onclick="filterByTag('${escapeHtml(tag)}')">#${escapeHtml(tag)}</button>`;
        }).join('');
    }

    function handleArticleClick(article) {
        console.log('[NewsLoader] 點擊文章:', article.title);
        window.location.href = `article.html?id=${article.id}&title=${encodeURIComponent(article.title)}`;
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
        } catch (e) {
            return dateStr;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showNoDataMessage() {
        const newsList = document.getElementById('newsList');
        if (newsList) {
            newsList.innerHTML = '<div style="text-align:center;padding:3rem;color:#666;"><p>暫無新聞數據</p><p style="font-size:0.9rem;margin-top:0.5rem;">請檢查 data/news.json 是否存在</p></div>';
        }
    }

    function showErrorMessage(msg) {
        const newsList = document.getElementById('newsList');
        if (newsList) {
            newsList.innerHTML = `<div style="text-align:center;padding:3rem;color:#FF0066;"><p>加載失敗</p><p style="font-size:0.9rem;margin-top:0.5rem;">${escapeHtml(msg)}</p></div>`;
        }
    }

    // 修復：重寫全局filterNews函數
    window.filterNews = function(category, btnElement) {
        console.log('[NewsLoader] 篩選分類:', category);

        // 更新按鈕狀態
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        if (btnElement) btnElement.classList.add('active');

        // 獲取該分類的文章
        let filteredNews = [];
        if (category === 'all') {
            filteredNews = newsData;
        } else if (allNewsData?.data?.by_category) {
            // 新格式
            filteredNews = allNewsData.data.by_category[category] || [];
            console.log('[NewsLoader] 從by_category獲取:', category, filteredNews.length, '篇');
        } else {
            // 舊格式：按category字段篩選
            filteredNews = newsData.filter(n => n.category === category);
        }

        // 重新渲染
        const newsList = document.getElementById('newsList');
        if (newsList) {
            // 清除現有
            newsList.querySelectorAll('.news-card').forEach(card => card.remove());

            if (filteredNews.length === 0) {
                const noData = document.createElement('div');
                noData.innerHTML = `<p style="text-align:center;padding:2rem;color:#666;">該分類暫無新聞</p>`;
                const loadMore = newsList.querySelector('.load-more');
                if (loadMore) {
                    newsList.insertBefore(noData, loadMore);
                } else {
                    newsList.appendChild(noData);
                }
            } else {
                filteredNews.forEach(item => {
                    const card = createNewsCard(item);
                    const loadMore = newsList.querySelector('.load-more');
                    if (loadMore) {
                        newsList.insertBefore(card, loadMore);
                    } else {
                        newsList.appendChild(card);
                    }
                });
            }
        }
    };

    // 暴露全局方法
    window.NewsLoader = {
        refresh: loadNewsData,
        getData: () => newsData,
        getAllData: () => allNewsData
    };
})();
