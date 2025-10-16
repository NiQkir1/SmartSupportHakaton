"""
Модуль извлечения ключевой информации из текста для оптимизации embedding
"""

import re
from typing import List, Dict, Tuple
from config import MAX_QUERY_TOKENS, TOKENS_PER_CHAR


class TextExtractor:
    """Извлекает ключевую информацию из текста, удаляя стоп-слова и неважные фразы"""
    
    def __init__(self):
        # Стоп-слова для русского языка
        self.stop_words = {
            # Приветствия и вежливость
            'добрый', 'день', 'вечер', 'утро', 'здравствуйте', 'привет', 'спасибо', 'пожалуйста',
            'извините', 'простите', 'благодарю', 'спасибо', 'пожалуйста',
            
            # Местоимения и предлоги
            'я', 'мне', 'меня', 'мной', 'мы', 'нам', 'нас', 'нами', 'вы', 'вам', 'вас', 'вами',
            'он', 'она', 'оно', 'они', 'его', 'её', 'их', 'ему', 'ей', 'им', 'его', 'её', 'их',
            'в', 'на', 'с', 'со', 'из', 'от', 'до', 'для', 'при', 'по', 'за', 'под', 'над', 'между',
            'к', 'ко', 'у', 'о', 'об', 'про', 'через', 'без', 'кроме', 'вместо', 'вокруг', 'около',
            
            # Союзы и частицы
            'и', 'а', 'но', 'или', 'либо', 'что', 'чтобы', 'как', 'так', 'же', 'ли', 'бы', 'б',
            'не', 'ни', 'уже', 'еще', 'ещё', 'только', 'лишь', 'даже', 'хоть', 'хотя',
            
            # Частые глаголы (не несущие смысловой нагрузки)
            'есть', 'быть', 'был', 'была', 'было', 'были', 'будет', 'будут', 'стать', 'стал',
            'стала', 'стало', 'стали', 'станет', 'станут', 'иметь', 'имею', 'имеешь', 'имеет',
            'имеем', 'имеете', 'имеют', 'имел', 'имела', 'имело', 'имели',
            
            # Слова-паразиты
            'ну', 'вот', 'это', 'эта', 'этот', 'эти', 'такой', 'такая', 'такое', 'такие',
            'какой', 'какая', 'какое', 'какие', 'который', 'которая', 'которое', 'которые',
            'свой', 'своя', 'свое', 'свои', 'мой', 'моя', 'мое', 'мои', 'твой', 'твоя', 'твое', 'твои',
            
            # Временные указатели (не всегда важны)
            'сегодня', 'вчера', 'завтра', 'сейчас', 'теперь', 'потом', 'позже', 'раньше',
            'всегда', 'никогда', 'иногда', 'часто', 'редко', 'обычно',
            
            # Общие слова
            'вещь', 'дело', 'вопрос',  'ситуация', 'случай', 'момент', 'время',
            'место', 'дом', 'работа', 'жизнь', 'человек', 'люди'
        }
        
        # Паттерны для удаления
        self.removal_patterns = [
            r'добрый\s+(день|вечер|утро)',
            r'здравствуйте\s*[!.]*',
            r'спасибо\s+(за\s+)?(что\s+)?(помощь|ответ|внимание)?',
            r'пожалуйста\s*[!.]*',
            r'извините\s+(за\s+)?(что\s+)?(беспокойство|неудобство)?',
            r'благодарю\s+(за\s+)?(что\s+)?(помощь|ответ|внимание)?',
            r'очень\s+(много|большое|большой|большая|большое)\s+спасибо',
            r'заранее\s+спасибо',
            r'с\s+уважением\s*[,.]*',
            r'до\s+свидания\s*[!.]*',
            r'всего\s+(хорошего|доброго)\s*[!.]*',
        ]
        
        # Компилируем паттерны для быстрого поиска
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.UNICODE) 
                                 for pattern in self.removal_patterns]
    
    def extract_key_information(self, text: str, max_tokens: int = MAX_QUERY_TOKENS) -> str:
        """
        Извлекает ключевую информацию из текста
        
        Args:
            text: Исходный текст
            max_tokens: Максимальное количество токенов в результате
            
        Returns:
            str: Оптимизированный текст с ключевой информацией
        """
        if not text or not text.strip():
            return text
        
        # Если текст короткий - возвращаем как есть
        if len(text.split()) <= 10:
            return text
        
        # Шаг 1: Удаляем вежливые фразы и приветствия
        cleaned_text = self._remove_polite_phrases(text)
        
        # Шаг 2: Извлекаем ключевые фразы (более консервативно)
        key_phrases = self._extract_key_phrases(cleaned_text)
        
        # Шаг 3: Объединяем и ограничиваем длину
        result = self._combine_and_limit(key_phrases, max_tokens)
        
        return result
    
    def _remove_polite_phrases(self, text: str) -> str:
        """Удаляет вежливые фразы и приветствия"""
        cleaned = text
        
        for pattern in self.compiled_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Удаляем множественные пробелы и знаки препинания в начале/конце
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'^[,\s!.-]+|[,\s!.-]+$', '', cleaned)
        
        return cleaned.strip()
    
    def _remove_stop_words(self, text: str) -> str:
        """Удаляет стоп-слова из текста"""
        words = text.split()
        filtered_words = []
        
        for word in words:
            # Очищаем слово от знаков препинания
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Пропускаем только самые частые стоп-слова, сохраняем важные слова
            if clean_word not in self.stop_words or len(clean_word) <= 2:
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Извлекает ключевые фразы из текста"""
        if not text:
            return []
        
        # Если текст короткий - возвращаем его целиком
        if len(text.split()) <= 15:
            return [text]
        
        # Разбиваем на предложения
        sentences = re.split(r'[.!?]+', text)
        key_phrases = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence.split()) < 3:
                continue
            
            # Ищем фразы с финансовыми терминами
            financial_terms = [
                'карт', 'банк', 'счет', 'вклад', 'кредит', 'перевод', 'платеж', 'оплата',
                'снятие', 'пополнение', 'блокировка', 'разблокировка', 'пароль', 'пин',
                'онлайн', 'мобильное', 'приложение', 'банкомат', 'терминал', 'комиссия',
                'баланс', 'выписка', 'договор', 'паспорт', 'документ', 'подтверждение', 'все про все',
                'PLAT/ON','Signature','КС','ЧЕРЕПАХА','Отличник','Портмоне','Форсаж', 'все только начинается'
            ]
            
            # Если предложение содержит финансовые термины - оно важное
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in financial_terms):
                key_phrases.append(sentence)
            # Или если предложение короткое и информативное
            elif len(sentence.split()) <= 8 and len(sentence) > 15:
                key_phrases.append(sentence)
        
        # Если ничего не нашли - возвращаем весь текст
        if not key_phrases:
            return [text]
        
        return key_phrases
    
    def _combine_and_limit(self, phrases: List[str], max_tokens: int) -> str:
        """Объединяет фразы и ограничивает длину"""
        if not phrases:
            return ""
        
        # Сортируем фразы по длине (короткие сначала)
        phrases.sort(key=len)
        
        result = ""
        max_chars = max_tokens * TOKENS_PER_CHAR
        
        for phrase in phrases:
            if len(result + " " + phrase) <= max_chars:
                if result:
                    result += " " + phrase
                else:
                    result = phrase
            else:
                break
        
        return result
    
    def optimize_for_embedding(self, text: str) -> Tuple[str, Dict]:
        """
        Оптимизирует текст для embedding с возвратом статистики
        
        Args:
            text: Исходный текст
            
        Returns:
            Tuple[str, Dict]: (оптимизированный текст, статистика изменений)
        """
        if not text:
            return text, {}
        
        original_length = len(text)
        original_tokens = len(text.split())
        
        optimized = self.extract_key_information(text)
        
        optimized_length = len(optimized)
        optimized_tokens = len(optimized.split())
        
        stats = {
            'original_length': original_length,
            'optimized_length': optimized_length,
            'original_tokens': original_tokens,
            'optimized_tokens': optimized_tokens,
            'compression_ratio': optimized_length / original_length if original_length > 0 else 1.0,
            'tokens_saved': original_tokens - optimized_tokens,
            'was_optimized': optimized_length < original_length
        }
        
        return optimized, stats


# Глобальный экземпляр для использования в других модулях
_text_extractor = None


def get_text_extractor() -> TextExtractor:
    """Получить глобальный экземпляр TextExtractor"""
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = TextExtractor()
    return _text_extractor


def extract_key_information(text: str, max_tokens: int = MAX_QUERY_TOKENS) -> str:
    """
    Удобная функция для извлечения ключевой информации
    
    Args:
        text: Исходный текст
        max_tokens: Максимальное количество токенов
        
    Returns:
        str: Оптимизированный текст
    """
    return get_text_extractor().extract_key_information(text, max_tokens)


# Тестирование
if __name__ == '__main__':
    extractor = TextExtractor()
    
    test_cases = [
        "Добрый день! У меня проблема с картой MORE. Не могу снять деньги в банкомате.",
        "Здравствуйте! Спасибо за помощь. У меня заблокировалась карта вчера вечером, когда я пытался оплатить покупку в магазине. Очень расстроен, нужны деньги срочно.",
        "Привет! Как дела? Хочу оформить новую карту, но не знаю какую выбрать. Можете посоветовать?",
        "Извините за беспокойство, но у меня не работает вход в онлайн-банк. Забыл пароль, что делать?",
        "Благодарю за ответ! У меня вопрос про вклад - какие проценты сейчас?",
    ]
    
    print("Тестирование извлечения ключевой информации:")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nТест {i}:")
        print(f"Исходный: {test}")
        
        optimized, stats = extractor.optimize_for_embedding(test)
        print(f"Оптимизированный: {optimized}")
        print(f"Статистика: {stats}")
        print("-" * 40)
