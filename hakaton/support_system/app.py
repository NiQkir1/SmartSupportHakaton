"""
Веб-приложение системы технической поддержки
"""

from flask import Flask, render_template, request, jsonify, session
from classifier import TicketClassifier
from response_generator import ResponseGenerator
from knowledge_search import KnowledgeBase
from anglicism_normalizer import get_normalizer
from feedback_system import get_feedback_system
from text_extractor import get_text_extractor
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # Для сессий

# Глобальные переменные для модулей (будут инициализированы после ввода токена)
classifier = None
response_gen = None
knowledge_base = None

# История обработанных обращений
tickets_history = []


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/init', methods=['POST'])
def initialize_system():
    """Инициализация системы с API ключом"""
    global classifier, response_gen, knowledge_base
    
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({'error': 'API ключ не может быть пустым'}), 400
        
        # Сначала проверяем валидность ключа
        try:
            from llm_client import LLMClient
            test_client = LLMClient(api_key=api_key)
            is_valid, error_message = test_client.validate_key()
            
            if not is_valid:
                return jsonify({
                    'error': error_message or 'Неверный API ключ'
                }), 401
        except Exception as e:
            return jsonify({
                'error': f'Ошибка при проверке API ключа: {str(e)}'
            }), 500
        
        # Если ключ валидный - инициализируем модули
        try:
            knowledge_base = KnowledgeBase(api_key=api_key)
            classifier = TicketClassifier(api_key=api_key, knowledge_base=knowledge_base)
            response_gen = ResponseGenerator(api_key=api_key, knowledge_base=knowledge_base)
            
            # Сохраняем в сессию
            session['initialized'] = True
            session['api_key'] = api_key
            
            return jsonify({
                'success': True,
                'message': 'Система успешно инициализирована',
                'articles_count': len(knowledge_base.articles) if knowledge_base else 0
            })
        except Exception as e:
            return jsonify({
                'error': f'Ошибка при инициализации: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check_init')
def check_initialization():
    """Проверка инициализации системы"""
    is_initialized = session.get('initialized', False) and classifier is not None
    return jsonify({
        'initialized': is_initialized,
        'articles_count': len(knowledge_base.articles) if knowledge_base and knowledge_base.articles else 0
    })

@app.route('/api/version')
def get_version():
    """Получение версии приложения из файла VERSION"""
    try:
        version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
        return jsonify({'version': version})
    except Exception as e:
        return jsonify({'version': '2.0.1', 'error': str(e)})


@app.route('/api/process_ticket', methods=['POST'])
def process_ticket():
    """
    API endpoint для обработки обращения клиента
    
    Принимает JSON: {"ticket_text": "текст обращения"}
    Возвращает полный анализ и предложенный ответ
    """
    # Проверяем инициализацию
    if not classifier or not response_gen or not knowledge_base:
        return jsonify({'error': 'Система не инициализирована. Введите API ключ.'}), 400
    
    try:
        data = request.get_json()
        ticket_text = data.get('ticket_text', '').strip()
        
        if not ticket_text:
            return jsonify({'error': 'Текст обращения не может быть пустым'}), 400
        
        # Нормализация англицизмов
        normalizer = get_normalizer()
        normalized_text, changes = normalizer.normalize_with_log(ticket_text)
        
        # Логируем изменения если они есть
        if changes:
            print(f"[ANGLICISM] Нормализация: {', '.join(changes)}")
        
        # Оптимизация текста для embedding
        text_extractor = get_text_extractor()
        optimized_text, optimization_stats = text_extractor.optimize_for_embedding(normalized_text)
        
        # Логируем оптимизацию если она была
        if optimization_stats['was_optimized']:
            print(f"[OPTIMIZATION] Текст оптимизирован: {optimization_stats['original_tokens']} → {optimization_stats['optimized_tokens']} токенов "
                  f"(сжатие: {optimization_stats['compression_ratio']:.2%})")
        
        # Начало замера общего времени
        import time
        total_start = time.time()
        
        # ОПТИМИЗАЦИЯ: Классификация + извлечение за ОДИН вызов
        start_classify = time.time()
        
        try:
            # Используем оптимизированный текст для классификации
            result = classifier.classify_and_extract(optimized_text)
            
            # Проверяем, не вернулась ли ошибка перегрузки
            if isinstance(result, dict) and 'error' in result:
                if result['error'] in ['rate_limit', 'max_retries_exceeded']:
                    return jsonify({
                        'error': 'rate_limit',
                        'message': result['message'],
                        'attempts': result.get('attempts', 0),
                        'retry_available': True
                    }), 429
            
            classification = {
                'category': result['category'],
                'confidence': result['confidence'],
                'reasoning': result['reasoning']
            }
            key_info = result['key_info']
            
            print(f"[TIMING] Классификация+извлечение: {time.time() - start_classify:.2f}s")
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                return jsonify({
                    'error': 'rate_limit',
                    'message': 'API временно перегружен. Пожалуйста, попробуйте через минуту.',
                    'retry_available': True
                }), 429
            else:
                return jsonify({
                    'error': f'Ошибка классификации: {str(e)}'
                }), 500
        
        # Шаг 2: Поиск релевантных решений (используем нормализованный текст)
        start_search = time.time()
        
        # Сначала пробуем с фильтром по категории
        search_results_filtered = knowledge_base.search(
            optimized_text, 
            category_filter=classification.get('category')
        )
        
        # Если результаты с фильтром плохие (низкое совпадение или мало результатов), 
        # ищем без фильтра и используем лучший результат
        best_similarity_filtered = search_results_filtered[0]['similarity'] if search_results_filtered else 0
        
        if not search_results_filtered or best_similarity_filtered < 0.6:
            if search_results_filtered:
                print(f"[SEARCH] Низкое совпадение с фильтром ({best_similarity_filtered*100:.0f}%), пробуем без фильтра...")
            else:
                print(f"[SEARCH] Нет результатов с фильтром, пробуем без фильтра...")
            
            search_results_all = knowledge_base.search(optimized_text, category_filter=None)
            
            # Если без фильтра результаты лучше - используем их
            if search_results_all:
                best_similarity_all = search_results_all[0]['similarity']
                if not search_results_filtered or best_similarity_all > best_similarity_filtered:
                    print(f"[SEARCH] Используем результаты БЕЗ фильтра (лучшее совпадение: {best_similarity_all*100:.0f}%)")
                    search_results = search_results_all
                else:
                    search_results = search_results_filtered
            else:
                search_results = search_results_filtered
        else:
            search_results = search_results_filtered
        
        # Переранжирование результатов с учетом feedback
        feedback_system = get_feedback_system()
        search_results = feedback_system.rerank_results(search_results)
        
        print(f"[TIMING] Поиск в БЗ: {time.time() - start_search:.2f}s")
        
        # Определяем срочность/приоритет из найденного шаблона (лучшее совпадение)
        priority_from_kb = 'Средний'  # По умолчанию
        subcategories_from_kb = []  # Собираем подкатегории из найденных статей
        
        if search_results and len(search_results) > 0:
            best_match = search_results[0]['article']
            priority_from_kb = best_match.get('priority', 'Средний')
            
            # Собираем уникальные подкатегории из всех найденных статей
            unique_subcats = set()
            for result in search_results:
                article = result['article']
                subcat = article.get('subcategory', '')
                if subcat and subcat != 'nan' and subcat.strip():
                    unique_subcats.add(subcat.strip())
            
            subcategories_from_kb = sorted(list(unique_subcats))
        
        # Заменяем срочность из LLM на приоритет из БЗ
        key_info['urgency'] = priority_from_kb
        
        # Добавляем подкатегории в классификацию
        if subcategories_from_kb:
            classification['subcategories'] = subcategories_from_kb
            classification['subcategory'] = ', '.join(subcategories_from_kb)  # Для совместимости
            print(f"[SUBCATEGORIES] Найдены подкатегории: {subcategories_from_kb}")
        else:
            print(f"[SUBCATEGORIES] Подкатегории не найдены в результатах поиска")
        
        # Шаг 3: Генерация ответа (используем уже найденные результаты)
        start_gen = time.time()
        response_data = response_gen.generate_response(
            optimized_text,
            category=classification.get('category'),
            classification_info=classification,
            search_results=search_results  # Передаём уже найденные результаты
        )
        
        # Проверяем на ошибку перегрузки
        if isinstance(response_data, dict) and 'error' in response_data:
            if response_data['error'] in ['rate_limit', 'max_retries_exceeded']:
                return jsonify({
                    'error': 'rate_limit',
                    'message': response_data['message'],
                    'attempts': response_data.get('attempts', 0),
                    'retry_available': True
                }), 429
        
        print(f"[TIMING] Генерация ответа: {time.time() - start_gen:.2f}s")
        
        # Формируем результат
        result = {
            'ticket_text': ticket_text,
            'normalized_text': normalized_text if changes else None,
            'optimized_text': optimized_text if optimization_stats['was_optimized'] else None,
            'anglicism_changes': changes if changes else None,
            'optimization_stats': optimization_stats if optimization_stats['was_optimized'] else None,
            'classification': classification,
            'key_info': key_info,
            'suggested_response': response_data['response'],
            'confidence': response_data['confidence'],
            'sources': [
                {
                    'id': s.get('id'),
                    'main_category': s.get('main_category', s.get('category', '')),
                    'subcategory': s.get('subcategory', ''),
                    'example_question': s.get('example_question', s.get('problem', '')),
                    'template_answer': s.get('template_answer', s.get('solution', '')),
                    'priority': s.get('priority', 'Средний'),
                    'target_audience': s.get('target_audience', 'Все')
                }
                for s in response_data['sources']
            ],
            'search_results': [
                {
                    'similarity': r['similarity'],
                    'article': r['article'],
                    'article_id': r.get('article_id', ''),
                    'feedback_bonus': r.get('feedback_bonus', 0),
                    'feedback_stats': r.get('feedback_stats', {'helpful': 0, 'total': 0, 'rate': 0})
                }
                for r in response_data.get('search_results', [])
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        # Сохраняем в историю
        tickets_history.append(result)
        
        # Итоговое время обработки
        total_time = time.time() - total_start
        print(f"\n{'='*60}")
        print(f"[TOTAL] Обработка запроса: {total_time:.2f}s")
        print(f"{'='*60}\n")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке обращения: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search_knowledge():
    """
    API endpoint для поиска по базе знаний
    
    Принимает JSON: {"query": "поисковый запрос", "category": "категория (опционально)"}
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        category = data.get('category')
        
        if not query:
            return jsonify({'error': 'Поисковый запрос не может быть пустым'}), 400
        
        results = knowledge_base.search(query, category_filter=category)
        
        formatted_results = [
            {
                'similarity': r['similarity'],
                'article': r['article']
            }
            for r in results
        ]
        
        return jsonify({'results': formatted_results})
    
    except Exception as e:
        print(f"[ERROR] Ошибка при поиске: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history')
def get_history():
    """Получить историю обработанных обращений"""
    return jsonify({'history': tickets_history[-20:]})  # Последние 20


@app.route('/api/categories')
def get_categories():
    """Получить список доступных категорий"""
    from config import CATEGORIES
    return jsonify({'categories': CATEGORIES})


@app.route('/api/stats')
def get_stats():
    """Получить статистику"""
    if not tickets_history:
        return jsonify({
            'total_tickets': 0,
            'categories_distribution': {},
            'avg_confidence': 0
        })
    
    # Подсчет статистики
    categories_count = {}
    confidences = []
    
    for ticket in tickets_history:
        category = ticket['classification'].get('category', 'Другое')
        categories_count[category] = categories_count.get(category, 0) + 1
        
        conf = ticket.get('confidence', 'средняя')
        confidences.append(conf)
    
    return jsonify({
        'total_tickets': len(tickets_history),
        'categories_distribution': categories_count,
        'confidence_distribution': {
            'высокая': confidences.count('высокая'),
            'средняя': confidences.count('средняя'),
            'низкая': confidences.count('низкая')
        }
    })


@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """
    API endpoint для получения обратной связи о полезности шаблона
    
    Принимает JSON: {
        "article_id": "уникальный ID статьи",
        "query": "исходный запрос пользователя",
        "is_helpful": true
    }
    """
    try:
        data = request.get_json()
        article_id = data.get('article_id', '').strip()
        query = data.get('query', '').strip()
        is_helpful = data.get('is_helpful', True)
        
        if not article_id:
            return jsonify({'error': 'article_id обязателен'}), 400
        
        if not query:
            return jsonify({'error': 'query обязателен'}), 400
        
        # Добавляем feedback
        feedback_system = get_feedback_system()
        feedback_system.add_feedback(article_id, query, is_helpful)
        
        # Получаем обновленную статистику
        stats = feedback_system.get_statistics()
        
        return jsonify({
            'success': True,
            'message': 'Спасибо за обратную связь!',
            'stats': stats
        })
    
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке feedback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/feedback/stats')
def get_feedback_stats():
    """Получить статистику обратной связи"""
    try:
        feedback_system = get_feedback_system()
        stats = feedback_system.get_statistics()
        return jsonify(stats)
    except Exception as e:
        print(f"[ERROR] Ошибка при получении статистики feedback: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" Система технической поддержки с AI")
    print("="*70)
    print("\n[INFO] Запуск веб-сервера...")
    print("[INFO] Откройте в браузере: http://localhost:5000")
    print("\n[Ctrl+C для остановки]\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

