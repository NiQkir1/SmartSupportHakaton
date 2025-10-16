"""
Модуль классификации обращений клиентов
"""

from llm_client import LLMClient
from config import CATEGORIES
import json


class TicketClassifier:
    """Классификатор обращений на основе LLM"""
    
    def __init__(self, api_key=None, knowledge_base=None):
        self.llm = LLMClient(api_key=api_key)
        self.knowledge_base = knowledge_base
        
        # Кэш для классификации (хэш запроса -> результат)
        self.classification_cache = {}
        self.cache_max_size = 100  # Максимум 100 запросов в кэше
        
        # Загружаем категории и подкатегории из БЗ если доступна
        if knowledge_base and knowledge_base.articles:
            unique_categories = set()
            self.category_subcategories = {}  # категория -> список подкатегорий
            
            for article in knowledge_base.articles:
                cat = article.get('main_category', article.get('category', ''))
                subcat = article.get('subcategory', '')
                
                if cat:
                    unique_categories.add(cat)
                    if subcat:
                        if cat not in self.category_subcategories:
                            self.category_subcategories[cat] = set()
                        self.category_subcategories[cat].add(subcat)
            
            self.categories = sorted(list(unique_categories)) if unique_categories else CATEGORIES
            
            # Преобразуем множества в списки
            for cat in self.category_subcategories:
                self.category_subcategories[cat] = sorted(list(self.category_subcategories[cat]))
        else:
            self.categories = CATEGORIES
            self.category_subcategories = {}
    
    def classify(self, ticket_text):
        """
        Классифицирует обращение клиента
        
        Args:
            ticket_text: Текст обращения клиента
            
        Returns:
            dict: {
                'category': str - определенная категория,
                'confidence': str - уверенность в классификации,
                'reasoning': str - обоснование выбора категории
            }
        """
        categories_str = "\n".join([f"- {cat}" for cat in self.categories])
        
        prompt = f"""Ты - опытный специалист службы поддержки. Проанализируй обращение клиента и определи его категорию.

Доступные категории:
{categories_str}

Обращение клиента:
"{ticket_text}"

Ответь в формате JSON:
{{
    "category": "название категории из списка",
    "confidence": "высокая/средняя/низкая",
    "reasoning": "краткое объяснение, почему выбрана эта категория"
}}

Будь точным и выбирай наиболее подходящую категорию."""

        messages = [
            {"role": "system", "content": "Ты - система классификации обращений технической поддержки."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate_response(messages, temperature=0.2, max_tokens=300)
        
        if response:
            try:
                # Извлекаем JSON из ответа
                # Иногда модель может добавить текст до/после JSON
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    return result
            except json.JSONDecodeError as e:
                print(f"[ERROR] Ошибка парсинга JSON: {e}")
                print(f"Response: {response}")
        
        # Fallback: возвращаем категорию "Другое"
        return {
            "category": "Другое",
            "confidence": "низкая",
            "reasoning": "Не удалось автоматически определить категорию"
        }
    
    def extract_key_info(self, ticket_text):
        """
        Извлекает ключевую информацию из обращения
        
        Args:
            ticket_text: Текст обращения
            
        Returns:
            dict: Ключевая информация (проблема, детали, эмоциональная окраска)
        """
        prompt = f"""Проанализируй обращение клиента и извлеки ключевую информацию.

Обращение:
"{ticket_text}"

Ответь в формате JSON:
{{
    "main_issue": "краткое описание основной проблемы",
    "urgency": "срочно/обычно/не срочно",
    "sentiment": "позитивное/нейтральное/негативное",
    "key_details": ["список", "важных", "деталей"]
}}"""

        messages = [
            {"role": "system", "content": "Ты - аналитик службы поддержки."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate_response(messages, temperature=0.2, max_tokens=400)
        
        if response:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return {
            "main_issue": "Не удалось извлечь",
            "urgency": "обычно",
            "sentiment": "нейтральное",
            "key_details": []
        }
    
    def classify_and_extract(self, ticket_text):
        """
        ОПТИМИЗИРОВАННЫЙ МЕТОД: Классификация + извлечение информации за ОДИН вызов LLM
        С КЭШИРОВАНИЕМ для ускорения повторных запросов
        
        Экономия: ~1-3 секунды по сравнению с отдельными вызовами classify() и extract_key_info()
        Кэш: моментальный ответ для повторных/похожих запросов
        
        Args:
            ticket_text: Текст обращения клиента
            
        Returns:
            dict: {
                'category': str,
                'confidence': str,
                'reasoning': str,
                'key_info': {
                    'main_issue': str,
                    'urgency': str,
                    'sentiment': str,
                    'key_details': list
                }
            }
        """
        import time
        import hashlib
        
        # Проверяем кэш
        cache_key = hashlib.md5(ticket_text.lower().strip().encode('utf-8')).hexdigest()
        
        if cache_key in self.classification_cache:
            print(f"[CACHE HIT] Классификация взята из кэша (~0.00s)")
            return self.classification_cache[cache_key].copy()
        
        start_time = time.time()
        
        # Формируем строку категорий с подкатегориями
        categories_info = []
        for cat in self.categories:
            if cat in self.category_subcategories and self.category_subcategories[cat]:
                subcats = ", ".join(self.category_subcategories[cat])
                categories_info.append(f"{cat} ({subcats})")
            else:
                categories_info.append(cat)
        
        categories_str = "; ".join(categories_info)
        
        prompt = f"""Категории: {categories_str}
Запрос: "{ticket_text}"
JSON: {{"category": "...", "subcategory": "..." (если применимо), "confidence": "высокая/средняя/низкая", "reasoning": "...", "key_info": {{"main_issue": "...", "urgency": "обычно", "sentiment": "нейтральное", "key_details": []}}}}"""

        messages = [
            {"role": "system", "content": "Классификация. JSON only. Всегда возвращай подкатегорию если она подходит."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate_response(messages, temperature=0.1, max_tokens=300)
        
        # Проверяем, не вернулась ли ошибка перегрузки
        if isinstance(response, dict) and 'error' in response:
            return response  # Возвращаем ошибку для обработки выше
        
        if response:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    
                    elapsed = time.time() - start_time
                    print(f"[FAST] classify_and_extract: {elapsed:.2f}s")
                    
                    # Сохраняем в кэш
                    self.classification_cache[cache_key] = result.copy()
                    
                    # Ограничиваем размер кэша
                    if len(self.classification_cache) > self.cache_max_size:
                        # Удаляем самый старый элемент
                        oldest_key = next(iter(self.classification_cache))
                        del self.classification_cache[oldest_key]
                    
                    return result
            except json.JSONDecodeError as e:
                print(f"[WARNING] JSON parse error: {e}")
        
        # Fallback
        elapsed = time.time() - start_time
        print(f"[⚠️ FALLBACK] classify_and_extract: {elapsed:.2f}s")
        
        return {
            "category": "Другое",
            "confidence": "низкая",
            "reasoning": "Не удалось определить",
            "key_info": {
                "main_issue": ticket_text[:100],
                "urgency": "обычно",
                "sentiment": "нейтральное",
                "key_details": []
            }
        }

