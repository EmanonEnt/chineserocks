/**
 * ChineseRocks 新聞加載器 - 修復版 v2
 * 修復：
 * 1. 图片解析支持 Notion API 返回的嵌套结构
 * 2. 点击事件正确处理
 * 3. 添加 LOAD MORE 分页功能（>=11条显示按钮）
 */
(function() {

// ===== 會員系統統一管理 =====
const MemberSystem = {
    DAILY_QUOTA: 3,

    getTodayReads: function() {
        const today = new Date().toDateString();
        const stored = localStorage.getItem('cr_readHistory');
        if (stored) {
            const data = JSON.parse(stored);
            if (data.date === today) return data.count || 0;
        }
        return 0;
    },

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

    isMember: function() {
        return localStorage.getItem('userLoggedIn') === 'true' || 
               localStorage.getItem('cr_member') === 'true';
    },

    getRemaining: function() {
        if (this.isMember()) return Infinity;
        return Math.max(0, this.DAILY_QUOTA - this.getTodayReads());
    },

    canRead: function(isPremium) {
        if (this.isMember()) return true;
        if (isPremium) return false;
        return this.getRemaining() > 0;
    }
};

window.MemberSystem = MemberSystem;

// ===== 分類標籤雙語轉換 =====
const categoryBilingualMap = {
    '獨家': '獨家 EXCLUSIVE',
    '現場': '現場 LIVE',
    '專題': '專題 FEATURE',
    '國際': '國際 INTERNATIONAL',
    '新發行': '新發行 RELEASES',
    '新聞': '新聞 NEWS',
    '音樂': '音樂 MUSIC'
};

function translateCategory(category) {
    if (!category) return '新聞 NEWS';
    if (category.indexOf(' ') !== -1 && /[a-zA-Z]/.test(category)) {
        return category;
    }
    return categoryBilingualMap[category] || category + ' NEWS';
}

    var allNews = [];
    var currentCategory = 'all';

    // ===== 分页变量 =====
    var INITIAL_DISPLAY = 8; // 初始显示8条
    var LOAD_MORE_COUNT = 8; // 每次加载8条
    var currentPage = 1;
    var filteredNews = [];
    var displayedCount = 0;

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
                filter: {
                    property: '狀態',
                    select: { equals: '已發佈' }
                },
                sorts: [{ property: '發布時間', direction: 'descending' }]
            })
        })
        .then(function(res) { 
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json(); 
        })
        .then(function(data) {
            console.log('📡 Notion 返回数据:', data.results ? data.results.length : 0, '条');

            if (data.results && Array.isArray(data.results)) {
                allNews = parseNotionData(data.results);
                console.log('解析后新闻数量:', allNews.length);
                updateDisplay(allNews);
            } else {
                showError('暂无新闻数据');
            }
        })
        .catch(function(e) {
            console.error('✗ 加載失敗:', e);
            showError('新聞加載失敗: ' + e.message);
        });
    }

    // ===== 解析 Notion 数据（支持中英文属性名）=====
    function parseNotionData(results) {
        return results.map(function(page) {
            var props = page.properties || {};

            // 获取标题（支持 Name/Title/標題）
            var title = '無標題';
            if (props.Title && props.Title.title && props.Title.title[0]) {
                title = props.Title.title[0].plain_text || props.Title.title[0].text.content;
            } else if (props.Name && props.Name.title && props.Name.title[0]) {
                title = props.Name.title[0].plain_text || props.Name.title[0].text.content;
            } else if (props.標題 && props.標題.title && props.標題.title[0]) {
                title = props.標題.title[0].plain_text || props.標題.title[0].text.content;
            }

            // 获取摘要（支持 Content/Excerpt/內容）
            var excerpt = '';
            if (props.Content && props.Content.rich_text && props.Content.rich_text[0]) {
                excerpt = props.Content.rich_text[0].plain_text;
            } else if (props.Excerpt && props.Excerpt.rich_text && props.Excerpt.rich_text[0]) {
                excerpt = props.Excerpt.rich_text[0].plain_text;
            } else if (props.內容 && props.內容.rich_text && props.內容.rich_text[0]) {
                excerpt = props.內容.rich_text[0].plain_text;
            }

            // 获取分类（支持 Category/Type/類型）
            var category = '新聞';
            if (props.Category && props.Category.select) {
                category = props.Category.select.name;
            } else if (props.Type && props.Type.select) {
                category = props.Type.select.name;
            } else if (props.類型 && props.類型.select) {
                category = props.類型.select.name;
            }

            // 获取封面图（支持 Cover Image/封面圖）
            var image = '';
            var imgField = props['封面圖'] || props['Cover Image'] || props.Cover || props.cover;
            if (imgField && imgField.files && imgField.files[0]) {
                var file = imgField.files[0];
                if (file.file) image = file.file.url;
                else if (file.external) image = file.external.url;
            }

            // 获取日期
            var date = '';
            if (props['發布時間'] && props['發布時間'].date) {
                date = props['發布時間'].date.start;
            } else if (props.Date && props.Date.date) {
                date = props.Date.date.start;
            }

            // 获取标签
            var tags = [];
            if (props.Tags && props.Tags.multi_select) {
                tags = props.Tags.multi_select.map(function(t) { return t.name; });
            } else if (props.標籤 && props.標籤.multi_select) {
                tags = props.標籤.multi_select.map(function(t) { return t.name; });
            }

            // 是否会员专享
            var isPremium = false;
            if (props['是否會員專享'] && props['是否會員專享'].checkbox === true) {
                isPremium = true;
            } else if (props.Premium && props.Premium.checkbox === true) {
                isPremium = true;
            }

            // 获取来源链接
            var link = '';
            if (props['來源'] && props['來源'].url) {
                link = props['來源'].url;
            } else if (props.Link && props.Link.url) {
                link = props.Link.url;
            } else if (props.URL && props.URL.url) {
                link = props.URL.url;
            }

            return {
                id: page.id,
                title: title,
                excerpt: excerpt || title,
                category: category,
                date: date,
                image: image,
                tags: tags,
                isPremium: isPremium,
                link: link
            };
        });
    }

    function updateDisplay(news) {
        if (!news || !news.length) return;

        // 重置分页
        currentPage = 1;
        filteredNews = news;

        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(allNews);
    }

    function renderHero(news) {
        // 主 Hero
        var main = news[0];
        if (!main) return;

        var heroMain = document.getElementById('hero-main');
        if (heroMain) {
            var imgUrl = main.image || getDefaultImage();
            var defaultImg = getDefaultImage();
            var catTag = translateCategory(main.category);
            heroMain.innerHTML = '<img src="' + imgUrl + '" alt="' + main.title + '" onerror="this.src='' + defaultImg + ''">' +
                '<div class="hero-overlay"><span class="hero-tag">' + catTag + '</span>' +
                '<h2 class="hero-title">' + main.title + '</h2>' +
                '<p class="hero-excerpt">' + (main.excerpt || '') + '</p></div>';
        }

        // 侧边 Hero
        var heroSide = document.getElementById('hero-side');
        if (heroSide && news.length > 1) {
            heroSide.innerHTML = '';
            for (var i = 1; i < Math.min(3, news.length); i++) {
                var n = news[i];
                var div = document.createElement('article');
                div.className = 'side-card';
                div.innerHTML = '<img src="' + (n.image || getDefaultImage()) + '" onerror="this.src='' + getDefaultImage() + ''">' +
                    '<div class="side-overlay"><span class="side-tag">' + translateCategory(n.category) + '</span>' +
                    '<h3 class="side-title">' + n.title + '</h3></div>';
                div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
                heroSide.appendChild(div);
            }
        }
    }

    function renderList(news) {
        var container = document.getElementById('news-list');
        if (!container) return;

        // 跳过前3条（已在Hero区域显示）
        var list = news.slice(3);
        if (!list.length) {
            container.innerHTML = '<div class="empty-state"><h3>暫無更多新聞</h3></div>';
            hideLoadMoreButton();
            return;
        }

        // 保留 Load More 按钮
        var loadMoreContainer = document.getElementById('loadMoreContainer');

        // 清空现有内容（除了 Load More）
        container.innerHTML = '';

        // 创建新闻卡片
        for (var i = 0; i < list.length; i++) {
            var n = list[i];
            var div = document.createElement('article');
            // 前8条可见，后面的隐藏
            var isVisible = i < INITIAL_DISPLAY;
            div.className = 'news-card' + (n.isPremium ? ' premium' : '') + (isVisible ? ' visible' : ' hidden');
            div.innerHTML = '<div class="news-thumb"><img src="' + (n.image || getDefaultImage()) + '" onerror="this.src='' + getDefaultImage() + ''"></div>' +
                '<div class="news-content"><span class="news-category">' + translateCategory(n.category) + '</span>' +
                '<h3 class="news-title">' + n.title + '</h3>' +
                '<p class="news-excerpt">' + (n.excerpt || '') + '</p></div>';
            div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
            container.appendChild(div);
        }

        // 添加回 Load More 按钮
        if (loadMoreContainer) {
            container.appendChild(loadMoreContainer);
        }

        // 更新显示计数
        displayedCount = Math.min(INITIAL_DISPLAY, list.length);

        // 控制 LOAD MORE 按钮显示（总条数>=11才显示）
        console.log('RenderList:', {
            listLength: list.length,
            displayedCount: displayedCount,
            INITIAL_DISPLAY: INITIAL_DISPLAY
        });

        if (list.length >= 11) {
            showLoadMoreButton();
        } else {
            hideLoadMoreButton();
        }
    }

    // ===== LOAD MORE 功能 =====
    function showLoadMoreButton() {
        var container = document.getElementById('loadMoreContainer');
        if (container) {
            container.style.display = 'block';
        }
    }

    function hideLoadMoreButton() {
        var container = document.getElementById('loadMoreContainer');
        if (container) {
            container.style.display = 'none';
        }
    }

    window.loadMore = function() {
        var hiddenCards = document.querySelectorAll('.news-card.hidden');
        var toShow = Math.min(LOAD_MORE_COUNT, hiddenCards.length);

        for (var i = 0; i < toShow; i++) {
            hiddenCards[i].classList.remove('hidden');
            hiddenCards[i].classList.add('visible');
        }

        displayedCount += toShow;

        // 如果没有更多隐藏卡片，隐藏按钮
        if (hiddenCards.length <= toShow) {
            hideLoadMoreButton();
        }
    };

    function renderTags(news) {
        var container = document.getElementById('tag-cloud');
        if (!container) return;

        var tags = [];
        var tagCount = {};

        for (var i = 0; i < news.length; i++) {
            if (news[i].tags && Array.isArray(news[i].tags)) {
                for (var j = 0; j < news[i].tags.length; j++) {
                    var tag = news[i].tags[j];
                    if (tag !== '會員專享' && tag !== '編輯精選') {
                        tagCount[tag] = (tagCount[tag] || 0) + 1;
                        if (tags.indexOf(tag) === -1) tags.push(tag);
                    }
                }
            }
        }

        tags.sort(function(a, b) { return (tagCount[b] || 0) - (tagCount[a] || 0); });

        container.innerHTML = tags.slice(0, 20).map(function(t) {
            return '<button class="tag-item" onclick="filterByTag('' + t + '')">#' + t + '</button>';
        }).join('');
    }

    function renderPicks(news) {
        var container = document.getElementById('editors-pick');
        if (!container) return;

        var picks = news.filter(function(n) { 
            return n.tags && (n.tags.indexOf('編輯精選') !== -1 || n.tags.indexOf('编辑精选') !== -1);
        }).slice(0, 6);

        container.innerHTML = picks.map(function(n) {
            return '<div class="pick-item" onclick="openArticleById('' + n.id + '')">' +
                '<img src="' + (n.image || getDefaultImage()) + '" class="pick-thumb" onerror="this.src='' + getDefaultImage() + ''">' +
                '<div class="pick-content"><h4>' + n.title + '</h4><span>' + translateCategory(n.category) + '</span></div></div>';
        }).join('');
    }

    window.openArticleById = function(id) {
        var article = allNews.find(function(n) { return n.id === id; });
        if (article) openArticle(article);
    };

    window.openArticle = function(article) {
        if (!article) return;

        // 检查会员权限
        if (article.isPremium && !MemberSystem.isMember()) {
            alert('此文章為會員專享，請升級會員');
            return;
        }

        // 检查免费额度
        if (!MemberSystem.canRead(article.isPremium)) {
            alert('今日免費閱讀額度已用完');
            return;
        }

        // 记录阅读
        if (!MemberSystem.isMember()) {
            MemberSystem.recordRead();
            updateQuotaDisplay();
        }

        // 打开链接
        if (article.link) {
            window.open(article.link, '_blank');
        } else {
            // 如果没有外部链接，显示提示
            alert('文章詳情：' + article.title);
        }
    };

    window.filterByTag = function(tag) {
        var filtered = allNews.filter(function(n) { 
            return n.tags && n.tags.indexOf(tag) !== -1; 
        });

        // 重置分页并更新显示
        currentPage = 1;
        filteredNews = filtered;

        // 重新渲染列表（Hero保持显示所有）
        renderList(filtered);
    };

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }

    function showError(msg) {
        var heroMain = document.getElementById('hero-main');
        if (heroMain) {
            heroMain.innerHTML = '<div style="padding:40px;text-align:center;color:#ff0066;">' + msg + '</div>';
        }
    }

    window.updateQuotaDisplay = function() {
        var remaining = MemberSystem.getRemaining();
        var els = document.querySelectorAll('.remaining-reads, #remainingReads');
        els.forEach(function(el) {
            if (el) {
                el.textContent = remaining === Infinity ? '無限' : remaining;
            }
        });
    };
})();
