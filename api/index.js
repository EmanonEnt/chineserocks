const { Client } = require('@notionhq/client');

const notion = new Client({ auth: process.env.NOTION_TOKEN });

// 数据库 ID
const DB_USERS = '3259f94580b78015ae41cacbd49c87a0';
const DB_ACTIONS = '3259f94580b78042a691ce555e6342da';
const DB_NEWS = '3229f94580b78029ba1bf49e33e7e46c';

module.exports = async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const { action } = req.query;

  try {
    switch (action) {
      case 'login':
        return await handleLogin(req, res);
      case 'userInfo':
        return await getUserInfo(req, res);
      case 'newsList':
        return await getNewsList(req, res);
      case 'newsDetail':
        return await getNewsDetail(req, res);
      case 'userAction':
        return await recordUserAction(req, res);
      case 'userHistory':
        return await getUserHistory(req, res);
      default:
        return res.status(400).json({ success: false, error: 'Unknown action' });
    }
  } catch (error) {
    console.error('API Error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
};

// 1. 登录/注册
async function handleLogin(req, res) {
  const { phone, code, platform = 'web', nickname = '' } = req.body;

  // 验证码检查（演示模式：123456）
  if (code !== '123456') {
    return res.status(400).json({ success: false, error: '验证码错误' });
  }

  const now = new Date().toISOString();

  // 查询用户
  const existing = await notion.databases.query({
    database_id: DB_USERS,
    filter: {
      property: 'Phone',
      phone_number: { equals: phone }
    }
  });

  let userId;
  let isNewUser = false;

  if (existing.results.length > 0) {
    // 更新登录时间
    userId = existing.results[0].id;
    await notion.pages.update({
      page_id: userId,
      properties: {
        'LastLogin': { date: { start: now } },
        'LastLoginPlatform': { select: { name: platform } }
      }
    });
  } else {
    // 创建新用户
    const newUser = await notion.pages.create({
      parent: { database_id: DB_USERS },
      properties: {
        'Phone': { phone_number: phone },
        'Nickname': { title: [{ text: { content: nickname || phone.slice(-4) } }] },
        'MemberType': { select: { name: 'free' } },
        'Points': { number: 0 },
        'VoteWeight': { number: 0.5 },
        'CreatedAt': { date: { start: now } },
        'RegisterPlatform': { select: { name: platform } },
        'LastLoginPlatform': { select: { name: platform } }
      }
    });
    userId = newUser.id;
    isNewUser = true;
  }

  res.json({
    success: true,
    data: { userId, phone, isNewUser, token: Buffer.from(userId).toString('base64') }
  });
}

// 2. 获取用户信息
async function getUserInfo(req, res) {
  const { userId } = req.query;

  const user = await notion.pages.retrieve({ page_id: userId });
  const props = user.properties;

  // 获取行为统计
  const actions = await notion.databases.query({
    database_id: DB_ACTIONS,
    filter: {
      property: 'UserID',
      relation: { contains: userId }
    }
  });

  const stats = {
    read: actions.results.filter(a => a.properties['ActionType']?.select?.name === '阅读').length,
    vote: actions.results.filter(a => a.properties['ActionType']?.select?.name === '投票').length,
    favorite: actions.results.filter(a => a.properties['ActionType']?.select?.name === '收藏').length
  };

  res.json({
    success: true,
    data: {
      userId,
      phone: props['Phone']?.phone_number,
      nickname: props['Nickname']?.title?.[0]?.text?.content,
      avatar: props['Avatar']?.files?.[0]?.file?.url || '',
      memberType: props['MemberType']?.select?.name || 'free',
      memberExpire: props['MemberExpire']?.date?.start || null,
      voteWeight: props['VoteWeight']?.number || 0.5,
      points: props['Points']?.number || 0,
      registerPlatform: props['RegisterPlatform']?.select?.name,
      lastLogin: props['LastLogin']?.date?.start,
      stats
    }
  });
}

// 3. 新闻列表
async function getNewsList(req, res) {
  const { page = 1, limit = 10, userId } = req.query;

  const news = await notion.databases.query({
    database_id: DB_NEWS,
    filter: { property: '状态', select: { equals: '已发布' } },
    sorts: [{ property: '发布时间', direction: 'descending' }],
    page_size: parseInt(limit)
  });

  // 获取用户已读记录
  let readIds = new Set();
  if (userId) {
    const reads = await notion.databases.query({
      database_id: DB_ACTIONS,
      filter: {
        and: [
          { property: 'UserID', relation: { contains: userId } },
          { property: 'ActionType', select: { equals: '阅读' } }
        ]
      }
    });
    readIds = new Set(reads.results.map(r => r.properties['ContentID']?.rich_text?.[0]?.text?.content));
  }

  const list = news.results.map(item => ({
    id: item.id,
    title: item.properties['标题']?.title?.[0]?.text?.content || '',
    summary: item.properties['摘要']?.rich_text?.[0]?.text?.content || '',
    cover: item.properties['封面图']?.files?.[0]?.file?.url || '',
    category: item.properties['类型']?.select?.name || '',
    tags: item.properties['标签']?.multi_select?.map(t => t.name) || [],
    publishTime: item.properties['发布时间']?.date?.start,
    source: item.properties['来源']?.rich_text?.[0]?.text?.content || '',
    isRead: readIds.has(item.id)
  }));

  res.json({ success: true, data: list });
}

// 4. 新闻详情
async function getNewsDetail(req, res) {
  const { id, userId } = req.query;

  const news = await notion.pages.retrieve({ page_id: id });

  // 记录阅读
  if (userId) {
    await notion.pages.create({
      parent: { database_id: DB_ACTIONS },
      properties: {
        'UserID': { relation: [{ id: userId }] },
        'ContentID': { rich_text: [{ text: { content: id } }] },
        'ActionType': { select: { name: '阅读' } },
        'Platform': { select: { name: 'web' } },
        'Time': { date: { start: new Date().toISOString() } }
      }
    });
  }

  res.json({
    success: true,
    data: {
      id: news.id,
      title: news.properties['标题']?.title?.[0]?.text?.content || '',
      content: news.properties['内容']?.rich_text?.[0]?.text?.content || '',
      cover: news.properties['封面图']?.files?.[0]?.file?.url || '',
      category: news.properties['类型']?.select?.name || '',
      tags: news.properties['标签']?.multi_select?.map(t => t.name) || [],
      publishTime: news.properties['发布时间']?.date?.start,
      source: news.properties['来源']?.rich_text?.[0]?.text?.content || ''
    }
  });
}

// 5. 记录用户行为
async function recordUserAction(req, res) {
  const { userId, contentId, actionType, platform = 'web', extraData = {} } = req.body;

  await notion.pages.create({
    parent: { database_id: DB_ACTIONS },
    properties: {
      'UserID': { relation: [{ id: userId }] },
      'ContentID': { rich_text: [{ text: { content: contentId } }] },
      'ActionType': { select: { name: actionType } },
      'Platform': { select: { name: platform } },
      'Time': { date: { start: new Date().toISOString() } },
      'ExtraData': { rich_text: [{ text: { content: JSON.stringify(extraData) } }] }
    }
  });

  res.json({ success: true, message: '记录成功' });
}

// 6. 获取用户历史
async function getUserHistory(req, res) {
  const { userId, actionType, limit = 20 } = req.query;

  const filter = { property: 'UserID', relation: { contains: userId } };
  if (actionType) {
    filter.and = [filter, { property: 'ActionType', select: { equals: actionType } }];
  }

  const actions = await notion.databases.query({
    database_id: DB_ACTIONS,
    filter,
    sorts: [{ property: 'Time', direction: 'descending' }],
    page_size: parseInt(limit)
  });

  const history = await Promise.all(actions.results.map(async (action) => {
    const contentId = action.properties['ContentID']?.rich_text?.[0]?.text?.content;
    let content = null;
    if (contentId) {
      try {
        const page = await notion.pages.retrieve({ page_id: contentId });
        content = {
          id: contentId,
          title: page.properties['标题']?.title?.[0]?.text?.content || ''
        };
      } catch (e) {}
    }
    return {
      actionType: action.properties['ActionType']?.select?.name,
      time: action.properties['Time']?.date?.start,
      platform: action.properties['Platform']?.select?.name,
      content
    };
  }));

  res.json({ success: true, data: history.filter(h => h.content) });
}
