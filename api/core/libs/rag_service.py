"""
RAG (Retrieval Augmented Generation) Knowledge Base Service.
Stores and retrieves help documentation for the AI assistant.
"""
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


@dataclass
class KnowledgeItem:
    """A single item in the knowledge base"""
    id: str
    title: str
    content: str
    category: str
    metadata: Dict = None
    embedding: Optional[np.ndarray] = None


class RAGKnowledgeBase:
    """
    RAG Knowledge Base for ERP help documentation.
    Uses embeddings and vector search for semantic retrieval.
    """
    
    def __init__(self):
        self.items: Dict[str, KnowledgeItem] = {}
        self.index = None
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self._initialized = False
        
        # Load default knowledge base
        self._load_default_knowledge()
    
    def _load_default_knowledge(self):
        """Load default ERP help documentation"""
        default_items = [
            # Accounting Module
            KnowledgeItem(
                id="acc-001",
                title="如何查看會計科目表",
                content="""
會計科目表 (Chart of Accounts) 是記錄所有會計科目的清單。

查看步驟：
1. 在左側選單點擊「會計」
2. 選擇「會計科目表」
3. 您會看到所有科目列表，包括科目代碼、名稱、類型和餘額

科目類型說明：
- 資產 (Asset): 公司擁有的資源
- 負債 (Liability): 公司的債務
- 權益 (Equity): 股東權益
- 收入 (Revenue): 營業收入
- 費用 (Expense): 營業支出
""",
                category="accounting"
            ),
            KnowledgeItem(
                id="acc-002",
                title="如何建立日記帳分錄",
                content="""
日記帳分錄是記錄會計交易的方式。

建立步驟：
1. 進入「會計」>「日記帳分錄」
2. 點擊「新增分錄」
3. 填寫分錄資訊：
   - 日期：交易日期
   - 描述：交易說明
   - 借方科目和金額
   - 貸方科目和金額
4. 確認借貸方金額相等
5. 點擊「儲存」

重要原則：
- 借方金額必須等於貸方金額
- 資產、費用增加記借方
- 負債、權益、收入增加記貸方
""",
                category="accounting"
            ),
            KnowledgeItem(
                id="acc-003",
                title="如何建立發票",
                content="""
發票用於記錄銷售交易。

建立步驟：
1. 進入「會計」>「發票」
2. 點擊「新增發票」
3. 填寫發票資訊：
   - 發票類型：銷售或採購
   - 客戶/供應商名稱
   - 發票日期和到期日
   - 品項明細（品名、數量、單價）
4. 系統自動計算總金額
5. 點擊「儲存」或「發送」

發票狀態：
- 草稿：尚未完成
- 已發送：已寄給客戶
- 已付款：已收到款項
""",
                category="accounting"
            ),
            KnowledgeItem(
                id="acc-004",
                title="如何生成財務報表",
                content="""
系統提供多種財務報表。

查看報表：
1. 進入「會計」>「報表」
2. 選擇報表類型：
   - 試算表：查看借貸方餘額
   - 資產負債表：查看財務狀況
   - 損益表：查看經營績效

操作方式：
1. 選擇報表類型
2. 設定日期範圍
3. 點擊「生成報表」
4. 可匯出 PDF 或 Excel
""",
                category="accounting"
            ),
            
            # HRMS Module
            KnowledgeItem(
                id="hrms-001",
                title="如何管理員工資料",
                content="""
員工資料管理功能讓您維護公司人員資訊。

操作步驟：
1. 進入「人力資源」>「員工」
2. 查看員工列表

新增員工：
1. 點擊「新增員工」
2. 填寫基本資料：
   - 員工編號
   - 姓名
   - 部門
   - 職稱
   - 入職日期
3. 點擊「儲存」

編輯員工：
1. 點擊員工列表中的「編輯」
2. 修改資料
3. 點擊「儲存」
""",
                category="hrms"
            ),
            KnowledgeItem(
                id="hrms-002",
                title="如何申請請假",
                content="""
員工可以透過系統申請各類休假。

申請步驟：
1. 進入「人力資源」>「請假」
2. 點擊「申請休假」
3. 填寫申請表：
   - 假別：年假、病假、事假等
   - 開始日期
   - 結束日期
   - 原因說明
4. 點擊「提交」

申請狀態：
- 審核中：等待主管核准
- 已核准：申請通過
- 已拒絕：申請未通過
""",
                category="hrms"
            ),
            
            # AI Features
            KnowledgeItem(
                id="ai-001",
                title="如何使用 AI 助手",
                content="""
AI 助手可以幫助您快速獲取資訊和完成任務。

使用方式：
1. 點擊畫面右下角的對話圖示
2. 輸入您的問題
3. AI 助手會根據上下文提供回答

功能範圍：
- 回答系統操作問題
- 提供會計相關指導
- 協助資料查詢
- 解釋報表數據

提示：
- 問題越具體，回答越準確
- 可以直接問「如何...」的操作問題
- AI 會根據您目前的頁面提供相關建議
""",
                category="ai"
            ),
            KnowledgeItem(
                id="ai-002",
                title="如何設定 API 金鑰",
                content="""
設定 AI 服務 API 金鑰以啟用 AI 功能。

設定步驟：
1. 進入「設定」>「API 金鑰」
2. 選擇要設定的服務：
   - OpenAI：GPT-4 等模型
   - Google Gemini：Gemini 模型
   - DeepSeek：經濟型 AI 服務
3. 輸入 API 金鑰
4. 點擊「儲存」
5. 可點擊「測試」驗證金鑰有效性

取得金鑰：
- OpenAI: https://platform.openai.com/api-keys
- Gemini: https://makersuite.google.com/app/apikey
- DeepSeek: https://platform.deepseek.com/api_keys
""",
                category="settings"
            ),
            
            # General
            KnowledgeItem(
                id="gen-001",
                title="如何切換語言",
                content="""
系統支援繁體中文和英文介面。

切換方式：
1. 找到頁面右上角的語言切換按鈕（地球圖示）
2. 點擊按鈕
3. 選擇「繁體中文」或「English」
4. 介面會立即切換

注意事項：
- 語言設定會儲存在瀏覽器中
- 下次登入會自動使用上次的語言設定
""",
                category="general"
            ),
        ]
        
        for item in default_items:
            self.items[item.id] = item
    
    def add_item(self, item: KnowledgeItem):
        """Add an item to the knowledge base"""
        self.items[item.id] = item
        self._initialized = False  # Need to rebuild index
    
    def search(self, query: str, top_k: int = 3, category: Optional[str] = None) -> List[KnowledgeItem]:
        """
        Search the knowledge base for relevant items.
        Falls back to keyword search if embeddings not available.
        """
        results = []
        
        # Simple keyword search (fallback)
        query_lower = query.lower()
        
        for item in self.items.values():
            if category and item.category != category:
                continue
            
            # Score based on keyword matching
            score = 0
            if query_lower in item.title.lower():
                score += 3
            if query_lower in item.content.lower():
                score += 1
            
            # Check for word overlap
            query_words = set(query_lower.split())
            title_words = set(item.title.lower().split())
            content_words = set(item.content.lower().split())
            
            score += len(query_words & title_words) * 2
            score += len(query_words & content_words) * 0.5
            
            if score > 0:
                results.append((score, item))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:top_k]]
    
    def get_context_for_query(self, query: str, category: Optional[str] = None) -> str:
        """
        Get relevant context from knowledge base for RAG.
        Returns formatted context string for LLM.
        """
        items = self.search(query, top_k=3, category=category)
        
        if not items:
            return ""
        
        context_parts = []
        for item in items:
            context_parts.append(f"### {item.title}\n{item.content}")
        
        return "\n\n---\n\n".join(context_parts)


# Singleton instance
_knowledge_base: Optional[RAGKnowledgeBase] = None


def get_knowledge_base() -> RAGKnowledgeBase:
    """Get the singleton knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = RAGKnowledgeBase()
    return _knowledge_base
