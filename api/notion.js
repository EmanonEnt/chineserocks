// Vercel Serverless Function - Notion API Proxy
export default async function handler(req, res) {
  // 設置 CORS 頭
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const { databaseId, filter, sorts } = req.body;

    // API Key（建議在 Vercel 環境變量中設置 NOTION_API_KEY）
    const apiKey = process.env.NOTION_API_KEY || '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';

    console.log('Proxying request to Notion API:', databaseId);

    const response = await fetch(`https://api.notion.com/v1/databases/${databaseId}/query`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filter: filter || undefined,
        sorts: sorts || undefined,
        page_size: 10
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Notion API error:', response.status, errorText);
      res.status(response.status).json({ 
        error: 'Notion API error', 
        status: response.status,
        details: errorText 
      });
      return;
    }

    const data = await response.json();
    console.log('Notion API success:', data.results?.length || 0, 'articles');
    res.status(200).json(data);

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ error: error.message });
  }
}
