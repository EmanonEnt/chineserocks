// news-loader.js - 新闻加载器
// 从data/news.json加载已发布的新闻

class NewsLoader {
    constructor() {
        this.data = null;
        this.currentCategory = 'all';
        this.currentPage = 1;
        this.itemsPerPage = 8;
    }

    async loadNews() {
        try {
            const timestamp = new Date().getTime();
            const response = await fetch(`data/news.json?t=${timestamp}`);
            if (!response.ok) throw new Error('Failed to load news');

            this.data = await response.json();
            console.log(`[NewsLoader] Loaded ${this.data.data.latest.length} articles`);
            return this.data;
        } catch (error) {
            console.error('[NewsLoader] Error:', error);
            return null;
        }
    }

    getHeroArticles() {
        return this.data?.data?.hero || [];
    }

    getFeaturedArticles() {
        return this.data?.data?.featured || [];
    }

    getLatestArticles(page = 1) {
        const articles = this.data?.data?.latest || [];
        const start = (page - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        return articles.slice(start, end);
    }

    getArticlesByCategory(category) {
        if (category === 'all') {
            return this.data?.data?.latest || [];
        }
        return this.data?.data?.by_category[category] || [];
    }

    getArticlesByTag(tag) {
        const all = this.data?.data?.latest || [];
        return all.filter(article => 
            article.tags && article.tags.includes(tag)
        );
    }

    renderHero() {
        const heroArticles = this.getHeroArticles();
        if (heroArticles.length === 0) return;

        const mainHero = heroArticles[0];
        const heroMain = document.querySelector('.hero-main');
        if (heroMain) {
            heroMain.innerHTML = `
                <img src="${mainHero.cover_image}" alt="${mainHero.title}">
                <div class="hero-overlay">
                    <span class="hero-tag exclusive">獨家 EXCLUSIVE</span>
                    <h2 class="hero-title">${mainHero.title}</h2>
                    <p class="hero-excerpt">${mainHero.content.substring(0, 100)}...</p>
                    <div class="hero-meta">
                        <span>${this.formatDate(mainHero.published_date)}</span>
                        <span>閱讀時間 ${this.estimateReadTime(mainHero.content)} 分鐘</span>
                        ${mainHero.tags.includes('会员专享') ? '<span>★ 會員專享</span>' : ''}
                    </div>
                </div>
            `;
            heroMain.onclick = () => this.openArticle(mainHero.id);
        }

        const sideArticles = heroArticles.slice(1, 3);
        const heroSide = document.querySelector('.hero-side');
        if (heroSide) {
            heroSide.innerHTML = sideArticles.map(article => `
                <article class="side-card" onclick="newsLoader.openArticle('${article.id}')">
                    <img src="${article.cover_image}" alt="${article.title}">
                    <div class="side-overlay">
                        <span class="side-tag">${article.tags[0] || '新闻'}</span>
                        <h3 class="side-title">${article.title}</h3>
                    </div>
                </article>
            `).join('');
        }
    }

    renderNewsList(category = 'all', page = 1) {
        const container = document.getElementById('newsList');
        if (!container) return;

        const loadMoreBtn = container.querySelector('.load-more');

        let articles = category === 'all' 
            ? this.getLatestArticles(page)
            : this.getArticlesByCategory(category).slice((page-1)*this.itemsPerPage, page*this.itemsPerPage);

        const articlesHTML = articles.map(article => `
            <article class="news-card ${article.tags.includes('会员专享') ? 'premium' : ''}" 
                     data-category="${this.mapCategory(article.category)}"
                     onclick="newsLoader.openArticle('${article.id}')">
                <div class="news-thumb">
                    <img src="${article.cover_image}" alt="${article.title}">
                </div>
                <div class="news-content">
                    <span class="news-category">${article.category} ${article.tags[0] || ''}</span>
                    <h3 class="news-title">${article.title}</h3>
                    <p class="news-excerpt">${article.content.substring(0, 80)}...</p>
                    <div class="news-footer">
                        <div class="news-meta">
                            <span>${this.formatDate(article.published_date)}</span>
                            <span>閱讀 ${this.estimateReadTime(article.content)} 分鐘</span>
                            ${article.tags.includes('会员专享') ? '<span style="color: #B8860B; font-weight: 700;">★ 會員專享</span>' : ''}
                        </div>
                        <div class="news-actions">
                            <button class="action-btn" onclick="event.stopPropagation(); toggleFav(this, '${article.title}')">☆</button>
                            <button class="action-btn" onclick="event.stopPropagation(); shareArticle('${article.title}')">↗</button>
                        </div>
                    </div>
                </div>
            </article>
        `).join('');

        if (page === 1) {
            container.innerHTML = articlesHTML + (loadMoreBtn ? loadMoreBtn.outerHTML : '');
        } else {
            container.insertAdjacentHTML('beforeend', articlesHTML);
        }
    }

    openArticle(articleId) {
        window.location.href = `article.html?id=${articleId}`;
    }

    mapCategory(category) {
        const map = {
            '演出预告': 'live',
            '新闻': 'news',
            '专访': 'feature',
            '乐评': 'review'
        };
        return map[category] || 'news';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}`;
    }

    estimateReadTime(content) {
        const words = content.length / 200;
        return Math.max(1, Math.round(words));
    }
}

const newsLoader = new NewsLoader();

document.addEventListener('DOMContentLoaded', async () => {
    await newsLoader.loadNews();
    newsLoader.renderHero();
    newsLoader.renderNewsList();
});
