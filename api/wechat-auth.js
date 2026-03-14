module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { code } = req.query;
  if (!code) return res.status(400).json({ error: 'Missing code' });

  try {
    const tokenUrl = `https://api.weixin.qq.com/sns/oauth2/access_token?appid=${process.env.WECHAT_APPID}&secret=${process.env.WECHAT_SECRET}&code=${code}&grant_type=authorization_code`;
    const tokenRes = await fetch(tokenUrl);
    const tokenData = await tokenRes.json();
    
    if (tokenData.errcode) {
      return res.status(400).json({ error: tokenData.errmsg });
    }

    const userUrl = `https://api.weixin.qq.com/sns/userinfo?access_token=${tokenData.access_token}&openid=${tokenData.openid}&lang=zh_CN`;
    const userRes = await fetch(userUrl);
    const userData = await userRes.json();

    if (userData.errcode) {
      return res.status(400).json({ error: userData.errmsg });
    }

    res.json({
      success: true,
      user: {
        openid: userData.openid,
        nickname: userData.nickname,
        avatar: userData.headimgurl
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
