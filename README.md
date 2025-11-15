# AP2 LINE Bot - 企業級智能購物與支付助手

## 專案簡介

這是一個採用現代化架構的企業級 LINE Bot 應用程式，整合 Google ADK (Agent SDK) 和 Gemini AI 模型，專為電商購物和 AP2 (Agent Payments Protocol) 支付協議設計。應用程式具備完整的購物體驗功能，從商品搜尋、購物車管理到安全支付處理一應俱全，並完全符合 AP2 協議標準。

## 🏗️ 架構亮點

### 現代化專案架構 (v0.1.0)
- **模組化設計**: 採用 `src/` 佈局，清晰的關注點分離
- **現代 Python**: 支援 Python 3.10+，使用 Pydantic v2 和現代異步模式
- **企業級工具**: 整合 Black、isort、flake8、mypy、pytest 等開發工具
- **AP2 合規性**: 完全符合 Google Agent Payments Protocol 標準

### 增強的服務架構 (v0.1.0)
- **服務層**: ProductService、PaymentService、MandateService
- **工具層**: 增強版購物和支付工具，支援複雜業務邏輯
- **模型層**: 完整的 Pydantic 資料模型定義
- **配置層**: 基於 Pydantic Settings 的環境變數管理

## 截圖展示

![image](https://github.com/user-attachments/assets/2bcbd827-0047-4a3a-8645-f8075d996c10)

## 🚀 核心功能

### 🛍️ 增強版智能購物助手

- **進階商品搜尋**: 多條件過濾 (類別、價格範圍、品牌)，相關性評分排序
- **智能推薦系統**: 基於用戶偏好的個人化商品推薦
- **購物車管理**: 完整的購物車操作，支援數量調整和商品管理
- **商品詳情增強**: 包含規格、庫存、相關商品等完整資訊
- **即時庫存檢查**: 實時商品可用性驗證

### 🔐 企業級 AP2 安全支付系統

- **AP2 協議合規**: 完全符合 Google Agent Payments Protocol 標準
- **HMAC-SHA256 簽署**: 使用業界標準的 mandate 數位簽章
- **增強 OTP 驗證**: 多重安全防護，防止未授權交易
- **Circuit Breaker 模式**: 防止系統級聯故障的斷路器保護
- **智能重試機制**: 指數退避的錯誤處理和自動重試
- **完整審計追蹤**: 所有交易的詳細日誌記錄

### 🛡️ 安全與可靠性特性

- **錯誤分類處理**: 自動區分暫時性和永久性錯誤
- **Session 管理增強**: 自動清理、用戶限制、詳細統計
- **結構化日誌**: 上下文感知的操作記錄和監控
- **配置驗證**: 啟動時自動驗證環境設定

### 🌤️ 天氣與時間查詢

- **即時天氣**: 查詢指定城市的天氣狀況
- **時間資訊**: 獲取各地區的當前時間

### 🧠 智能意圖識別系統

- **增強意圖檢測**: 模式匹配 + 關鍵字，信心評分機制
- **多語言支援**: 繁體中文和英文關鍵字智能識別
- **上下文對話**: 維持對話狀態，提供連貫的互動體驗
- **智能路由**: 基於信心評分的精準 agent 路由

### 📊 監控與維護

- **健康檢查端點**: `/health` 提供系統狀態監控
- **指標端點**: `/metrics` 提供詳細的應用程式指標
- **Session 統計**: 即時用戶活動和 session 使用分析

## 🛠️ 技術堆疊

### 核心技術
- **Python 3.10+**: 現代 Python 特性，包括 `zoneinfo`、異步語法等
- **FastAPI**: 高效能異步 Web 框架，支援 lifespan 管理
- **Pydantic v2**: 資料驗證和 Settings 管理
- **LINE Messaging API**: LINE 官方訊息 API

### AI 與代理技術
- **Google ADK (Agent SDK)**: Google 代理開發套件
- **Google Gemini 2.5 Flash**: 最新 AI 模型
- **AP2 Protocol**: 完整的 Agent Payments Protocol 支援
- **a2a-SDK**: Agent-to-Agent 通訊協議

### 企業級功能
- **HMAC-SHA256**: 業界標準數位簽章
- **Circuit Breaker**: 系統穩定性保護
- **Exponential Backoff**: 智能重試機制
- **Structured Logging**: 企業級日誌系統

### 開發與部署
- **Modern Python Packaging**: `pyproject.toml` 配置
- **Development Tools**: Black、isort、flake8、mypy、pytest
- **Docker**: 容器化部署支援
- **Google Cloud Run**: 雲端部署平台

### 資料與儲存
- **In-Memory Services**: 開發和測試用記憶體儲存
- **Session Management**: 進階 session 追蹤和管理
- **Audit Logging**: 完整的操作審計追蹤

## 🤖 主要代理系統

### 增強版購物代理 (Enhanced Shopping Agent)

**核心功能:**
- **進階商品搜尋**: 7 個專業工具，支援多條件過濾和相關性排序
- **智能推薦引擎**: 基於用戶偏好和瀏覽行為的個人化推薦
- **購物車管理**: 完整的購物車生命週期管理
- **AP2 Mandate 創建**: 安全的購物車轉換為支付 mandate

**技術特色:**
- 使用 `ProductService` 進行商品管理
- 整合 `MandateService` 支援 AP2 協議
- 結構化的商品資料模型
- 即時庫存驗證和管理

### 增強版支付代理 (Enhanced Payment Agent)

**安全功能:**
- **AP2 協議合規**: 完整的 mandate 簽署和驗證流程
- **多重 OTP 驗證**: 增強的安全驗證機制
- **交易狀態追蹤**: 即時交易監控和狀態更新
- **智能錯誤處理**: 自動重試和錯誤分類

**企業級特性:**
- Circuit Breaker 防護模式
- 完整的審計日誌追蹤
- PCI DSS Level 1 合規性
- 支援退款和爭議處理

### 天氣時間代理 (Weather Time Agent)

**功能:**
- 提供即時天氣資訊查詢
- 支援多時區時間查詢
- 整合第三方天氣 API

## 📁 專案結構

```
linebot-ap2/
├── src/linebot_ap2/           # 主要應用程式套件
│   ├── agents/                # 增強版代理實現
│   │   ├── enhanced_shopping_agent.py
│   │   └── enhanced_payment_agent.py
│   ├── common/                # 共用工具和組件
│   │   ├── session_manager.py # 增強版 session 管理
│   │   ├── intent_detector.py # 智能意圖檢測
│   │   ├── retry_handler.py   # 重試和錯誤處理
│   │   └── logger.py          # 結構化日誌系統
│   ├── config/                # 配置管理
│   │   └── settings.py        # Pydantic 設定管理
│   ├── models/                # 資料模型
│   │   ├── payment.py         # 支付相關模型
│   │   ├── product.py         # 商品和購物車模型
│   │   └── agent.py           # 代理回應模型
│   ├── services/              # 業務邏輯服務
│   │   ├── mandate_service.py # AP2 mandate 管理
│   │   ├── payment_service.py # 支付處理服務
│   │   └── product_service.py # 商品管理服務
│   └── tools/                 # 代理工具
│       ├── shopping_tools.py  # 增強版購物工具
│       └── payment_tools.py   # 增強版支付工具
├── main.py                    # 增強版 FastAPI 應用程式
├── main_new.py               # 開發版本 (可選)
├── pyproject.toml            # 現代 Python 專案配置
├── requirements.txt          # 舊版依賴 (向後相容)
└── CLAUDE.md                 # Claude Code 指導文件
```

## ⚙️ 環境設定

### 必要環境變數

#### 基本配置
- `ChannelSecret`: LINE Channel Secret
- `ChannelAccessToken`: LINE Channel Access Token  
- `GOOGLE_API_KEY`: Google Gemini API 金鑰 (不使用 Vertex AI 時)

#### 進階配置 (可選)
- `DEBUG`: 啟用偵錯模式 (預設: False)
- `LOG_LEVEL`: 日誌等級 - DEBUG, INFO, WARNING, ERROR (預設: INFO)
- `HOST`: 伺服器主機 (預設: 0.0.0.0)
- `PORT`: 伺服器連接埠 (預設: 8080)
- `SESSION_TIMEOUT_MINUTES`: Session 逾時時間 (預設: 30)
- `MAX_OTP_ATTEMPTS`: OTP 最大嘗試次數 (預設: 3)
- `OTP_EXPIRY_MINUTES`: OTP 過期時間 (預設: 5)

### Vertex AI 設定 (選用)

如果設定 `GOOGLE_GENAI_USE_VERTEXAI=True`，需額外設定：

- `GOOGLE_CLOUD_PROJECT`: Google Cloud 專案 ID
- `GOOGLE_CLOUD_LOCATION`: Google Cloud 地區

### 📦 安裝步驟

#### 方法一：現代化安裝 (推薦)

1. **複製專案**
   ```bash
   git clone <repository-url>
   cd linebot-ap2
   ```

2. **使用 pyproject.toml 安裝**
   ```bash
   # 基本安裝
   pip install -e .
   
   # 包含開發工具
   pip install -e ".[dev]"
   
   # 或使用 uv (更快的套件管理器)
   uv sync
   uv sync --group dev
   ```

3. **設定環境變數** (創建 `.env` 檔案)
   ```env
   ChannelSecret=your_line_channel_secret
   ChannelAccessToken=your_line_access_token
   GOOGLE_API_KEY=your_google_api_key
   DEBUG=True
   LOG_LEVEL=DEBUG
   ```

4. **啟動增強版應用程式**
   ```bash
   # 推薦：使用增強版 main.py
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   
   # 使用自訂配置
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload --log-level debug
   ```

#### 方法二：舊版相容安裝

```bash
# 使用舊版 requirements.txt
pip install -r requirements.txt

# 啟動應用程式
uvicorn main:app --host 0.0.0.0 --port 8080
```

### 🔧 開發工具使用

安裝開發依賴後，可使用以下工具：

```bash
# 程式碼格式化
black src/

# 排序 imports
isort src/

# 程式碼檢查
flake8 src/

# 型別檢查
mypy src/

# 執行測試
pytest

# 執行所有檢查
black src/ && isort src/ && flake8 src/ && mypy src/ && pytest
```

## 🎯 使用方式

### 💬 增強版對話範例

**🛍️ 購物體驗:**

- "我想買 iPhone" → 啟動智能商品搜尋
- "推薦 1000 美元以下的電腦" → 基於價格的個人化推薦
- "MacBook 有什麼規格？" → 顯示詳細商品資訊含規格
- "幫我加入購物車" → 購物車管理和數量選擇
- "創建訂單" → 生成 AP2 合規的安全 mandate

**🔐 安全支付流程:**

- "我要付款" → 顯示可用支付方式
- "選擇信用卡付款" → 啟動 AP2 安全支付流程
- "驗證碼是 123456" → 多重 OTP 安全驗證
- "查詢交易狀態" → 即時交易追蹤
- "申請退款" → 安全退款處理

**🌤️ 天氣時間:**

- "台北天氣如何？" → 即時天氣資訊
- "紐約現在幾點？" → 多時區時間查詢

### 🧠 智能路由系統增強

**意圖檢測特色:**
- **信心評分**: 基於模式匹配和關鍵字的信心度計算
- **多語言支援**: 繁體中文和英文無縫切換
- **上下文感知**: 維持對話狀態和購物上下文

**自動路由邏輯:**
- 購物關鍵字 (信心度 > 0.7) → 增強版購物代理
- 支付關鍵字 (最高優先級) → 增強版支付代理  
- 天氣時間關鍵字 → 天氣時間代理
- 未知意圖 → 預設為購物代理 (提供幫助選項)

### 🔗 API 端點

**監控端點:**
- `GET /health` - 系統健康檢查
  ```json
  {
    "status": "healthy",
    "active_sessions": 5,
    "timestamp": 1234567890.123
  }
  ```

- `GET /metrics` - 詳細應用程式指標
  ```json
  {
    "active_sessions": 5,
    "active_users": ["user1", "user2"],
    "app_name": "linebot_ap2",
    "model": "gemini-2.5-flash"
  }
  ```

**核心端點:**
- `POST /` - LINE webhook 回調 (增強錯誤處理)

## 🚀 部署選項

### 本地開發

**快速啟動:**
```bash
# 使用增強版應用程式
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 使用 ngrok 暴露至網際網路
ngrok http 8080
```

**進階本地開發:**
```bash
# 啟用偵錯模式
DEBUG=True LOG_LEVEL=DEBUG uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 監控健康狀態
curl http://localhost:8080/health

# 查看應用程式指標
curl http://localhost:8080/metrics
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

#### 使用 Google Cloud Secret Manager (建議)

為了更好的安全性，將 API 金鑰儲存為機密：

1. 為敏感資料建立機密：

   ```bash
   echo -n "YOUR_SECRET" | gcloud secrets create line-channel-secret --data-file=-
   echo -n "YOUR_TOKEN" | gcloud secrets create line-channel-token --data-file=-
   echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
   ```

2. 授予 Cloud Run 服務存取這些機密的權限：

   ```bash
   gcloud secrets add-iam-policy-binding line-channel-secret --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding line-channel-token --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding gemini-api-key --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
   ```

3. 使用機密部署：

   ```bash
   gcloud run deploy linebot-ap2 \
     --image gcr.io/YOUR_PROJECT_ID/linebot-ap2 \
     --platform managed \
     --region asia-east1 \
     --allow-unauthenticated \
     --update-secrets=ChannelSecret=line-channel-secret:latest,ChannelAccessToken=line-channel-token:latest,GOOGLE_API_KEY=gemini-api-key:latest
   ```

## 📊 維護與監控

### 增強版監控功能

**內建監控端點:**
```bash
# 健康檢查
curl http://your-service-url/health

# 詳細指標
curl http://your-service-url/metrics
```

**Google Cloud Console 監控:**
```bash
# 查看應用程式日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=linebot-ap2"

# 即時日誌串流
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=linebot-ap2"
```

**關鍵指標監控:**
- Session 活躍數量和用戶統計
- Agent 回應時間和成功率
- 支付交易處理狀態
- 錯誤率和重試統計
- Circuit Breaker 狀態

### 日誌分析

**結構化日誌格式:**
```
2025-10-31 10:00:00 | session_manager | INFO | ✓ New session created: session_user123 for user: user123
2025-10-31 10:00:01 | shopping_tools | INFO | Product search: query='iPhone', category='', price_range=None-None
2025-10-31 10:00:02 | payment_service | INFO | Payment initiated: mandate=mandate_abc123, user=user123
```

**監控警報建議:**
- 錯誤率 > 5%
- 平均回應時間 > 3 秒
- 活躍 Session 數量異常
- OTP 驗證失敗率 > 10%

## 🔄 版本更新紀錄

### v0.1.0 (最新版)
- ✅ 現代化專案架構重構
- ✅ AP2 協議完整實現  
- ✅ 企業級錯誤處理和重試機制
- ✅ 增強版 session 管理系統
- ✅ 結構化日誌和監控
- ✅ Circuit Breaker 和指數退避
- ✅ Pydantic v2 配置管理
- ✅ 開發工具整合 (Black, mypy, pytest)

### v0.0.1 (初始版本)
- 基本 LINE Bot 功能
- 簡單的購物和支付代理
- 基礎 AP2 支付流程

## 🤝 貢獻指南

### 開發流程
1. Fork 此專案
2. 建立功能分支: `git checkout -b feature/your-feature`
3. 執行代碼品質檢查: `black src/ && isort src/ && flake8 src/ && mypy src/`
4. 執行測試: `pytest`
5. 提交變更: `git commit -m "Add: your feature description"`
6. 推送分支: `git push origin feature/your-feature`
7. 建立 Pull Request

### 程式碼標準
- 遵循 Black 程式碼格式
- 通過 flake8 和 mypy 檢查
- 維持測試覆蓋率 > 80%
- 使用 Pydantic 模型進行資料驗證
- 結構化的日誌記錄

## 📄 授權

此專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

## 🙏 致謝

- [Google ADK](https://github.com/google/adk) - Agent Development Kit
- [LINE Messaging API](https://developers.line.biz/en/docs/messaging-api/) - LINE Bot 平台
- [FastAPI](https://fastapi.tiangolo.com/) - 現代 Python Web 框架
- [Pydantic](https://pydantic.dev/) - 資料驗證與設定管理

---

**🚀 立即開始使用企業級 LINE Bot AP2 購物助手！**
