# ChineseRocks API 接口文档

Base URL: `https://your-vercel-app.vercel.app/api`

## 接口列表

| 接口 | 方法 | 说明 |
|-----|------|------|
| /api/login | POST | 手机号登录 |
| /api/userInfo?userId=xxx | GET | 获取用户信息 |
| /api/newsList?userId=xxx | GET | 新闻列表 |
| /api/newsDetail?id=xxx&userId=xxx | GET | 新闻详情 |
| /api/userAction | POST | 记录用户行为 |
| /api/userHistory?userId=xxx | GET | 用户历史记录 |

## 1. 登录

**POST** `/api/login`

```json
{
  "phone": "13800138000",
  "code": "123456",
  "platform": "miniprogram",
  "nickname": "摇滚青年"
}
```

## 2. 获取用户信息

**GET** `/api/userInfo?userId=xxxxxxxx`

返回会员类型、投票权重、积分、统计等。

## 3. 记录用户行为

**POST** `/api/userAction`

```json
{
  "userId": "xxx",
  "contentId": "新闻ID",
  "actionType": "阅读",
  "platform": "miniprogram"
}
```

actionType: 阅读/投票/收藏/分享/点赞
