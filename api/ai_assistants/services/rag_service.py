"""
RAG (Retrieval-Augmented Generation) Service
RAG 檢索增強生成服務

Provides document retrieval and context injection for AI responses.
"""

import logging
from typing import List, Dict, Optional, Any
from django.db.models import Q

logger = logging.getLogger('analyst.rag')


def get_relevant_documents(
    user_id: str,
    query: str,
    max_docs: int = 3,
    min_relevance: float = 0.1
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents for a query.
    檢索與查詢相關的文件。
    
    Uses keyword matching and document metadata to find relevant context.
    
    Args:
        user_id: The user's ID for filtering documents
        query: The search query
        max_docs: Maximum number of documents to return
        min_relevance: Minimum relevance score (0-1)
    
    Returns:
        List of relevant document summaries with context
    """
    try:
        from ai_assistants.models import AIDocument
        
        # Tokenize query into keywords
        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 2]
        
        # Build query filter
        # Filter by user or public documents
        base_query = Q(uploaded_by_id=user_id) | Q(tags__contains=['public'])
        
        # Text search filter
        text_filter = Q()
        for keyword in keywords[:10]:  # Limit keywords
            text_filter |= (
                Q(title__icontains=keyword) |
                Q(extracted_text__icontains=keyword) |
                Q(ai_summary__icontains=keyword) |
                Q(ai_keywords__contains=[keyword])
            )
        
        if not text_filter:
            return []
        
        # Query documents
        documents = AIDocument.objects.filter(
            base_query & text_filter,
            is_active=True,
            extracted_text__isnull=False,
        ).order_by('-created_at')[:max_docs * 2]  # Get more, then score
        
        # Score and filter documents
        results = []
        for doc in documents:
            score = calculate_relevance_score(doc, keywords)
            
            if score >= min_relevance:
                results.append({
                    'id': str(doc.id),
                    'title': doc.title,
                    'document_type': doc.document_type,
                    'summary': doc.ai_summary[:500] if doc.ai_summary else '',
                    'keywords': doc.ai_keywords[:10] if doc.ai_keywords else [],
                    'excerpt': get_relevant_excerpt(doc.extracted_text, keywords),
                    'relevance_score': score,
                    'created_at': doc.created_at.isoformat(),
                })
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:max_docs]
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return []


def calculate_relevance_score(doc, keywords: List[str]) -> float:
    """
    Calculate relevance score for a document.
    計算文件的相關性分數。
    """
    score = 0.0
    
    title_lower = doc.title.lower()
    text_lower = (doc.extracted_text or '').lower()
    summary_lower = (doc.ai_summary or '').lower()
    doc_keywords = [k.lower() for k in (doc.ai_keywords or [])]
    
    for keyword in keywords:
        # Title match (highest weight)
        if keyword in title_lower:
            score += 0.3
        
        # Keyword match
        if keyword in doc_keywords:
            score += 0.25
        
        # Summary match
        if keyword in summary_lower:
            score += 0.2
        
        # Text match (lower weight due to noise)
        if keyword in text_lower:
            score += 0.1
    
    # Normalize by keyword count
    if keywords:
        score = score / len(keywords)
    
    return min(score, 1.0)  # Cap at 1.0


def get_relevant_excerpt(text: str, keywords: List[str], max_length: int = 300) -> str:
    """
    Extract a relevant excerpt from text.
    從文本中提取相關摘要。
    """
    if not text:
        return ''
    
    text_lower = text.lower()
    
    # Find the best starting position
    best_pos = 0
    best_score = 0
    
    for i, keyword in enumerate(keywords):
        pos = text_lower.find(keyword)
        if pos != -1:
            # Score based on keyword importance (earlier keywords more important)
            score = 1 / (i + 1)
            if score > best_score:
                best_score = score
                best_pos = max(0, pos - 50)  # Start slightly before keyword
    
    # Extract excerpt
    excerpt = text[best_pos:best_pos + max_length]
    
    # Clean up - don't cut in the middle of words
    if best_pos > 0 and excerpt and excerpt[0] != ' ':
        space_pos = excerpt.find(' ')
        if space_pos > 0 and space_pos < 20:
            excerpt = excerpt[space_pos + 1:]
    
    if len(text) > best_pos + max_length:
        last_space = excerpt.rfind(' ')
        if last_space > max_length - 50:
            excerpt = excerpt[:last_space] + '...'
    
    return excerpt.strip()


def build_rag_context(
    user_id: str,
    query: str,
    max_docs: int = 3
) -> str:
    """
    Build RAG context string for AI prompt.
    構建用於 AI 提示的 RAG 上下文。
    
    Args:
        user_id: User ID for document filtering
        query: The user's query
        max_docs: Maximum documents to include
    
    Returns:
        Formatted context string for AI prompt
    """
    documents = get_relevant_documents(user_id, query, max_docs)
    
    if not documents:
        return ""
    
    context_parts = ["\n--- 相關文件參考 / Relevant Document References ---\n"]
    
    for i, doc in enumerate(documents, 1):
        context_parts.append(f"\n📄 文件 {i}: {doc['title']}")
        context_parts.append(f"   類型: {doc['document_type']}")
        
        if doc['summary']:
            context_parts.append(f"   摘要: {doc['summary'][:200]}...")
        
        if doc['excerpt']:
            context_parts.append(f"   相關內容: ...{doc['excerpt']}...")
        
        if doc['keywords']:
            context_parts.append(f"   關鍵字: {', '.join(doc['keywords'][:5])}")
    
    context_parts.append("\n--- 結束參考文件 / End References ---\n")
    
    return '\n'.join(context_parts)


def enhance_query_with_rag(
    user_id: str,
    query: str,
    data_context: str = "",
    max_docs: int = 3
) -> str:
    """
    Enhance the system prompt with RAG context.
    使用 RAG 上下文增強系統提示。
    """
    rag_context = build_rag_context(user_id, query, max_docs)
    
    if not rag_context:
        return data_context
    
    return f"{data_context}\n\n{rag_context}\n\n請在回答時參考以上文件內容（如果相關）。"
