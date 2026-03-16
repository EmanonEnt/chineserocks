# 創建 api 文件夾
mkdir api

# 創建 sync-user.js 文件
cat > api/sync-user.js << 'EOF'
const { Client } = require('@notionhq/client');
const notion = new Client({ auth: process.env.NOTION_TOKEN });
const DATABASE_ID = process.env.NOTION_DATABASE_ID;

module.exports = async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

    try {
        const { phone, userData } = req.body;
        
        const result = await notion.databases.query({
            database_id: DATABASE_ID,
            filter: {
                property: 'Phone',
                phone_number: { equals: phone }
            }
        });

        const now = new Date().toISOString();
        
        if (result.results.length > 0) {
            await notion.pages.update({
                page_id: result.results[0].id,
                properties: {
                    'Nickname': { title: [{ text: { content: userData.nickname } }] },
                    'LastLogin': { date: { start: now } }
                }
            });
        } else {
            await notion.pages.create({
                parent: { database_id: DATABASE_ID },
                properties: {
                    'Phone': { phone_number: phone },
                    'Nickname': { title: [{ text: { content: userData.nickname } }] },
                    'MemberType': { select: { name: 'free' } },
                    'CreatedAt': { date: { start: now } }
                }
            });
        }

        res.status(200).json({ success: true });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
};
EOF
