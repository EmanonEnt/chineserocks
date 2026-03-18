/**
 * ChineseRocks 新聞加載器 - 統一修復版 v4
 * 修復：
 * 1. INDEX和NEWS頁面瀏覽額度統一
 * 2. 彈窗樣式統一
 * 3. 外鏈點擊統一處理
 * 4. 編輯精選有幾個顯示幾個，最多6個，不足不補充
 * 5. 熱門標籤有幾個顯示幾個，超過20個選最多的前20個，不足不顯示默認標籤
 */
(function() {

// ===== 會員系統統一管理 =====
const MemberSystem = {
    // 每日免費額度
    DAILY_QUOTA: 3,

    // 獲取今日已讀數
    getTodayReads: function() {
        const today = new Date().toDateString();
        const stored = localStorage.getItem('cr_readHistory');
        if (stored) {
            const data = JSON.parse(stored);
            if (data.date === today) {
                return data.count || 0;
            }
        }
        return 0;
    },

    // 記錄閱讀
    recordRead: function() {
        if (this.isMember()) return true;

        const today = new Date().toDateString();
        const current = this.getTodayReads();

        localStorage.setItem('cr_readHistory', JSON.stringify({
            date: today,
            count: current + 1
        }));

        return current + 1;
    },

    // 檢查是否會員
    isMember: function() {
        return localStorage.getItem('userLoggedIn') === 'true' || 
               localStorage.getItem('cr_member') === 'true';
    },

    // 獲取剩餘額度
    getRemaining: function() {
        if (this.isMember()) return Infinity;
        return Math.max(0, this.DAILY_QUOTA - this.getTodayReads());
    },

    // 檢查是否可以閱讀
    canRead: function(isPremium) {
        if (this.isMember()) return true;
        if (isPremium) return false;
        return this.getRemaining() > 0;
    }
};

// 暴露到全局
window.MemberSystem = MemberSystem;

// ===== 分類標籤雙語轉換 =====
const categoryBilingualMap = {
    '獨家': '獨家 EXCLUSIVE',
    '現場': '現場 LIVE',
    '專題': '專題 FEATURE',
    '國際': '國際 INTERNATIONAL',
    '新發行': '新發行 RELEASES',
    '新聞': '新聞 NEWS',
    '音樂': '音樂 MUSIC',
    'ALL': '全部 ALL',
    'EXCLUSIVE': '獨家 EXCLUSIVE',
    'LIVE': '現場 LIVE',
    'FEATURE': '專題 FEATURE',
    'INTERNATIONAL': '國際 INTERNATIONAL',
    'RELEASES': '新發行 RELEASES'
};

function translateCategory(category) {
    if (!category) return '新聞 NEWS';
    if (category.indexOf(' ') !== -1 && /[a-zA-Z]/.test(category)) {
        return category;
    }
    return categoryBilingualMap[category] || category + ' NEWS';
}

function convertAllCategoryTags() {
    document.querySelectorAll('.featured-tag, .hero-tag, .side-tag, .news-category').forEach(function(el) {
        el.textContent = translateCategory(el.textContent.trim());
    });
}

    var allNews = [];
    var currentCategory = 'all';

    document.addEventListener('DOMContentLoaded', function() {
        loadNewsData();
        updateQuotaDisplay();
    });

    function loadNewsData() {
        fetch('/api/notion', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                databaseId: '3229f94580b78029ba1bf49e33e7e46c',
                sorts: [{ property: 'Display Order', direction: 'ascending' }]
            })
            cache: 'no-store',
            headers: { 'Accept': 'application/json' }
        })
        .then(function(res) { 
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json(); 
        })
        .then(function(data) {
            console.log('📡 Notion 返回数据:', data.results ? data.results.length : 0, '条');
            // Notion API 返回格式处理
            if (data.results && Array.isArray(data.results)) {
                allNews = data.results.filter(function(page) {
                    // 只显示已发布的文章
                    var status = page.properties && (page.properties['Status'] || page.properties['狀態'] || page.properties['状态']);
                    var statusName = status && status.select ? status.select.name : '';
                    return statusName === '已發佈' || statusName === '已发布' || statusName === 'Published' || !statusName;
                }).map(function(page) {
                    var props = page.properties || {};

                    // 获取图片
                    var imgUrl = '';
                    var imgField = props['封面圖'] || props['Cover Image'] || props.Cover || props.cover;
                    if (imgField && imgField.files && imgField.files[0]) {
                        var file = imgField.files[0];
                        if (file.file) imgUrl = file.file.url;
                        else if (file.external) imgUrl = file.external.url;
                    }

                    return {
                        id: page.id,
                        title: props.Title && props.Title.title && props.Title.title[0] ? props.Title.title[0].plain_text : 
                               (props.標題 && props.標題.title && props.標題.title[0] ? props.標題.title[0].plain_text : '無標題'),
                        content: props.Content && props.Content.rich_text && props.Content.rich_text[0] ? props.Content.rich_text[0].plain_text : 
                                 (props.內容 && props.內容.rich_text && props.內容.rich_text[0] ? props.內容.rich_text[0].plain_text : ''),
                        excerpt: props.Excerpt && props.Excerpt.rich_text && props.Excerpt.rich_text[0] ? props.Excerpt.rich_text[0].plain_text : 
                                 (props.摘要 && props.摘要.rich_text && props.摘要.rich_text[0] ? props.摘要.rich_text[0].plain_text : ''),
                        category: props.Category && props.Category.select ? props.Category.select.name : 
                                  (props.類型 && props.類型.select ? props.類型.select.name : 
                                   (props.分類 && props.分類.select ? props.分類.select.name : '新聞')),
                        tags: props.Tags && props.Tags.multi_select ? props.Tags.multi_select.map(function(t) { return t.name; }) : 
                              (props.標籤 && props.標籤.multi_select ? props.標籤.multi_select.map(function(t) { return t.name; }) : []),
                        cover_image: imgUrl,
                        published_date: props['Published Date'] && props['Published Date'].date ? props['Published Date'].date.start : 
                                       (props['發布日期'] && props['發布日期'].date ? props['發布日期'].date.start : 
                                        (props.Date && props.Date.date ? props.Date.date.start : page.created_time)),
                        is_premium: props['Is Premium'] && props['Is Premium'].checkbox === true || 
                                   (props['會員專享'] && props['會員專享'].checkbox === true),
                        source_url: props['Source URL'] && props['Source URL'].url ? props['Source URL'].url : 
                                   (props['來源網址'] && props['來源網址'].url ? props['來源網址'].url : ''),
                        featured: props['Home Featured'] && props['Home Featured'].checkbox === true || 
                                 (props['編輯精選'] && props['編輯精選'].checkbox === true)
                    };
                });
            } else if (Array.isArray(data)) {
                allNews = data;
            } else if (data.data && data.data.all) {
                allNews = data.data.all;
            } else {
                allNews = [];
            }

            allNews.sort(function(a, b) {
                var dateA = new Date(b.published_date || b.publishDate || b.date || b.created_time || 0);
                var dateB = new Date(a.published_date || a.publishDate || a.date || a.created_time || 0);
                return dateA - dateB;
            });

            updateDisplay(allNews);
        })
        .catch(function(e) {
            console.error('✗ 加載失敗:', e);
            showError('新聞加載失敗，請檢查網絡連接');
        });
    }

    function showError(msg) {
        var heroMain = document.getElementById('hero-main');
        if (heroMain) {
            heroMain.innerHTML = '<div style="padding:40px;text-align:center;color:#ff0066;">' + msg + '</div>';
        }
    }

    function updateDisplay(news) {
        if (!news || !news.length) return;
        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(allNews);
        convertAllCategoryTags();

        if (typeof window.initNewsDisplay === 'function') {
            window.initNewsDisplay();
        }
    }

    function checkIsPremium(article) {
        if (article.is_premium === true) return true;
        if (article.isPremium === true) return true;
        if (article.tags && article.tags.indexOf('會員專享') !== -1) return true;
        return false;
    }

    function getImageUrl(article) {
        var url = article.cover_image || article.coverImage || article.image || article.cover || article.thumbnail;
        if (!url) return getDefaultImage();
        return url;
    }

    function renderHero(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        if (!heroMain || !news.length) return;

        var main = news[0];
        var isPremium = checkIsPremium(main);
        var imageUrl = getImageUrl(main);

        var heroImg = document.getElementById('hero-img');
        if (heroImg) {
            heroImg.onerror = function() {
                this.src = getDefaultImage();
            };
            heroImg.src = imageUrl;
        }

        var heroTag = document.getElementById('hero-tag');
        if (heroTag) heroTag.textContent = translateCategory(main.category);

        var heroTitle = document.getElementById('hero-title');
        if (heroTitle) heroTitle.textContent = main.title || '無標題';

        var heroExcerpt = document.getElementById('hero-excerpt');
        if (heroExcerpt) {
            var content = main.content || main.excerpt || main.summary || '';
            heroExcerpt.textContent = content.substring(0, 120) + (content.length > 120 ? '...' : '');
        }

        var heroDate = document.getElementById('hero-date');
        if (heroDate) heroDate.textContent = formatDate(main.published_date || main.publishDate || main.date);

        var heroPremium = document.getElementById('hero-premium');
        if (heroPremium) {
            heroPremium.innerHTML = isPremium ? '<span style="color:#FFD700;">★ 會員專享</span>' : '';
        }

        heroMain.onclick = function() { openArticle(main); };

        if (heroSide) {
            heroSide.innerHTML = '';
            for (var i = 1; i < Math.min(3, news.length); i++) {
                var n = news[i];
                var sideImageUrl = getImageUrl(n);

                var div = document.createElement('article');
                div.className = 'side-card';
                div.innerHTML = '<img src="' + sideImageUrl + '" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'">' +
                    '<div class="side-overlay"><span class="side-tag">' + translateCategory(n.category) + '</span>' +
                    '<h3 class="side-title">' + (n.title || '無標題') + '</h3></div>';
                div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
                heroSide.appendChild(div);
            }
        }
    }

    function renderList(news) {
        var container = document.getElementById('news-list');
        if (!container) return;

        var list = news.slice(3);
        if (!list.length) {
            container.innerHTML = '<div id="loadMoreContainer" class="load-more-container"><button class="load-more-btn" id="loadMoreBtn" onclick="loadMoreNews()">LOAD MORE 查看更多</button></div>';
            return;
        }

        container.innerHTML = '';

        for (var i = 0; i < list.length; i++) {
            var n = list[i];
            var isPremium = checkIsPremium(n);
            var cardClass = isPremium ? 'news-card premium hidden' : 'news-card hidden';
            if (i < 8) {
                cardClass = cardClass.replace('hidden', 'visible');
            }
            var listImageUrl = getImageUrl(n);

            var div = document.createElement('article');
            div.className = cardClass;
            div.innerHTML = '<div class="news-thumb"><img src="' + listImageUrl + '" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'"></div>' +
                '<div class="news-content">' +
                '<span class="news-category">' + translateCategory(n.category) + '</span>' +
                '<h3 class="news-title">' + (n.title || '無標題') + '</h3>' +
                '<p class="news-excerpt">' + (n.content || n.excerpt || '').substring(0, 100) + '...</p>' +
                '<div class="news-footer">' +
                '<div class="news-meta"><span>' + formatDate(n.published_date || n.publishDate || n.date) + '</span>' +
                (isPremium ? '<span style="color:#B8860B;font-weight:700;">★ 會員專享</span>' : '') +
                '</div></div></div>';
            div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
            container.appendChild(div);
        }

        var loadMoreDiv = document.createElement('div');
        loadMoreDiv.id = 'loadMoreContainer';
        loadMoreDiv.className = 'load-more-container';
        if (list.length <= 8) {
            loadMoreDiv.classList.add('hidden');
        }
        loadMoreDiv.innerHTML = '<button class="load-more-btn" id="loadMoreBtn" onclick="loadMoreNews()">LOAD MORE 查看更多</button>';
        container.appendChild(loadMoreDiv);
    }

    function renderTags(news) {
        var container = document.getElementById('tag-cloud');
        if (!container) return;

        var tags = [];
        var tagCount = {};

        for (var i = 0; i < news.length; i++) {
            if (news[i].tags && Array.isArray(news[i].tags)) {
                for (var j = 0; j < news[i].tags.length; j++) {
                    var tag = news[i].tags[j];
                    if (tag !== '會員專享' && tag !== '編輯精選' && tag !== '编辑精选') {
                        tagCount[tag] = (tagCount[tag] || 0) + 1;
                        if (tags.indexOf(tag) === -1) {
                            tags.push(tag);
                        }
                    }
                }
            }
        }

        tags.sort(function(a, b) {
            return (tagCount[b] || 0) - (tagCount[a] || 0);
        });

        if (tags.length > 0) {
            window._tagData = tags.slice(0, 20);
            container.innerHTML = window._tagData.map(function(t, index) {
                return '<button class="tag-item" onclick="filterByTagIndex(' + index + ')">#' + t + '</button>';
            }).join('');
        } else {
            container.innerHTML = '';
        }
    }

    window.filterByTagIndex = function(index) {
        if (window._tagData && window._tagData[index]) {
            filterByTag(window._tagData[index], event.target);
        }
    };

    function renderPicks(news) {
        var container = document.getElementById('editors-pick');
        if (!container) return;

        var picks = [];

        for (var i = 0; i < news.length; i++) {
            var isPick = news[i].featured || 
                         (news[i].tags && (
                             news[i].tags.indexOf('編輯精選') !== -1 || 
                             news[i].tags.indexOf('编辑精选') !== -1
                         ));
            if (isPick) {
                picks.push(news[i]);
            }
        }

        var display = picks.slice(0, 6);
        window._pickArticles = display;

        container.innerHTML = display.map(function(n, index) {
            var pickImageUrl = getImageUrl(n);
            return '<div class="pick-item" onclick="openPickArticle(' + index + ')">' +
                '<img src="' + pickImageUrl + '" class="pick-thumb" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'">' +
                '<div class="pick-content"><h4>' + n.title + '</h4><span>' + translateCategory(n.category) + '</span></div></div>';
        }).join('');
    }

    window.openPickArticle = function(index) {
        if (window._pickArticles && window._pickArticles[index]) {
            openArticle(window._pickArticles[index]);
        }
    };

    window.filterNews = function(category, btn) {
        currentCategory = category;
        var buttons = document.querySelectorAll('.category-btn');
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].classList.remove('active');
        }
        btn.classList.add('active');

        var filtered = category === 'all' ? allNews : allNews.filter(function(n) {
            var catMatch = n.category === category || 
                          translateCategory(n.category) === category ||
                          n.category === category.split(' ')[0];
            var tagMatch = n.tags && n.tags.indexOf(category) !== -1;
            return catMatch || tagMatch;
        });
        updateDisplay(filtered);
    };

    window.filterByTag = function(tag, btn) {
        var filtered = allNews.filter(function(n) { return n.tags && n.tags.indexOf(tag) !== -1; });
        updateDisplay(filtered);
    };

    // ===== 統一的文章打開函數 =====
    window.openArticle = function(article) {
        if (!article) return;

        var isPremium = checkIsPremium(article);

        // 檢查是否可以閱讀
        if (!MemberSystem.canRead(isPremium)) {
            showUnifiedPaywall();
            return;
        }

        // 記錄閱讀（非會員）
        if (!MemberSystem.isMember()) {
            MemberSystem.recordRead();
            updateQuotaDisplay();
        }

        // 打開外鏈
        var url = article.source_url || article.sourceUrl || article.link || article.url;
        if (url) {
            window.open(url, '_blank');
        } else {
            // 如果沒有外鏈，顯示文章詳情（待開發）
            showArticleDetail(article);
        }
    };

    // ===== 統一的付費牆彈窗 =====
    window.showUnifiedPaywall = function() {
        // 移除舊的彈窗
        var oldModal = document.getElementById('unifiedPaywall');
        if (oldModal) oldModal.remove();

        var modal = document.createElement('div');
        modal.id = 'unifiedPaywall';
        modal.innerHTML = `
            <div class="paywall-overlay" onclick="closeUnifiedPaywall()"></div>
            <div class="paywall-modal">
                <button class="paywall-close" onclick="closeUnifiedPaywall()">×</button>
                <div class="paywall-icon">🔒</div>
                <h3 class="paywall-title">今日免費閱讀額度已用完</h3>
                <p class="paywall-desc">您已免費閱讀3篇新聞</p>
                <p class="paywall-sub">升級會員，無限暢讀全站內容</p>
                <button class="paywall-btn" onclick="upgradeMember()">升級會員 ¥66/月</button>
                <p class="paywall-hint">或明日再來，額度每日重置</p>
            </div>
        `;

        // 添加樣式
        if (!document.getElementById('paywallStyles')) {
            var styles = document.createElement('style');
            styles.id = 'paywallStyles';
            styles.textContent = `
                .paywall-overlay {
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.85);
                    z-index: 9998;
                    backdrop-filter: blur(5px);
                }
                .paywall-modal {
                    position: fixed;
                    top: 50%; left: 50%;
                    transform: translate(-50%, -50%);
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    border: 1px solid rgba(255,0,102,0.3);
                    border-radius: 16px;
                    padding: 40px;
                    text-align: center;
                    z-index: 9999;
                    min-width: 320px;
                    max-width: 90vw;
                    box-shadow: 0 20px 60px rgba(255,0,102,0.3);
                }
                .paywall-close {
                    position: absolute;
                    top: 15px; right: 20px;
                    background: none;
                    border: none;
                    color: #888;
                    font-size: 28px;
                    cursor: pointer;
                    transition: color 0.3s;
                }
                .paywall-close:hover { color: #fff; }
                .paywall-icon {
                    font-size: 48px;
                    margin-bottom: 15px;
                }
                .paywall-title {
                    color: #fff;
                    font-size: 1.3rem;
                    margin-bottom: 10px;
                    font-weight: 700;
                }
                .paywall-desc {
                    color: #ff0066;
                    font-size: 1rem;
                    margin-bottom: 8px;
                    font-weight: 600;
                }
                .paywall-sub {
                    color: #aaa;
                    font-size: 0.9rem;
                    margin-bottom: 25px;
                }
                .paywall-btn {
                    background: linear-gradient(135deg, #ff0066 0%, #cc0052 100%);
                    color: white;
                    border: none;
                    padding: 14px 40px;
                    border-radius: 30px;
                    font-size: 1rem;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s;
                    width: 100%;
                }
                .paywall-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(255,0,102,0.4);
                }
                .paywall-hint {
                    color: #666;
                    font-size: 0.8rem;
                    margin-top: 15px;
                }
                @media (max-width: 480px) {
                    .paywall-modal {
                        padding: 30px 20px;
                        min-width: 280px;
                    }
                }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(modal);
    };

    window.closeUnifiedPaywall = function() {
        var modal = document.getElementById('unifiedPaywall');
        if (modal) modal.remove();
    };

    window.upgradeMember = function() {
        window.location.href = 'member.html';
    };

    // 文章詳情（簡化版）
    function showArticleDetail(article) {
        alert('文章詳情頁功能開發中...\n標題: ' + article.title);
    }

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }

    function formatDate(date) {
        if (!date) return '';
        var d = new Date(date);
        if (isNaN(d.getTime())) return '';
        return d.getFullYear() + '.' + (d.getMonth() + 1) + '.' + d.getDate();
    }

    // 更新額度顯示
    window.updateQuotaDisplay = function() {
        var remaining = MemberSystem.getRemaining();
        var els = document.querySelectorAll('.remaining-reads, #remainingReads');
        els.forEach(function(el) {
            if (el) {
                if (remaining === Infinity) {
                    el.textContent = '無限';
                } else {
                    el.textContent = remaining;
                }
            }
        });
    };

    // 兼容舊的函數名
    window.showMobilePaywall = window.showUnifiedPaywall;
    window.closeMobilePaywall = window.closeUnifiedPaywall;

    window.toggleFav = function(btn, title) {
        if (!MemberSystem.isMember()) {
            showUnifiedPaywall();
            return;
        }
        btn.classList.toggle('active');
        btn.textContent = btn.classList.contains('active') ? '★' : '☆';
    };
})();

// ===== LOAD MORE 功能 =====
const INITIAL_COUNT = 8;
const BATCH_SIZE = 6;
let currentVisibleCount = INITIAL_COUNT;

window.initNewsDisplay = function() {
    const newsCards = document.querySelectorAll('.news-list .news-card');
    const loadMoreContainer = document.getElementById('loadMoreContainer');

    if (newsCards.length === 0) return;

    newsCards.forEach((card, index) => {
        if (index < INITIAL_COUNT) {
            card.classList.remove('hidden');
            card.classList.add('visible');
        } else {
            card.classList.add('hidden');
            card.classList.remove('visible');
        }
    });

    currentVisibleCount = INITIAL_COUNT;

    if (loadMoreContainer) {
        if (newsCards.length > INITIAL_COUNT) {
            loadMoreContainer.classList.remove('hidden');
        } else {
            loadMoreContainer.classList.add('hidden');
        }
    }
};

window.loadMoreNews = function() {
    const newsCards = document.querySelectorAll('.news-list .news-card');
    const loadMoreContainer = document.getElementById('loadMoreContainer');

    let newlyShown = 0;

    newsCards.forEach((card, index) => {
        if (index >= currentVisibleCount && index < currentVisibleCount + BATCH_SIZE) {
            card.classList.remove('hidden');
            card.classList.add('visible');
            newlyShown++;
        }
    });

    currentVisibleCount += newlyShown;

    if (currentVisibleCount >= newsCards.length) {
        if (loadMoreContainer) {
            loadMoreContainer.classList.add('hidden');
        }
    }
};
