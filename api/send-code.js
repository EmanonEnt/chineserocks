// api/send-code.js
const { Resend } = require('resend');

// Resend API Key
const resend = new Resend('re_NowXWg4X_3xcaFtoWGU3FofY5DzDwFZc5');

module.exports = async (req, res) => {
  // 只允许 POST 请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, type } = req.body;

  // 生成 6 位随机验证码
  const code = Math.floor(100000 + Math.random() * 900000).toString();

  try {
    if (type === 'email') {
      // 发送邮件验证码
      await resend.emails.send({
        from: 'ChineseRocks <onboarding@resend.dev>',  // Resend 默认域名
        to: email,
        subject: 'ChineseRocks 验证码',
        html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #FF0066;">ChineseRocks 验证码</h2>
            <p>您的验证码是：</p>
            <div style="background: #f0f0f0; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #FF0066;">
              ${code}
            </div>
            <p>验证码 5 分钟内有效。</p>
            <p style="color: #888; font-size: 12px;">如非本人操作，请忽略此邮件。</p>
          </div>
        `
      });
    }

    // 返回成功（实际项目中应该保存 code 到数据库，设置过期时间）
    res.json({ 
      success: true, 
      message: '验证码已发送',
      // 演示模式：直接返回验证码
      demoCode: code 
    });

  } catch (error) {
    console.error('发送失败:', error);
    res.status(500).json({ 
      success: false, 
      error: '发送失败，请重试' 
    });
  }
};
