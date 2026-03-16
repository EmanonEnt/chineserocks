// news-loader.js - 新闻加载器
// 从data/news.json加载已发布的新闻

class NewsLoader {
    constructor() {
        this.data = null;
        this.currentCategory = 'all';
        this.currentPage = 1;
        this.itemsPerPage = 8;
        // 优先显示的标签（权重更高）
        this.priorityTags = [
            'TheNoname', '無名', '無名樂隊', 'THE NONAME', 'the noname',
            'PUNK', 'Punk', 'punk', 'PUNK & HARDCORE', 
            '龐克', '庞克', '硬核', 'Hardcore'
        ];
    }

    async loadNews() {
        try {
            const timestamp = new Date().getTime();
            const response = await fetch(`data/news.json?t=${timestamp}`);
            if (!response.ok) throw new Error('Failed to load news');

            this.data = await response.json();
            console.log(`[NewsLoader] Loaded ${this.data.data.latest.length} articles`);

            // 生成热门标签
            this.generateHotTags();

            return this.data;
        } catch (error) {
            console.error('[NewsLoader] Error:', error);
            return null;
        }
    }

    // 自动生成热门标签
    generateHotTags() {
        const articles = this.data?.data?.latest || [];
        const tagCount = {};

        // 统计所有标签出现次数
        articles.forEach(article => {
            const tags = article.tags || [];
            tags.forEach(tag => {
                tagCount[tag] = (tagCount[tag] || 0) + 1;
            });
        });

        // 转换为数组并排序
        let sortedTags = Object.entries(tagCount)
            .map(([tag, count]) => ({ tag, count }))
            .sort((a, b) => {
                // 优先标签权重 +10
                const aPriority = this.priorityTags.some(pt => 
                    a.tag.toLowerCase().includes(pt.toLowerCase())
                ) ? 10 : 0;
                const bPriority = this.priorityTags.some(pt => 
                    b.tag.toLowerCase().includes(pt.toLowerCase())
                ) ? 10 : 0;

                // 按 (出现次数 + 优先级) 排序
                return (b.count + bPriority) - (a.count + aPriority);
            })
            .slice(0, 12) // 取前12个
            .map(item => item.tag);

        // 如果没有标签，使用默认标签
        if (sortedTags.length === 0) {
            sortedTags = [
                'TheNoname無名', '龐克', '獨立音樂', 
                '地下搖滾', '後龐克', '迷笛音樂節'
            ];
        }

        // 渲染热门标签
        this.renderHotTags(sortedTags);
    }

    // 渲染热门标签到页面
    renderHotTags(tags) {
        const container = document.getElementById('tagCloud');
        if (!container) return;

        container.innerHTML = tags.map(tag => {
            // 判断是否是优先标签，添加特殊样式
            const isPriority = this.priorityTags.some(pt => 
                tag.toLowerCase().includes(pt.toLowerCase())
            );
            const priorityClass = isPriority ? 'priority-tag' : '';

            return `<button class="tag-item ${priorityClass}" onclick="newsLoader.filterByTag('${tag}', this)">#${tag}</button>`;
        }).join('');
    }

    getHeroArticles() {
        // 优先返回包含 TheNoname/Punk 的文章作为头条
        const articles = this.data?.data?.latest || [];
        const priorityArticles = articles.filter(article => {
            const text = (article.title + ' ' + article.content + ' ' + article.tags.join(' ')).toLowerCase();
            return this.priorityTags.some(pt => text.includes(pt.toLowerCase()));
        });

        // 合并优先文章和其他文章
        const combined = [...priorityArticles, ...articles.filter(a => !priorityArticles.includes(a))];
        return combined.slice(0, 3); // 取前3篇
    }

    getFeaturedArticles() {
        const articles = this.data?.data?.latest || [];
        // 优先选择会员专享和包含优先标签的文章
        return articles.filter(article => {
            const text = (article.title + ' ' + article.tags.join(' ')).toLowerCase();
            const hasPriority = this.priorityTags.some(pt => text.includes(pt.toLowerCase()));
            return article.is_premium || hasPriority;
        }).slice(0, 4);
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
            article.tags && article.tags.some(t => 
                t.toLowerCase().includes(tag.toLowerCase()) ||
                tag.toLowerCase().includes(t.toLowerCase())
            )
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
                        ${mainHero.is_premium ? '<span>★ 會員專享</span>' : ''}
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
            <article class="news-card ${article.is_premium ? 'premium' : ''}" 
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
                            ${article.is_premium ? '<span style="color: #B8860B; font-weight: 700;">★ 會員專享</span>' : ''}
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

    filterByTag(keyword, btn) {
        const isActive = btn.classList.contains('active');
        document.querySelectorAll('.tag-item').forEach(t => t.classList.remove('active'));

        if (!isActive) {
            btn.classList.add('active');
            const newsCards = document.querySelectorAll('.news-card');
            let hasResult = false;

            newsCards.forEach(card => {
                const title = card.querySelector('.news-title').textContent;
                const category = card.querySelector('.news-category').textContent;
                if (title.includes(keyword) || category.includes(keyword)) {
                    card.style.display = 'flex';
                    hasResult = true;
                } else {
                    card.style.display = 'none';
                }
            });

            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));

            if (!hasResult) {
                alert('暫無包含 "' + keyword + '" 的文章');
                newsCards.forEach(card => card.style.display = 'flex');
                btn.classList.remove('active');
            }
        } else {
            document.querySelectorAll('.news-card').forEach(card => {
                card.style.display = 'flex';
            });
        }
    }

    openArticle(articleId) {
        window.location.href = `article.html?id=${articleId}`;
    }

    mapCategory(category) {
        const map = {
            '獨家': 'exclusive',
            '演出': 'live',
            '專題': 'feature',
            '乐评': 'releases',
            '新闻': 'all',
            '国际': 'international'
        };
        return map[category] || 'all';
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
