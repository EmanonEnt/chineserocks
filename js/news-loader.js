// News Loader - 完整替換版
(function() {
    const NEWS_JSON_URL = 'data/news.json';

    async function loadNews() {
        try {
            console.log('📰 加載真實新聞...');

            const res = await fetch(`${NEWS_JSON_URL}?t=${Date.now()}`, {cache: 'no-store'});
            const data = await res.json();
            const newsList = data.data?.all || data.news || [];

            console.log('獲取到', newsList.length, '條真實新聞');

            if (newsList.length === 0) {
                console.log('⚠️ 沒有真實新聞數據');
                return;
            }

            // 強制替換所有新聞區域
            replaceAllNews(newsList);

        } catch (e) {
            console.error('❌ 錯誤:', e);
        }
    }

    function replaceAllNews(newsList) {
        // 1. 找到所有新聞卡片（通過查找包含圖片和標題的容器）
        const allCards = findAllNewsCards();
        console.log('找到', allCards.length, '個新聞卡片');

        // 2. 用真實數據替換每個卡片
        allCards.forEach((card, index) => {
            if (index < newsList.length) {
                const news = newsList[index];
                updateCard(card, news);
                console.log(`✅ 卡片 ${index + 1} 已更新:`, news.title.substring(0, 30));
            } else if (newsList.length > 0) {
                // 如果新聞不夠，循環使用
                const news = newsList[index % newsList.length];
                updateCard(card, news);
                console.log(`✅ 卡片 ${index + 1} 已更新（循環）:`, news.title.substring(0, 30));
            }
        });
    }

    function findAllNewsCards() {
        const cards = [];

        // 策略1: 查找常見的新聞容器 class
        const selectors = [
            '.news-item', '.news-card', '.article-card',
            '.featured-news', '.side-news-item',
            '[class*="news"]', '[class*="article"]'
        ];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (!cards.includes(el)) cards.push(el);
            });
        });

        // 策略2: 如果沒找到，查找包含大圖片的容器
        if (cards.length === 0) {
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                const rect = img.getBoundingClientRect();
                // 只取可見的、尺寸合適的圖片
                if (rect.width > 200 && rect.height > 100) {
                    let parent = img.parentElement;
                    // 向上查找3層，找到包含標題的容器
                    for (let i = 0; i < 3 && parent; i++) {
                        if (parent.querySelector('h1, h2, h3, h4, .title, [class*="title"]')) {
                            if (!cards.includes(parent)) {
                                cards.push(parent);
                                break;
                            }
                        }
                        parent = parent.parentElement;
                    }
                }
            });
        }

        return cards;
    }

    function updateCard(card, news) {
        // 更新圖片
        const img = card.querySelector('img');
        if (img) {
            const newSrc = news.cover_image || news.image || news.coverImage;
            if (newSrc) img.src = newSrc;
        }

        // 更新標題（查找 h1-h6 或包含 title 的 class）
        const titleSelectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '[class*="title"]', '.news-title'];
        for (const sel of titleSelectors) {
            const title = card.querySelector(sel);
            if (title) {
                title.textContent = news.title;
                break;
            }
        }

        // 更新摘要/內容
        const summarySelectors = ['.summary', '.excerpt', '.description', '.content', 'p'];
        for (const sel of summarySelectors) {
            const summary = card.querySelector(sel);
            if (summary && summary.textContent.length > 10) {
                summary.textContent = news.content || news.summary || news.description || '';
                break;
            }
        }

        // 更新分類標籤
        const catSelectors = ['.category', '.tag', '.label', '[class*="category"]', '[class*="tag"]'];
        for (const sel of catSelectors) {
            const cat = card.querySelector(sel);
            if (cat) {
                cat.textContent = news.category || news.tag || '新聞';
                break;
            }
        }

        // 更新鏈接
        const link = card.querySelector('a') || (card.tagName === 'A' ? card : null);
        if (link && news.source_url) {
            link.href = news.source_url;
        }
    }

    // 頁面加載後執行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNews);
    } else {
        loadNews();
    }

    // 延遲再執行一次（確保動態內容加載完成）
    setTimeout(loadNews, 500);
    setTimeout(loadNews, 1500);

})();
