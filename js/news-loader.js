// News Loader - 強制更新版
(function() {
    const NEWS_JSON_URL = 'data/news.json';

    async function loadNews() {
        try {
            console.log('📰 強制更新新聞...');

            const res = await fetch(`${NEWS_JSON_URL}?t=${Date.now()}`, {cache: 'no-store'});
            const data = await res.json();
            const newsList = data.data?.all || [];

            console.log('新聞數量:', newsList.length);

            if (newsList.length === 0) return;

            // 策略：直接查找所有新聞卡片，強制替換內容
            updateAllNewsCards(newsList);

        } catch (e) {
            console.error('錯誤:', e);
        }
    }

    function updateAllNewsCards(newsList) {
        // 查找所有可能的新聞卡片（通過圖片容器）
        const allImages = document.querySelectorAll('img');
        console.log('頁面圖片總數:', allImages.length);

        // 查找大圖（通常是尺寸最大的那個）
        let bigImage = null;
        let maxArea = 0;

        allImages.forEach(img => {
            const rect = img.getBoundingClientRect();
            const area = rect.width * rect.height;
            if (area > maxArea && rect.width > 300) {
                maxArea = area;
                bigImage = img;
            }
        });

        console.log('找到大圖:', bigImage ? '是' : '否');

        // 更新大圖區域
        if (bigImage && newsList[0]) {
            const news = newsList[0];
            bigImage.src = news.cover_image || news.image;

            // 查找大圖的父容器，更新標題
            let parent = bigImage.parentElement;
            for (let i = 0; i < 5 && parent; i++) {
                const title = parent.querySelector('h1, h2, h3, h4, .title');
                if (title) {
                    title.textContent = news.title;
                    console.log('✅ 更新大圖標題:', news.title);
                    break;
                }
                parent = parent.parentElement;
            }
        }

        // 查找側邊小圖（尺寸較小的圖片）
        const sideImages = [];
        allImages.forEach(img => {
            const rect = img.getBoundingClientRect();
            if (rect.width > 100 && rect.width < 400 && rect.height > 80) {
                sideImages.push(img);
            }
        });

        console.log('找到側邊圖片:', sideImages.length);

        // 更新側邊圖片
        sideImages.forEach((img, index) => {
            const newsIndex = index + 1; // 跳過第一個（大圖）
            if (newsIndex < newsList.length) {
                const news = newsList[newsIndex];
                img.src = news.cover_image || news.image;

                // 更新旁邊的標題
                let parent = img.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const title = parent.querySelector('h4, h5, .title, .news-title');
                    if (title) {
                        title.textContent = news.title;
                        console.log('✅ 更新側邊標題:', news.title);
                        break;
                    }
                    parent = parent.parentElement;
                }
            }
        });
    }

    // 頁面加載後執行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNews);
    } else {
        loadNews();
    }

    // 也延遲執行一次（確保動態內容加載完成）
    setTimeout(loadNews, 1000);
})();
