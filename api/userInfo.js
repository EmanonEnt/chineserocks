// api/userInfo.js - 获取用户信息（用于会员互通）
const { Client } = require('@notionhq/client');

const notion = new Client({ 
  auth: process.env.NOTION_TOKEN 
});

const databaseId = process.env.NOTION_DATABASE_ID;

module.exports = async (req, res) => {
  // 设置 CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const userId = req.query.userId || req.query.userid;
const phone = req.query.phone;
  
  if (!userId && !phone) {
    return res.status(400).json({ 
      error: 'Missing userId or phone parameter' 
    });
  }

  try {
    // 查询 Notion 数据库
    const response = await notion.databases.query({
    database_id: databaseId,
    filter: phone
      ? { property: 'Phone', phone_number: { equals: phone } }
      : { property: 'Nickname', title: { equals: userId } }
    });

    if (response.results.length === 0) {
      return res.status(404).json({ 
        error: 'User not found',
        exists: false 
      });
    }

    const user = response.results[0];
    const props = user.properties;

    res.json({
      exists: true,
      userId: props.Nickname?.title?.[0]?.text?.content || userId,
      phone: props.Phone?.phone_number || null,
      name: props.Name?.title?.[0]?.text?.content || null,
      email: props.Email?.email || null,
      avatar: props.Avatar?.url || null,
      points: props.Points?.number || 0,
      createdTime: user.created_time,
      lastLogin: props.LastLogin?.date?.start || null
    });

  } catch (error) {
    console.error('Notion API Error:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message 
    });
  }
};
