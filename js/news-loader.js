// News Loader - 調試版本
(function() {
    const NEWS_JSON_URL = 'data/news.json';

    async function loadNews() {
        try {
            console.log('🔍 === 新聞加載調試開始 ===');

            // 強制清除緩存
            const nocacheUrl = `${NEWS_JSON_URL}?nocache=${Date.now()}&r=${Math.random()}`;
            console.log('🌐 請求 URL:', nocacheUrl);

            const response = await fetch(nocacheUrl, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });

            console.log('📡 響應狀態:', response.status, response.statusText);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('📦 原始數據:', JSON.stringify(data, null, 2));

            if (!data.news || !Array.isArray(data.news)) {
                console.error('❌ 數據格式錯誤: news 不是數組');
                return;
            }

            console.log('📊 新聞數量:', data.news.length);
            console.log('📝 新聞列表:');
            data.news.forEach((news, i) => {
                console.log(`   ${i+1}. ${news.title} (ID: ${news.id})`);
                console.log(`      圖片: ${news.image ? news.image.substring(0, 50) + '...' : '無'}`);
            });

            // 檢查頁面元素
            console.log('🔍 檢查頁面元素:');
            const selectors = [
                '.featured-news-img', '.news-main-image', '.hero-news img',
                '.featured-news-title', '.news-main-title', '.hero-news h3',
                '.side-news', '.news-sidebar'
            ];
            selectors.forEach(sel => {
                const el = document.querySelector(sel);
                console.log(`   ${sel}: ${el ? '✅ 找到' : '❌ 未找到'}`);
            });

            renderNews(data.news);

        } catch (error) {
            console.error('❌ 加載失敗:', error);
        }
    }

    function renderNews(newsList) {
        console.log('🎨 開始渲染', newsList.length, '條新聞');

        if (newsList.length >= 1) {
            console.log('🖼️ 渲染大圖新聞:', newsList[0].title);
            updateFeaturedNews(newsList[0]);
        }

        if (newsList.length >= 2) {
            const sideNews = newsList.slice(1, 3);
            console.log('📑 渲染側邊新聞:', sideNews.length, '條');
            updateSideNews(sideNews);
        }
    }

    function updateFeaturedNews(news) {
        // 嘗試所有可能的選擇器
        const imgSelectors = ['.featured-news-img', '.news-main-image', '.hero-news img', '.main-news-image'];
        const titleSelectors = ['.featured-news-title', '.news-main-title', '.hero-news h3', '.main-news-title', '.news-title'];

        const img = findElement(imgSelectors);
        const title = findElement(titleSelectors);

        if (img) {
            img.src = news.image;
            img.alt = news.title;
            console.log('✅ 圖片已更新為:', news.image.substring(0, 50));
        } else {
            console.error('❌ 未找到圖片元素，嘗試的選擇器:', imgSelectors.join(', '));
        }

        if (title) {
            title.textContent = news.title;
            console.log('✅ 標題已更新為:', news.title);
        } else {
            console.error('❌ 未找到標題元素，嘗試的選擇器:', titleSelectors.join(', '));
        }
    }

    function updateSideNews(newsList) {
        const containerSelectors = ['.side-news', '.news-sidebar', '.secondary-news', '.right-news'];
        const container = findElement(containerSelectors);

        if (!container) {
            console.error('❌ 未找到側邊容器，嘗試的選擇器:', containerSelectors.join(', '));
            return;
        }

        console.log('✅ 找到側邊容器:', container.className);
        container.innerHTML = '';

        newsList.forEach((news, i) => {
            console.log(`  渲染側邊 ${i+1}:`, news.title);
            const item = document.createElement('div');
            item.className = 'side-news-item';
            item.innerHTML = `
                <a href="${news.sourceUrl || '#'}" style="display:block;text-decoration:none;color:inherit;">
                    <img src="${news.image}" style="width:100%;height:150px;object-fit:cover;border-radius:8px;margin-bottom:10px;">
                    <span style="background:#ff0066;color:white;padding:2px 8px;border-radius:4px;font-size:12px;">${news.category || '新聞'}</span>
                    <h4 style="margin:5px 0;font-size:16px;color:#333;">${news.title}</h4>
                </a>
            `;
            container.appendChild(item);
        });
    }

    function findElement(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    // 立即執行
    loadNews();

    // 也監聽 DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNews);
    }
})();
