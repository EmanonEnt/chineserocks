const { Client } = require('@notionhq/client');

module.exports = async (req, res) => {
  // 设置 CORS 头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // 处理预检请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // 只接受 POST 请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { databaseId, filter, sorts } = req.body;

    if (!databaseId) {
      return res.status(400).json({ error: 'Database ID is required' });
    }

    // 初始化 Notion 客户端
    const notion = new Client({ 
      auth: process.env.NOTION_TOKEN 
    });

    console.log('Querying database:', databaseId);
    console.log('Filter:', JSON.stringify(filter));
    console.log('Sorts:', JSON.stringify(sorts));

    // 构建查询参数
    const queryParams = {
      database_id: databaseId,
    };

    if (filter) {
      queryParams.filter = filter;
    }

    if (sorts) {
      queryParams.sorts = sorts;
    }

    // 查询数据库
    const response = await notion.databases.query(queryParams);

    console.log('Notion response:', response.results.length, 'results');

    return res.status(200).json({
      results: response.results,
      has_more: response.has_more,
      next_cursor: response.next_cursor
    });

  } catch (error) {
    console.error('Notion API Error:', error);

    return res.status(500).json({
      error: 'Failed to query Notion database',
      message: error.message,
      code: error.code
    });
  }
};
