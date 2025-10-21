# AP2 LINE Bot - 智能購物與支付助手

## 專案簡介

這是一個整合 Google ADK (Agent SDK) 和 Gemini AI 模型的智能 LINE Bot，專為電商購物和 AP2 支付協議設計。機器人具備完整的購物體驗功能，從商品搜尋到安全支付一應俱全。

## 截圖展示

![image](https://github.com/user-attachments/assets/2bcbd827-0047-4a3a-8645-f8075d996c10)

## 核心功能

### 🛍️ 智能購物助手
- **商品搜尋與推薦**: 根據關鍵字或類別搜尋商品，提供個人化推薦
- **商品詳情查詢**: 查看商品價格、庫存、描述等詳細資訊
- **購物車管理**: 創建購物車清單和訂單

### 💳 AP2 安全支付系統
- **多種支付方式**: 支援信用卡等多種付款方式管理
- **OTP 雙重驗證**: 提供 OTP 驗證碼確保交易安全
- **交易追蹤**: 查詢交易狀態和歷史記錄
- **退款處理**: 支援安全的退款機制

### 🌤️ 天氣與時間查詢
- **即時天氣**: 查詢指定城市的天氣狀況
- **時間資訊**: 獲取各地區的當前時間

### 🤖 智能意圖識別
- **自動路由**: 根據用戶訊息內容自動判斷意圖並轉至對應代理
- **多語言支援**: 支援繁體中文和英文關鍵字識別
- **上下文對話**: 維持對話上下文，提供連貫的互動體驗

## 使用技術

- **Python 3.10+**: 主要開發語言
- **FastAPI**: 高效能異步 Web 框架
- **LINE Messaging API**: LINE 官方訊息 API
- **Google ADK (Agent SDK)**: Google 代理開發套件
- **Google Gemini 2.0 Flash**: 最新 AI 模型
- **AP2 Protocol**: 安全支付協議整合
- **Docker**: 容器化部署
- **Google Cloud Run**: 雲端部署平台

## 主要代理系統

### 購物代理 (Shopping Agent)
- 處理商品搜尋和推薦
- 管理購物車和訂單創建
- 支援多種商品類別 (電子產品、電腦、音響、穿戴裝置)

### 支付代理 (Payment Agent)  
- 整合 AP2 安全支付流程
- OTP 驗證和交易確認
- 支付方式管理和退款處理

### 天氣時間代理 (Weather Time Agent)
- 提供天氣資訊查詢
- 多時區時間查詢功能

## 環境設定

### 必要環境變數
設定以下環境變數：
- `ChannelSecret`: LINE 頻道密鑰
- `ChannelAccessToken`: LINE 頻道存取權杖
- `GOOGLE_API_KEY`: Google Gemini API 金鑰
- `GOOGLE_GENAI_USE_VERTEXAI`: 是否使用 Vertex AI (預設為 FALSE)

### Vertex AI 設定 (選用)
如果設定 `GOOGLE_GENAI_USE_VERTEXAI=True`，需額外設定：
- `GOOGLE_CLOUD_PROJECT`: Google Cloud 專案 ID
- `GOOGLE_CLOUD_LOCATION`: Google Cloud 地區

### 安裝步驟

1. 複製專案到本地端
   ```bash
   git clone <repository-url>
   cd linebot-ap2
   ```

2. 安裝相依套件
   ```bash
   pip install -r requirements.txt
   ```

3. 設定環境變數並啟動服務
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```

4. 設定 LINE Bot webhook URL 指向您的伺服器端點

## 使用方式

### 💬 對話範例

**購物相關:**
- "我想買 iPhone" → 自動轉至購物代理
- "推薦一些產品給我" → 提供商品推薦
- "MacBook 有庫存嗎？" → 查詢商品詳情

**支付相關:**
- "我要付款" → 轉至支付代理
- "確認購買" → 啟動 AP2 支付流程
- "驗證碼是 123456" → OTP 驗證

**天氣時間:**
- "台北天氣如何？" → 查詢天氣資訊
- "紐約現在幾點？" → 查詢當地時間

### 🔄 智能路由系統
機器人會自動根據訊息內容判斷用戶意圖：
- 偵測購物關鍵字 → 購物代理
- 偵測支付關鍵字 → 支付代理  
- 偵測天氣時間關鍵字 → 天氣時間代理

## 部署選項

### 本地開發

使用 ngrok 等工具將本地伺服器暴露至網際網路以供 webhook 存取：

```bash
ngrok http 8080
```

### Docker 部署

使用內建的 Dockerfile 建置和部署應用程式：

```bash
docker build -t linebot-ap2 .
docker run -p 8080:8080 \
  -e ChannelSecret=YOUR_SECRET \
  -e ChannelAccessToken=YOUR_TOKEN \
  -e GOOGLE_API_KEY=YOUR_GEMINI_KEY \
  linebot-ap2
```

### Google Cloud 部署

#### 前置需求

1. 安裝 [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. 建立 Google Cloud 專案並啟用以下 API：
   - Cloud Run API
   - Container Registry API 或 Artifact Registry API
   - Cloud Build API

#### 部署步驟

1. 驗證 Google Cloud：
   ```bash
   gcloud auth login
   ```

2. 設定 Google Cloud 專案：
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. 建置並推送 Docker 映像至 Google Container Registry：
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/linebot-ap2
   ```

4. 部署至 Cloud Run：
   ```bash
   gcloud run deploy linebot-ap2 \
     --image gcr.io/YOUR_PROJECT_ID/linebot-ap2 \
     --platform managed \
     --region asia-east1 \
     --allow-unauthenticated \
     --set-env-vars ChannelSecret=YOUR_SECRET,ChannelAccessToken=YOUR_TOKEN,GOOGLE_API_KEY=YOUR_GEMINI_KEY
   ```

   注意：生產環境建議使用 Secret Manager 儲存敏感的環境變數。

5. 取得服務 URL：
   ```bash
   gcloud run services describe linebot-ap2 --platform managed --region asia-east1 --format 'value(status.url)'
   ```

6. 在 LINE Developer Console 中設定服務 URL 作為 LINE Bot webhook URL。

#### Setting Up Secrets in Google Cloud (Recommended)

For better security, store your API keys as secrets:

1. Create secrets for your sensitive values:

   ```
   echo -n "YOUR_SECRET" | gcloud secrets create line-channel-secret --data-file=-
   echo -n "YOUR_TOKEN" | gcloud secrets create line-channel-token --data-file=-
   echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
   ```

2. Give the Cloud Run service access to these secrets:

   ```
   gcloud secrets add-iam-policy-binding line-channel-secret --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding line-channel-token --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding gemini-api-key --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   ```

3. Deploy with secrets:

   ```
   gcloud run deploy linebot-adk \
     --image gcr.io/YOUR_PROJECT_ID/linebot-adk \
     --platform managed \
     --region asia-east1 \
     --allow-unauthenticated \
     --update-secrets=ChannelSecret=line-channel-secret:latest,ChannelAccessToken=line-channel-token:latest,GEMINI_API_KEY=gemini-api-key:latest
   ```

## Maintenance and Monitoring

After deployment, you can monitor your service through the Google Cloud Console:

1. View logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=linebot-adk"`
2. Check service metrics: Access the Cloud Run dashboard in Google Cloud Console
3. Set up alerts for error rates or high latency in Cloud Monitoring
