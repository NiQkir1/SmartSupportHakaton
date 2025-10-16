"""
Система обратной связи для непрерывного обучения
Хранит статистику полезности шаблонов и использует её для улучшения ранжирования
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class FeedbackSystem:
    def __init__(self, feedback_file='data/feedback_stats.json'):
        self.feedback_file = feedback_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Загрузка статистики из файла"""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[FEEDBACK] Ошибка загрузки статистики: {e}")
                return self._init_stats()
        return self._init_stats()
    
    def _init_stats(self) -> Dict:
        """Инициализация пустой статистики"""
        return {
            'templates': {},  # article_id -> {helpful: int, total: int}
            'history': []     # История feedback
        }
    
    def _save_stats(self):
        """Сохранение статистики в файл"""
        try:
            os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
            print(f"[FEEDBACK] Статистика сохранена: {len(self.stats['templates'])} шаблонов")
        except Exception as e:
            print(f"[FEEDBACK] Ошибка сохранения: {e}")
    
    def add_feedback(self, article_id: str, query: str, is_helpful: bool = True):
        """
        Добавление отзыва о шаблоне
        
        Args:
            article_id: ID статьи (используем question + answer для уникальности)
            query: Исходный запрос пользователя
            is_helpful: Был ли шаблон полезен
        """
        # Инициализация статистики для шаблона если её нет
        if article_id not in self.stats['templates']:
            self.stats['templates'][article_id] = {
                'helpful': 0,
                'total': 0,
                'first_seen': datetime.now().isoformat()
            }
        
        # Обновление счетчиков
        self.stats['templates'][article_id]['total'] += 1
        if is_helpful:
            self.stats['templates'][article_id]['helpful'] += 1
        
        # Добавление в историю
        self.stats['history'].append({
            'article_id': article_id,
            'query': query,
            'is_helpful': is_helpful,
            'timestamp': datetime.now().isoformat()
        })
        
        # Ограничиваем историю последними 1000 записями
        if len(self.stats['history']) > 1000:
            self.stats['history'] = self.stats['history'][-1000:]
        
        self._save_stats()
        
        helpful = self.stats['templates'][article_id]['helpful']
        total = self.stats['templates'][article_id]['total']
        print(f"[FEEDBACK] Шаблон {article_id[:50]}... отмечен как {'полезный' if is_helpful else 'неполезный'}")
        print(f"[FEEDBACK] Статистика: {helpful}/{total} ({helpful/total*100:.1f}% полезных)")
    
    def get_template_score(self, article_id: str) -> float:
        """
        Получение бонусного скора для шаблона на основе feedback
        
        Returns:
            float: Бонус к similarity (0.0 - 0.15)
        """
        if article_id not in self.stats['templates']:
            return 0.0
        
        stats = self.stats['templates'][article_id]
        helpful = stats['helpful']
        total = stats['total']
        
        # Минимум 3 отзыва для учета статистики
        if total < 3:
            return 0.0
        
        # Расчет процента полезности
        helpfulness_rate = helpful / total
        
        # Бонус от 0 до 0.15 в зависимости от процента и количества отзывов
        # Больше отзывов = больше уверенность = больше бонус
        confidence_multiplier = min(total / 10, 1.0)  # Максимум при 10+ отзывах
        bonus = helpfulness_rate * 0.15 * confidence_multiplier
        
        return bonus
    
    def rerank_results(self, search_results: List[Dict]) -> List[Dict]:
        """
        Переранжирование результатов поиска с учетом feedback
        
        Args:
            search_results: Список результатов поиска с similarity
            
        Returns:
            List[Dict]: Переранжированный список
        """
        for result in search_results:
            article = result['article']
            
            # Создаем уникальный ID на основе вопроса и ответа
            question = article.get('example_question', article.get('problem', ''))
            answer = article.get('template_answer', article.get('solution', ''))
            article_id = f"{question[:100]}_{answer[:100]}"
            
            # Получаем бонус на основе feedback
            feedback_bonus = self.get_template_score(article_id)
            
            # Сохраняем оригинальную similarity
            result['original_similarity'] = result['similarity']
            
            # Добавляем бонус
            result['similarity'] = min(result['similarity'] + feedback_bonus, 1.0)
            result['feedback_bonus'] = feedback_bonus
            result['article_id'] = article_id
            
            # Добавляем статистику в результат
            if article_id in self.stats['templates']:
                stats = self.stats['templates'][article_id]
                result['feedback_stats'] = {
                    'helpful': stats['helpful'],
                    'total': stats['total'],
                    'rate': stats['helpful'] / stats['total'] if stats['total'] > 0 else 0
                }
            else:
                result['feedback_stats'] = {
                    'helpful': 0,
                    'total': 0,
                    'rate': 0
                }
        
        # Пересортировка по новой similarity
        search_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return search_results
    
    def get_statistics(self) -> Dict:
        """Получение общей статистики"""
        total_templates = len(self.stats['templates'])
        total_feedback = sum(t['total'] for t in self.stats['templates'].values())
        total_helpful = sum(t['helpful'] for t in self.stats['templates'].values())
        
        return {
            'total_templates_rated': total_templates,
            'total_feedback': total_feedback,
            'total_helpful': total_helpful,
            'helpfulness_rate': total_helpful / total_feedback if total_feedback > 0 else 0,
            'history_size': len(self.stats['history'])
        }


# Глобальный экземпляр для использования в приложении
_feedback_system = None

def get_feedback_system() -> FeedbackSystem:
    """Получение единственного экземпляра FeedbackSystem"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system

