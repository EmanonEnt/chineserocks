export default async function handler(req, res) {
    // 设置 CORS 头
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // 处理预检请求
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // 只允许 POST 请求
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    try {
        const { databaseId, filter, sorts } = req.body;

        // 从环境变量读取 API Key（安全！）
        const apiKey = process.env.NOTION_API_KEY;

        if (!apiKey) {
            console.error('❌ NOTION_API_KEY 未设置');
            return res.status(500).json({ error: 'Server configuration error: NOTION_API_KEY not set' });
        }

        if (!databaseId) {
            return res.status(400).json({ error: 'databaseId is required' });
        }

        console.log('📡 代理请求到 Notion API:', databaseId);

        // 调用 Notion API
        const notionUrl = `https://api.notion.com/v1/databases/${databaseId}/query`;

        const response = await fetch(notionUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filter: filter || undefined,
                sorts: sorts || undefined
            })
        });

        const data = await response.json();

        console.log('📡 Notion API 响应状态:', response.status);

        if (!response.ok) {
            console.error('❌ Notion API 错误:', data);
            return res.status(response.status).json(data);
        }

        console.log('✅ 成功获取数据，条目数:', data.results?.length || 0);

        // 返回数据给前端
        res.status(200).json(data);

    } catch (error) {
        console.error('❌ 代理错误:', error);
        res.status(500).json({ 
            error: 'Internal server error',
            message: error.message 
        });
    }
}
