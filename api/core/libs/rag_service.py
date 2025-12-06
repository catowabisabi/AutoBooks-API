"""
RAG (Retrieval Augmented Generation) Knowledge Base Service.
Stores and retrieves help documentation for the AI assistant.
Supports bilingual (EN/ZH) content.
"""
import os
import json
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
    title_en: str
    title_zh: str
    content: str
    content_en: str
    content_zh: str
    category: str
    metadata: Dict = None
    embedding: Optional[np.ndarray] = None


class RAGKnowledgeBase:
    """
    RAG Knowledge Base for ERP help documentation.
    Uses embeddings and vector search for semantic retrieval.
    Supports bilingual (EN/ZH) content.
    """
    
    def __init__(self):
        self.items: Dict[str, KnowledgeItem] = {}
        self.index = None
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self._initialized = False
        
        # Load knowledge base from JSON file
        self._load_knowledge_from_json()
    
    def _load_knowledge_from_json(self):
        """Load knowledge base from JSON file"""
        # Try to find the JSON file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'ai_assistants', 'data', 'knowledge_base.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_assistants', 'data', 'knowledge_base.json'),
            'ai_assistants/data/knowledge_base.json',
        ]
        
        json_file = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                json_file = abs_path
                break
        
        if json_file and os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    knowledge_data = json.load(f)
                
                for item_data in knowledge_data:
                    item = KnowledgeItem(
                        id=item_data['id'],
                        title=item_data.get('title_en', item_data.get('title', '')),
                        title_en=item_data.get('title_en', ''),
                        title_zh=item_data.get('title_zh', ''),
                        content=item_data.get('content_en', item_data.get('content', '')),
                        content_en=item_data.get('content_en', ''),
                        content_zh=item_data.get('content_zh', ''),
                        category=item_data.get('category', 'general'),
                        metadata=item_data.get('metadata', {})
                    )
                    self.items[item.id] = item
                
                print(f"[RAG] Loaded {len(self.items)} knowledge base entries from JSON")
            except Exception as e:
                print(f"[RAG] Error loading knowledge base JSON: {e}")
                self._load_default_knowledge()
        else:
            print("[RAG] Knowledge base JSON not found, using defaults")
            self._load_default_knowledge()
    
    def _load_default_knowledge(self):
        """Load default ERP help documentation (fallback when JSON not available)"""
        # Default items are minimal - full data should come from knowledge_base.json
        default_items = [
            KnowledgeItem(
                id="default-001",
                title="How to use AI Assistant",
                title_en="How to use AI Assistant",
                title_zh="如何使用 AI 助手",
                content="Click the chat icon at bottom right to open AI Assistant. Type your question and get instant help.",
                content_en="Click the chat icon at bottom right to open AI Assistant. Type your question and get instant help.",
                content_zh="點擊右下角的對話圖示開啟 AI 助手。輸入您的問題即可獲得即時幫助。",
                category="ai"
            ),
        ]
        
        for item in default_items:
            self.items[item.id] = item
    
    def add_item(self, item: KnowledgeItem):
        """Add an item to the knowledge base"""
        self.items[item.id] = item
        self._initialized = False  # Need to rebuild index
    
    def search(self, query: str, top_k: int = 3, category: Optional[str] = None, language: str = 'en') -> List[KnowledgeItem]:
        """
        Search the knowledge base for relevant items.
        Falls back to keyword search if embeddings not available.
        
        Args:
            query: Search query
            top_k: Number of results to return
            category: Optional category filter
            language: 'en' or 'zh' for language preference
        """
        results = []
        
        # Simple keyword search (fallback)
        query_lower = query.lower()
        
        for item in self.items.values():
            if category and item.category != category:
                continue
            
            # Score based on keyword matching in both languages
            score = 0
            
            # Search in title (both languages)
            title_en = item.title_en.lower() if item.title_en else item.title.lower()
            title_zh = item.title_zh if item.title_zh else ''
            
            if query_lower in title_en:
                score += 3
            if query_lower in title_zh:
                score += 3
            
            # Search in content (both languages)
            content_en = item.content_en.lower() if item.content_en else item.content.lower()
            content_zh = item.content_zh if item.content_zh else ''
            
            if query_lower in content_en:
                score += 1
            if query_lower in content_zh:
                score += 1
            
            # Check for word overlap
            query_words = set(query_lower.split())
            title_words = set(title_en.split()) | set(title_zh.split() if title_zh else [])
            content_words = set(content_en.split()) | set(content_zh.split() if content_zh else [])
            
            score += len(query_words & title_words) * 2
            score += len(query_words & content_words) * 0.5
            
            if score > 0:
                results.append((score, item))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:top_k]]
    
    def get_context_for_query(self, query: str, category: Optional[str] = None, language: str = 'en') -> str:
        """
        Get relevant context from knowledge base for RAG.
        Returns formatted context string for LLM.
        
        Args:
            query: Search query
            category: Optional category filter
            language: 'en' or 'zh' for language preference
        """
        items = self.search(query, top_k=3, category=category, language=language)
        
        if not items:
            return ""
        
        context_parts = []
        for item in items:
            # Use language-specific content
            if language == 'zh':
                title = item.title_zh or item.title_en or item.title
                content = item.content_zh or item.content_en or item.content
            else:
                title = item.title_en or item.title
                content = item.content_en or item.content
            
            context_parts.append(f"### {title}\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_all_items(self, language: str = 'en') -> List[Dict]:
        """Get all knowledge base items for display"""
        items = []
        for item in self.items.values():
            if language == 'zh':
                title = item.title_zh or item.title_en or item.title
                content = item.content_zh or item.content_en or item.content
            else:
                title = item.title_en or item.title
                content = item.content_en or item.content
            
            items.append({
                'id': item.id,
                'title': title,
                'title_en': item.title_en,
                'title_zh': item.title_zh,
                'content': content,
                'content_en': item.content_en,
                'content_zh': item.content_zh,
                'category': item.category,
            })
        return items


# Singleton instance
_knowledge_base: Optional[RAGKnowledgeBase] = None


def get_knowledge_base() -> RAGKnowledgeBase:
    """Get the singleton knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = RAGKnowledgeBase()
    return _knowledge_base
