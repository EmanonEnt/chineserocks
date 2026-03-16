// News Loader - 修復版
(function() {
    const NEWS_JSON_URL = 'data/news.json';

    async function loadNews() {
        try {
            console.log('📰 開始加載新聞...');

            const response = await fetch(`${NEWS_JSON_URL}?t=${Date.now()}`, {
                cache: 'no-store'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('📦 數據結構:', Object.keys(data));

            // 解析正確的數據結構
            // 格式: { updated_at, total_count, data: { all: [...], hero: [...] } }
            let newsList = [];

            if (data.data && data.data.all && Array.isArray(data.data.all)) {
                // 新格式
                newsList = data.data.all;
                console.log('✅ 使用 data.data.all 格式');
            } else if (data.news && Array.isArray(data.news)) {
                // 舊格式
                newsList = data.news;
                console.log('✅ 使用 data.news 格式');
            } else if (Array.isArray(data)) {
                // 直接是數組
                newsList = data;
                console.log('✅ 使用直接數組格式');
            } else {
                console.error('❌ 無法識別數據格式:', data);
                return;
            }

            console.log('📊 新聞數量:', newsList.length);
            newsList.forEach((news, i) => {
                console.log(`   ${i+1}. ${news.title}`);
            });

            renderNews(newsList);

        } catch (error) {
            console.error('❌ 加載失敗:', error);
        }
    }

    function renderNews(newsList) {
        if (newsList.length === 0) {
            console.log('⚠️ 沒有新聞');
            return;
        }

        // 根據數量決定布局
        if (newsList.length === 1) {
            updateFeaturedNews(newsList[0], true);
            updateSideNews([]);
        } else if (newsList.length === 2) {
            updateFeaturedNews(newsList[0], false);
            updateSideNews([newsList[1]]);
        } else {
            updateFeaturedNews(newsList[0], false);
            updateSideNews(newsList.slice(1, 3));
        }
    }

    function updateFeaturedNews(news, isFullWidth) {
        // 查找元素（嘗試多種選擇器）
        const imgSelectors = ['.featured-news-img', '.news-main-image', '.hero-news img', '.main-news-image'];
        const titleSelectors = ['.featured-news-title', '.news-main-title', '.hero-news h3', '.main-news-title'];
        const summarySelectors = ['.featured-news-summary', '.news-main-summary', '.hero-news p'];
        const linkSelectors = ['.featured-news-link', '.news-main-link', '.hero-news a'];

        const img = findElement(imgSelectors);
        const title = findElement(titleSelectors);
        const summary = findElement(summarySelectors);
        const link = findElement(linkSelectors);

        // 使用 cover_image 或 image 字段
        const imageUrl = news.cover_image || news.image || '';

        if (img && imageUrl) {
            img.src = imageUrl;
            img.alt = news.title;
            console.log('✅ 大圖已更新:', news.title);
        }

        if (title) {
            title.textContent = news.title;
        }

        if (summary) {
            // 使用 content 或 summary 字段
            summary.textContent = news.summary || news.content || '';
        }

        if (link) {
            link.href = news.source_url || news.sourceUrl || '#';
        }

        // 更新分類
        const catSelectors = ['.featured-news-category', '.news-category', '.category-tag'];
        const catEl = findElement(catSelectors);
        if (catEl && news.category) {
            catEl.textContent = news.category;
        }
    }

    function updateSideNews(newsList) {
        const containerSelectors = ['.side-news', '.news-sidebar', '.secondary-news'];
        const container = findElement(containerSelectors);

        if (!container) {
            console.log('⚠️ 未找到側邊容器');
            return;
        }

        container.innerHTML = '';

        if (newsList.length === 0) {
            container.style.display = 'none';
            return;
        }

        newsList.forEach(news => {
            const imageUrl = news.cover_image || news.image || '';
            const item = document.createElement('div');
            item.className = 'side-news-item';
            item.style.cssText = 'margin-bottom: 15px;';

            item.innerHTML = `
                <a href="${news.source_url || news.sourceUrl || '#'}" style="
                    display: block;
                    text-decoration: none;
                    color: inherit;
                ">
                    <div style="
                        width: 100%;
                        height: 150px;
                        overflow: hidden;
                        border-radius: 8px;
                        margin-bottom: 10px;
                    ">
                        <img src="${imageUrl}" alt="${news.title}" style="
                            width: 100%;
                            height: 100%;
                            object-fit: cover;
                        ">
                    </div>
                    <span style="
                        display: inline-block;
                        background: #ff0066;
                        color: white;
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        margin-bottom: 5px;
                    ">${news.category || '新聞'}</span>
                    <h4 style="
                        margin: 0;
                        font-size: 16px;
                        line-height: 1.3;
                        color: #333;
                    ">${news.title}</h4>
                </a>
            `;
            container.appendChild(item);
        });

        console.log('✅ 側邊新聞已更新:', newsList.length, '條');
    }

    function findElement(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    // 頁面加載後執行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNews);
    } else {
        loadNews();
    }

    // 每5分鐘刷新
    setInterval(loadNews, 5 * 60 * 1000);
})();
