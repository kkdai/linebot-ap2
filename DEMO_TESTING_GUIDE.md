# 📱 Demo 測試指南 - OTP 驗證碼顯示

## ✅ 已啟用的功能

### 1. OTP 自動顯示
當用戶進行支付時，系統會自動生成並**明確顯示**測試用的 OTP 驗證碼。

### 2. Payment Agent 設定
Payment Agent 已經配置為：
- ✅ 自動檢測 `demo_hint` 和 `otp_code` 欄位
- ✅ 使用醒目格式顯示 OTP：`🔐 測試用 OTP 驗證碼：123456`
- ✅ 提供使用範例：`請回覆驗證碼完成付款，例如：驗證碼是 123456`

## 🎯 完整測試流程

### Step 1: 選購商品
```
用戶: "我想買 iPhone"
Bot: [顯示商品列表]
```

### Step 2: 加入購物車
```
用戶: "加入購物車"
Bot: [確認加入]
```

### Step 3: 結帳
```
用戶: "結帳" 或 "創建訂單"
Bot: [創建 cart mandate]
```

### Step 4: 發起支付（重要！）
```
用戶: "我要付款"
Bot: [顯示支付方式]

用戶: "使用第一個支付方式" 或指定支付方式
Bot 回應範例:
---
已發送 OTP 驗證碼！

🔐 **測試用 OTP 驗證碼：762775**

請在 5 分鐘內回覆此驗證碼完成付款。
範例：驗證碼是 762775

💳 支付方式：Visa ending in 1234
💰 金額：$999.00
⏰ 有效期限：5 分鐘
🔒 最多嘗試：3 次
---
```

### Step 5: 驗證 OTP
```
用戶: "驗證碼是 762775"
Bot: [完成支付，顯示交易確認]
```

## 🔧 技術實現細節

### OTP 返回格式
```json
{
  "otp_code": "762775",
  "demo_hint": "🔐 Demo OTP Code: 762775",
  "demo_note": "In production, OTP would be sent via SMS/Email",
  "demo_instruction": {
    "important": "THIS IS A DEMO - Display the OTP code to user",
    "display_format": "🔐 測試用 OTP 驗證碼：762775",
    "user_guidance": "請回覆驗證碼完成付款，例如：驗證碼是 762775"
  }
}
```

### Payment Agent Instruction 摘錄
```
🔄 **OTP Verification Process (CRITICAL FOR DEMO):**
⚠️ **MUST DO**: When you receive payment initiation response:
1. **ALWAYS display the OTP code** from the response
2. **Format it clearly** like: "🔐 測試用 OTP 驗證碼：123456"
3. Tell user to send this code back to complete payment
```

## 📝 預期的展示效果

### 完整對話範例
```
👤 用戶: 我想買 iPhone
🤖 Bot: 找到以下商品...

👤 用戶: 加入購物車
🤖 Bot: 已加入購物車...

👤 用戶: 結帳
🤖 Bot: 訂單已創建...

👤 用戶: 我要付款
🤖 Bot: 以下是可用的支付方式...

👤 用戶: 使用第一個
🤖 Bot: 
已發送 OTP 驗證碼！

🔐 **測試用 OTP 驗證碼：762775**

請在 5 分鐘內回覆此驗證碼完成付款。
範例：驗證碼是 762775

👤 用戶: 驗證碼是 762775
🤖 Bot: ✅ 支付成功！訂單已完成...
```

## ⚠️ 重要提醒

1. **OTP 每次都不同**：每次發起支付時，系統會生成新的 6 位數 OTP
2. **5 分鐘有效期**：OTP 在 5 分鐘後自動失效
3. **最多 3 次嘗試**：輸入錯誤 OTP 最多 3 次
4. **測試環境專用**：生產環境中，OTP 會透過 SMS/Email 發送，不會顯示在回應中

## 🚀 部署後驗證

部署到 Cloud Run 後，透過 LINE Bot 測試：
1. 確認 OTP 確實顯示在對話中
2. 確認格式醒目易讀（含 emoji 🔐）
3. 確認提供使用範例
4. 確認 OTP 驗證功能正常

## 📊 日誌檢查

在 Cloud Run 日誌中應該看到：
```
Payment initiated successfully: mandate_xxx, OTP=762775
```

這確認 OTP 已生成並記錄。
