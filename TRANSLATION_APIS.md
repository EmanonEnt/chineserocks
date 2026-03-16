
# 翻译 API 配置指南

## 🆓 免费方案（推荐）

### 方案 1: LibreTranslate（默认，无需配置）
- **价格**: 完全免费
- **限制**: 无限制（公用实例）
- **准确度**: ⭐⭐⭐ 良好
- **配置**: 无需配置，直接可用

**状态**: ✅ 已内置，无需 Secrets

---

### 方案 2: MyMemory（备用）
- **价格**: 免费，每天 5000 条
- **限制**: 5000 requests/day
- **准确度**: ⭐⭐⭐ 良好
- **配置**: 可选 API Key 提高限额

**如需配置**：
1. 访问 https://mymemory.translated.net/doc/spec.php
2. 注册获取 API Key
3. 添加到 GitHub Secrets: `MYMEMORY_API_KEY`

---

## 💳 付费方案（更准）

### 方案 3: Google Cloud Translation
- **价格**: 每月前 50万字符免费
- **准确度**: ⭐⭐⭐⭐⭐ 最准
- **配置**: 需要信用卡

**配置步骤**：
1. 访问 https://console.cloud.google.com/
2. 创建项目 → 启用 Cloud Translation API
3. 创建 API Key
4. 添加到 GitHub Secrets: `GOOGLE_TRANSLATE_API_KEY`

---

### 方案 4: DeepL（你之前尝试的）
- **价格**: 每月前 50万字符免费
- **准确度**: ⭐⭐⭐⭐⭐ 最准
- **问题**: 国内访问不稳定

**配置步骤**：
1. 访问 https://www.deepl.com/pro-api
2. 注册免费账户
3. 复制 API Key
4. 添加到 GitHub Secrets: `DEEPL_API_KEY`

---

## 🎯 推荐配置

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| **快速开始** | LibreTranslate | 无需配置，直接可用 |
| **稳定运行** | LibreTranslate + MyMemory | 双保险，一个失败用另一个 |
| **高准确度** | Google 或 DeepL | 翻译质量最好 |

---

## 🔧 当前配置

脚本 v4.1 默认使用优先级：
```
1. LibreTranslate（免费）→ 2. MyMemory（免费）→ 3. Google（需Key）→ 4. DeepL（需Key）
```

**你现在不需要配置任何翻译 API**，LibreTranslate 会自动工作！

如果后续想要提高翻译质量，可以添加 Google 或 MyMemory 的 API Key。
