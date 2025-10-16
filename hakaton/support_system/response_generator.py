"""
Модуль генерации ответов с использованием RAG (Retrieval-Augmented Generation)
"""

from llm_client import LLMClient
from knowledge_search import KnowledgeBase
from config import GENERATION_PARAMS


class ResponseGenerator:
    """Генератор ответов на основе найденной информации"""
    
    def __init__(self, api_key=None, knowledge_base=None):
        self.llm = LLMClient(api_key=api_key)
        # Используем переданный knowledge_base или создаём новый
        self.kb = knowledge_base if knowledge_base else KnowledgeBase(api_key=api_key)
    
    def generate_response(self, ticket_text, category=None, classification_info=None, search_results=None):
        """
        Находит подходящие шаблоны из базы знаний
        
        Args:
            ticket_text: Текст обращения клиента
            category: Определенная категория (опционально)
            classification_info: Дополнительная информация о классификации
            search_results: Предварительно найденные результаты (оптимизация, чтобы не искать дважды)
            
        Returns:
            dict: {
                'response': str - шаблонный ответ из базы знаний,
                'sources': list - использованные статьи из базы знаний,
                'confidence': str - уверенность в ответе
            }
        """
        # Используем переданные результаты поиска или ищем заново
        if search_results is None:
            search_results = self.kb.search(ticket_text, category_filter=category)
        
        if not search_results:
            # Если ничего не найдено, возвращаем стандартное сообщение
            return {
                'response': "К сожалению, в базе знаний не найдено подходящих шаблонов для данного обращения. Рекомендуется обратиться к специалисту техподдержки.",
                'sources': [],
                'confidence': 'низкая',
                'search_results': []
            }
        
        # Берём шаблонный ответ из наиболее релевантной статьи
        best_match = search_results[0]['article']
        template_answer = best_match.get('template_answer', best_match.get('solution', ''))
        
        # Если шаблонный ответ пустой, берём из следующей статьи
        if not template_answer and len(search_results) > 1:
            for result in search_results[1:]:
                template_answer = result['article'].get('template_answer', result['article'].get('solution', ''))
                if template_answer:
                    break
        
        if not template_answer:
            template_answer = "Шаблонный ответ не найден. Пожалуйста, свяжитесь со специалистом техподдержки."
        
        return {
            'response': template_answer,
            'sources': [r['article'] for r in search_results],
            'confidence': self._assess_confidence(search_results),
            'search_results': search_results
        }
    
    
    def _assess_confidence(self, search_results):
        """Оценивает уверенность в ответе на основе релевантности найденных решений"""
        if not search_results:
            return "низкая"
        
        max_similarity = search_results[0]['similarity']
        
        if max_similarity >= 0.8:
            return "высокая"
        elif max_similarity >= 0.6:
            return "средняя"
        else:
            return "низкая"

