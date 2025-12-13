"""
RAG (Retrieval Augmented Generation) API views.
Provides endpoints for querying the knowledge base.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema
from core.libs.rag_service import get_knowledge_base
from core.libs.ai_service import AIService
from core.schema_serializers import RAGQueryRequestSerializer, RAGChatRequestSerializer


@extend_schema(tags=['Settings'])
class RAGQueryView(APIView):
    """
    Query the RAG knowledge base.
    Returns relevant documentation based on the query.
    """
    permission_classes = [AllowAny]  # Allow public access to help docs
    serializer_class = RAGQueryRequestSerializer
    
    @extend_schema(
        summary='查詢知識庫 / Query knowledge base',
        description='查詢 RAG 知識庫並返回相關文檔。\n\nQuery RAG knowledge base and return relevant documents.'
    )
    def post(self, request):
        query = request.data.get('query', '')
        category = request.data.get('category')
        include_context = request.data.get('include_context', True)
        
        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        kb = get_knowledge_base()
        
        # Get relevant items
        items = kb.search(query, top_k=5, category=category)
        
        # Format response
        results = []
        for item in items:
            results.append({
                'id': item.id,
                'title': item.title,
                'content': item.content,
                'category': item.category,
            })
        
        response_data = {'results': results}
        
        # Optionally include formatted context
        if include_context:
            response_data['context'] = kb.get_context_for_query(query, category)
        
        return Response(response_data)


@extend_schema(tags=['Settings'])
class RAGChatView(APIView):
    """
    Chat with AI using RAG-enhanced responses.
    Combines knowledge base context with AI generation.
    """
    permission_classes = [IsAuthenticated]  # Require authentication
    serializer_class = RAGChatRequestSerializer
    
    @extend_schema(
        summary='RAG 智能對話 / RAG chat',
        description='使用 RAG 增強的 AI 對話，結合知識庫上下文生成回應。\n\nChat with AI using RAG-enhanced responses with knowledge base context.'
    )
    def post(self, request):
        query = request.data.get('query', '')
        category = request.data.get('category')
        provider = request.data.get('provider', 'openai')
        
        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get context from knowledge base
        kb = get_knowledge_base()
        context = kb.get_context_for_query(query, category)
        
        # Build RAG prompt
        system_prompt = """你是 Wisematic ERP 系統的智能助手，使用 RAG (檢索增強生成) 技術回答問題。

使用說明：
1. 根據提供的參考文件回答用戶問題
2. 如果參考文件包含相關資訊，優先使用文件內容
3. 如果參考文件不足以回答，基於你對 ERP 系統的理解提供幫助
4. 使用繁體中文或英文回應（根據用戶問題的語言）
5. 回答簡潔明瞭"""

        if context:
            system_prompt += f"\n\n參考文件：\n{context}"
        
        # Generate AI response
        try:
            # 將字串 provider 轉換為 AIProvider enum
            from core.libs.ai_service import AIProvider
            provider_enum = AIProvider(provider) if provider else AIProvider.OPENAI
            
            ai_service = AIService(provider=provider_enum)
            response = ai_service.chat(
                message=query,
                system_prompt=system_prompt
            )
            
            return Response({
                'response': response.content,
                'sources': [item.title for item in kb.search(query, top_k=3, category=category)],
                'provider': provider,
            })
        except ValueError as e:
            # Invalid provider
            return Response(
                {'error': f'Invalid provider: {provider}. Use openai, gemini, or deepseek.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印完整錯誤到後端日誌
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Settings'])
class RAGKnowledgeListView(APIView):
    """
    List all items in the knowledge base.
    Useful for displaying help index.
    """
    permission_classes = [AllowAny]
    serializer_class = RAGQueryRequestSerializer
    
    @extend_schema(
        summary='列出知識庫項目 / List knowledge base items',
        description='列出知識庫中的所有項目。\n\nList all items in the knowledge base.'
    )
    def get(self, request):
        category = request.query_params.get('category')
        kb = get_knowledge_base()
        
        items = []
        for item in kb.items.values():
            if category and item.category != category:
                continue
            items.append({
                'id': item.id,
                'title': item.title,
                'category': item.category,
            })
        
        # Group by category
        categories = {}
        for item in items:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                'id': item['id'],
                'title': item['title'],
            })
        
        return Response({
            'items': items,
            'categories': categories,
            'total': len(items),
        })
