"""
Модуль поиска по базе знаний с использованием векторных представлений
"""

import warnings
import json
import numpy as np
import pandas as pd
from llm_client import LLMClient
from config import SEARCH_TOP_K, SIMILARITY_THRESHOLD

# Подавляем warning от openpyxl о Data Validation
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
import os


class KnowledgeBase:
    """Система поиска по базе знаний с использованием embeddings"""
    
    def __init__(self, knowledge_file='data/smart_support_vtb_belarus_faq_final.xlsx', api_key=None):
        self.llm = LLMClient(api_key=api_key)
        
        # Формируем абсолютный путь к файлу БЗ
        if not os.path.isabs(knowledge_file):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.knowledge_file = os.path.join(base_dir, knowledge_file)
        else:
            self.knowledge_file = knowledge_file
            
        # Формируем абсолютный путь к файлу embeddings
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.embeddings_file = os.path.join(base_dir, 'data/embeddings_cache.npy')
        
        self.articles = []
        self.embeddings = None
        self.query_cache = {}  # Кэш для embeddings запросов
        self.cache_limit = 100  # Ограничение размера кэша
        
        self.load_knowledge_base()
        if self.articles:
            self.load_or_create_embeddings()
    
    def load_knowledge_base(self):
        """Загружает базу знаний из XLSX или JSON файла"""
        if not os.path.exists(self.knowledge_file):
            print(f"[WARNING] Файл базы знаний не найден: {self.knowledge_file}")
            self.articles = []
            return
        
        try:
            # Определяем формат файла
            if self.knowledge_file.endswith('.xlsx'):
                # Загружаем из Excel
                df = pd.read_excel(self.knowledge_file)
                
                # Преобразуем DataFrame в список словарей
                self.articles = []
                for idx, row in df.iterrows():
                    article = {
                        'id': int(row.get('id', idx + 1)),
                        'main_category': str(row.get('main_category', row.get('Основная категория', 'Другое'))),
                        'subcategory': str(row.get('subcategory', row.get('Подкатегория', ''))),
                        'example_question': str(row.get('example_question', row.get('Пример вопроса', ''))),
                        'priority': str(row.get('priority', row.get('Приоритет', 'Средний'))),
                        'target_audience': str(row.get('target_audience', row.get('Целевая аудитория', 'Все'))),
                        'template_answer': str(row.get('template_answer', row.get('Шаблонный ответ', ''))),
                        # Для обратной совместимости
                        'category': str(row.get('main_category', row.get('Основная категория', 'Другое'))),
                        'problem': str(row.get('example_question', row.get('Пример вопроса', ''))),
                        'solution': str(row.get('template_answer', row.get('Шаблонный ответ', '')))
                    }
                    self.articles.append(article)
                
                print(f"[OK] Загружено {len(self.articles)} статей из XLSX файла")
                
            elif self.knowledge_file.endswith('.json'):
                # Загружаем из JSON (обратная совместимость)
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    self.articles = json.load(f)
                print(f"[OK] Загружено {len(self.articles)} статей из JSON файла")
            
            else:
                print(f"[ERROR] Неподдерживаемый формат файла: {self.knowledge_file}")
                self.articles = []
                
        except Exception as e:
            print(f"[ERROR] Ошибка при загрузке базы знаний: {e}")
            self.articles = []
    
    def load_or_create_embeddings(self):
        """Загружает или создает embeddings для базы знаний"""
        # Проверяем, есть ли кэшированные embeddings
        if os.path.exists(self.embeddings_file):
            try:
                self.embeddings = np.load(self.embeddings_file)
                print(f"[OK] Загружены кэшированные embeddings: {self.embeddings.shape}")
                return
            except Exception as e:
                print(f"[WARNING] Не удалось загрузить кэш embeddings: {e}")
        
        # Создаем embeddings для всех статей
        if self.articles:
            print("[INFO] Создание embeddings для базы знаний...")
            # Используем новые поля или fallback на старые
            texts = [
                f"{article.get('example_question', article.get('problem', ''))} "
                f"{article.get('template_answer', article.get('solution', ''))}" 
                for article in self.articles
            ]
            embeddings_list = self.llm.get_embeddings_batch(texts)
            
            if embeddings_list:
                self.embeddings = np.array(embeddings_list)
                # Сохраняем в кэш
                np.save(self.embeddings_file, self.embeddings)
                print(f"[OK] Создано и сохранено {self.embeddings.shape[0]} embeddings")
            else:
                print("[ERROR] Не удалось создать embeddings")
    
    def cosine_similarity(self, vec1, vec2):
        """Вычисляет косинусное сходство между двумя векторами"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2)
    
    def search(self, query, top_k=SEARCH_TOP_K, category_filter=None):
        """
        Ищет релевантные статьи по запросу
        
        Args:
            query: Текст запроса
            top_k: Количество результатов
            category_filter: Фильтр по категории (опционально)
            
        Returns:
            list: Список найденных статей с оценкой релевантности
        """
        if not self.articles or self.embeddings is None:
            return []
        
        # Проверяем кэш embeddings
        import hashlib
        import time
        
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        if query_hash in self.query_cache:
            query_embedding = self.query_cache[query_hash]
            print(f"[CACHE HIT] Embedding взят из кэша")
        else:
            start_time = time.time()
            query_embedding = self.llm.get_embedding(query)
            elapsed = time.time() - start_time
            print(f"[API CALL] Embedding создан: {elapsed:.2f}s")
            
            if query_embedding is None:
                return []
            
            # Сохраняем в кэш
            self.query_cache[query_hash] = query_embedding
            
            # Ограничиваем размер кэша
            if len(self.query_cache) > self.cache_limit:
                # Удаляем самый старый элемент (первый добавленный)
                oldest_key = next(iter(self.query_cache))
                del self.query_cache[oldest_key]
                print(f"[INFO] Кэш очищен, размер: {len(self.query_cache)}")
        
        query_vec = np.array(query_embedding)
        
        # ОПТИМИЗАЦИЯ: Векторизованное вычисление сходства для всех статей сразу
        # Нормализуем векторы
        query_norm = query_vec / np.linalg.norm(query_vec)
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        
        # Вычисляем косинусное сходство для всех статей одновременно
        all_similarities = np.dot(embeddings_norm, query_norm)
        
        # Применяем фильтры
        similarities = []
        for i, similarity in enumerate(all_similarities):
            # Фильтр по порогу схожести
            if similarity < SIMILARITY_THRESHOLD:
                continue
            
            article = self.articles[i]
            
            # Применяем фильтр по категории, если указан (мягкая фильтрация)
            if category_filter:
                article_category = article.get('main_category', article.get('category', ''))
                # Проверяем частичное совпадение (нечувствительно к регистру)
                category_filter_lower = category_filter.lower()
                article_category_lower = article_category.lower()
                
                # Разбиваем на слова для более мягкого сравнения
                filter_words = set(category_filter_lower.split())
                article_words = set(article_category_lower.split())
                
                # Если есть хотя бы одно общее слово - считаем подходящим
                if not (filter_words & article_words):
                    # Нет общих слов - пропускаем только если категории сильно различаются
                    if category_filter_lower not in article_category_lower and article_category_lower not in category_filter_lower:
                        continue
            
            similarities.append({
                'article': article,
                'similarity': float(similarity),
                'rank': len(similarities) + 1
            })
        
        # Сортируем по убыванию схожести
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Возвращаем top_k результатов
        return similarities[:top_k]
    
    def format_search_results(self, results):
        """Форматирует результаты поиска для отображения"""
        if not results:
            return "Релевантных решений не найдено."
        
        formatted = []
        for i, result in enumerate(results, 1):
            article = result['article']
            similarity = result['similarity']
            
            # Используем новые поля с fallback
            main_cat = article.get('main_category', article.get('category', 'Не указано'))
            subcat = article.get('subcategory', '')
            question = article.get('example_question', article.get('problem', ''))
            answer = article.get('template_answer', article.get('solution', ''))
            priority = article.get('priority', 'Средний')
            audience = article.get('target_audience', 'Все')
            
            formatted.append(f"""
{'='*60}
Результат #{i} (релевантность: {similarity:.2%})
Основная категория: {main_cat}
Подкатегория: {subcat}
Приоритет: {priority}
Целевая аудитория: {audience}

Пример вопроса:
{question}

Шаблонный ответ:
{answer}
{'='*60}
""")
        
        return "\n".join(formatted)

