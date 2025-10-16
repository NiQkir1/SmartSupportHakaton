"""
Модуль нормализации англицизмов в запросах клиентов
Преобразует англицизмы и неправильные написания к стандартным терминам
"""

import re


class AnglicismNormalizer:
    """Нормализатор англицизмов и сокращений"""
    
    def __init__(self):
        # Словарь англицизмов и вариантов написания
        # Формат: паттерн -> стандартное значение
        self.replacements = {
            # Карта MORE - сначала обрабатываем сложные фразы, потом простые
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(море|мор)\b': lambda m: f'{m.group(1)} карту MORE',
            r'\b(карт[ауе]?\s+)(море|мор)\b': 'карту MORE',
            r'\b(я\s+хочу|хочу)\s+(море|мор)\b': lambda m: f'{m.group(1)} карту MORE',
            r'\b(море|мор)(?!\s*MORE)\b': 'карту MORE',
            
            # Карта Infinite
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(инфинит[иы]|infinity)\b': lambda m: f'{m.group(1)} карту Infinite',
            r'\b(карт[ауе]?\s+)?(инфинит[иы]|infinity)\b': 'карту Infinite',
            r'\b(я\s+хочу|хочу)\s+(инфинит[иы]|infinity)\b': lambda m: f'{m.group(1)} карту Infinite',
            
            # Карта PLAT/ON (Платон)
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(платон|plat[\/\-]?on)\b': lambda m: f'{m.group(1)} карту PLAT/ON',
            r'\b(карт[ауе]?\s+)?(платон|plat[\/\-]?on)\b': 'карту PLAT/ON',
            r'\b(я\s+хочу|хочу)\s+(платон|plat[\/\-]?on)\b': lambda m: f'{m.group(1)} карту PLAT/ON',
            
            # Карта Signature (Сигнатур)
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(сигнатур[ауеыой]*|signature)\b': lambda m: f'{m.group(1)} карту Signature',
            r'\b(карт[ауе]?\s+)?(сигнатур[ауеыой]*|signature)\b': 'карту Signature',
            r'\b(я\s+хочу|хочу)\s+(сигнатур[ауеыой]*|signature)\b': lambda m: f'{m.group(1)} карту Signature',
            
            # Другие популярные карты
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(форсаж|forsazh)\b': lambda m: f'{m.group(1)} карту Форсаж',
            r'\b(карт[ауе]?\s+)?(форсаж|forsazh)\b': 'карту Форсаж',
            
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(премиум|premium)\b': lambda m: f'{m.group(1)} карту Премиум',
            r'\b(карт[ауе]?\s+)?(премиум|premium)\b': 'карту Премиум',
            
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(голд|gold)\b': lambda m: f'{m.group(1)} карту Gold',
            r'\b(карт[ауе]?\s+)?(голд|gold)\b': 'карту Gold',
            
            # Карта КСТАТИ
            r'\b(кстати)(?!\s+(банк|счет|вклад|кредит))\b': 'карта КСТАТИ',
            
            # Карта ЧЕРЕПАХА
            r'\b(черепах[ауи]?)(?!\s+(банк|счет|вклад|кредит))\b': 'карта ЧЕРЕПАХА',
            
            # Карта Отличник
            r'\b(отличник[ауи]?)(?!\s+(банк|счет|вклад|кредит))\b': 'карта Отличник',
            
            # Карта Портмоне 2.0
            r'\b(портмоне|portmone)(?!\s*2\.0)(?!\s+(банк|счет|вклад|кредит))\b': 'карта Портмоне 2.0',
            
            # Mir Pay
            r'\b(оформить|получить|заказать|хочу)\s+(карт[ауеоюий]?\s+)?(мир\s+(?:пей|пэй|пай|pay))\b': lambda m: f'{m.group(1)} Mir Pay',
            r'\b(карт[ауе]?\s+)?(мир\s+(?:пей|пэй|пай|pay))\b': 'Mir Pay',
            r'\b(я\s+хочу|хочу)\s+(мир\s+(?:пей|пэй|пай|pay))\b': lambda m: f'{m.group(1)} Mir Pay',
            r'\b(мир\s+(?:пей|пэй|пай|pay))\b': 'Mir Pay',
            
            # КАСКО
            r'\b(kasko|каска|каско)\b': 'КАСКО',
            
            # СуперСемь
            r'\b(суперсемь|super7|supersem|супер7)\b': 'СуперСемь',
            
            # Мир
            r'\b(mir|мир)[а-яёa-z]*\b': 'Мир',
            
            # Онлайн-банкинг
            r'\b(онлайн\s*банк[а-яё]*|online\s*bank[a-z]*)\b': 'онлайн-банк',
            r'\b(интернет\s*банк[а-яё]*|internet\s*bank[a-z]*)\b': 'интернет-банк',
            r'\b(веб\s*банк[а-яё]*|web\s*bank[a-z]*)\b': 'веб-банк',
            
            # Мобильное приложение
            r'\b(моб\s*прил|mobile\s*app)\b': 'мобильное приложение',
            r'\b(приложуха|прилож[ае]н[ие]{2,3})\b': 'приложение',
            
            # Пин-код
            r'\b(pin\s*cod[е]?|пин\s*кот|pin)\b': 'ПИН-код',
            r'(?<!ПИН-)\b(пин)(?!\s*код)\b': 'ПИН-код',
            
            # Кредит/кредитка
            r'\b(креди?тк[ауеоюий]?|credit\s*card)\b': 'кредитная карта',
            r'\b(кредит[а-яё]*(?<!ная)|kredit)\b': 'кредит',
            
            # Депозит/вклад
            r'\b(депозит|deposit)\b': 'вклад',
            r'\b(депо)\b': 'вклад',
            
            # Перевод
            r'\b(transfer|трансфер)\b': 'перевод',
            
            # Баланс
            r'\b(balance|балланс|баланс)\b': 'баланс',
            
            # Блокировка
            r'\b(блок|block)\b': 'блокировка',
            r'\b(заблочен[ао]?|blocked)\b': 'заблокирован',
            
            # Разблокировка
            r'\b(разблок|unblock)\b': 'разблокировка',
            
            # Пароль
            r'\b(pass|пасс|password)\b': 'пароль',
            
            # Логин
            r'\b(login|log\s*in)\b': 'логин',
            
            # Кэшбэк
            r'\b(кэш\s*бэк|cash\s*back|кешбек|кэшбек)\b': 'кэшбэк',
            
            # Овердрафт
            r'\b(овер\s*драфт|over\s*draft)\b': 'овердрафт',
            
            # Смс
            r'\b(sms|смс|смска)\b': 'СМС',
            
            # Комиссия
            r'\b(комисси[яи]|commission)\b': 'комиссия',
            
            # Терминал
            r'\b(terminal|термина?л)\b': 'терминал',
            r'\b(банкомат|atm)\b': 'банкомат',
            
            # Валюты
            r'\b(byn|бел\.?\s*руб|белорусски[ехй]\s+рубл[ейя])\b': 'BYN',  # Белорусский рубль
            r'\b(rub|руб|российски[ех]\s+рубл[ейя]|рос\.?\s*руб|rur)\b': 'RUB',  # Российский рубль
            r'\b(usd|юсд)\b': 'USD',
            r'\b(eur|евро)\b': 'EUR',
            
            # Операции
            r'\b(перечислени[ея]|transfer)\b': 'перевод',
            r'\b(пополнени[ея]|top\s*up)\b': 'пополнение',
            r'\b(снятие|withdrawal)\b': 'снятие',
            r'\b(платеж|payment)\b': 'платеж',
            
            # Документы
            r'\b(паспорт|passport)\b': 'паспорт',
            r'\b(договор|contract)\b': 'договор',
            r'\b(выписк[ауи]|statement)\b': 'выписка',
            
            # Счета
            r'\b(счет|счёт|account)\b': 'счет',
            r'\b(текущ[ийего]+\s+счет[а]?)\b': 'текущий счет',
            r'\b(сберегательны[йе]\s+счет[а]?)\b': 'сберегательный счет',
        }
        
        # Компилируем паттерны для быстрого поиска
        self.compiled_patterns = {
            re.compile(pattern, re.IGNORECASE | re.UNICODE): replacement
            for pattern, replacement in self.replacements.items()
        }
    
    def normalize(self, text):
        """
        Нормализует текст, заменяя англицизмы и неправильные написания
        
        Args:
            text: Исходный текст запроса
            
        Returns:
            str: Нормализованный текст
        """
        if not text:
            return text
        
        normalized_text = text
        
        # Применяем все замены
        for pattern, replacement in self.compiled_patterns.items():
            if callable(replacement):
                # Если replacement - это функция, используем её
                normalized_text = pattern.sub(replacement, normalized_text)
            else:
                # Иначе простая строковая замена
                normalized_text = pattern.sub(replacement, normalized_text)
        
        return normalized_text
    
    def normalize_with_log(self, text):
        """
        Нормализует текст с логированием изменений
        
        Args:
            text: Исходный текст запроса
            
        Returns:
            tuple: (нормализованный текст, список изменений)
        """
        if not text:
            return text, []
        
        normalized_text = text
        changes = []
        
        # Применяем все замены и фиксируем изменения
        for pattern, replacement in self.compiled_patterns.items():
            # Найдем все совпадения до замены
            original_matches = pattern.findall(normalized_text)
            
            if original_matches:
                # Сохраняем текст до замены
                before_text = normalized_text
                
                # Применяем замену
                if callable(replacement):
                    normalized_text = pattern.sub(replacement, normalized_text)
                else:
                    normalized_text = pattern.sub(replacement, normalized_text)
                
                # Если текст изменился, фиксируем это
                if before_text != normalized_text:
                    # Для callable замен показываем общее изменение
                    if callable(replacement):
                        # Определяем тип замены по паттерну
                        pattern_str = pattern.pattern
                        if 'море|мор' in pattern_str:
                            changes.append(f"'море/мор' → 'карту MORE'")
                        elif 'инфинит' in pattern_str or 'infinity' in pattern_str:
                            changes.append(f"'инфинити/infinity' → 'карту Infinite'")
                        elif 'платон' in pattern_str or 'plat' in pattern_str:
                            changes.append(f"'платон/plat/on' → 'карту PLAT/ON'")
                        elif 'сигнатур' in pattern_str or 'signature' in pattern_str:
                            changes.append(f"'сигнатур/signature' → 'карту Signature'")
                        elif 'форсаж' in pattern_str:
                            changes.append(f"'форсаж' → 'карту Форсаж'")
                        elif 'премиум' in pattern_str or 'premium' in pattern_str:
                            changes.append(f"'премиум/premium' → 'карту Премиум'")
                        elif 'голд' in pattern_str or 'gold' in pattern_str:
                            changes.append(f"'голд/gold' → 'карту Gold'")
                        elif 'кстати' in pattern_str:
                            changes.append(f"'кстати' → 'карту КСТАТИ'")
                        elif 'черепах' in pattern_str:
                            changes.append(f"'черепаха' → 'карту ЧЕРЕПАХА'")
                        elif 'отличник' in pattern_str:
                            changes.append(f"'отличник' → 'карту Отличник'")
                        elif 'портмоне' in pattern_str or 'portmone' in pattern_str:
                            changes.append(f"'портмоне' → 'карту Портмоне 2.0'")
                        else:
                            changes.append(f"обнаружены изменения")
                    else:
                        for match in original_matches:
                            match_str = match if isinstance(match, str) else ' '.join(match)
                            if match_str.lower() != str(replacement).lower():
                                changes.append(f"'{match_str}' → '{replacement}'")
        
        return normalized_text, changes


# Глобальный экземпляр для использования в других модулях
_normalizer_instance = None


def get_normalizer():
    """Получить глобальный экземпляр нормализатора"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = AnglicismNormalizer()
    return _normalizer_instance


def normalize_text(text):
    """
    Удобная функция для нормализации текста
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Нормализованный текст
    """
    return get_normalizer().normalize(text)


# Тестирование
if __name__ == '__main__':
    normalizer = AnglicismNormalizer()
    
    test_cases = [
        "я хочу море",
        "хочу оформить карту море",
        "не могу войти в онлайн банк",
        "забыл пин кот от карты",
        "как получить кэшбэк?",
        "заблокировали креди́тку",
        "хочу сделать трансфер денег",
        "не приходят смски",
        "я хочу карту мор",
        "где взять карту MORE?",
    ]
    
    print("Тестирование нормализатора англицизмов:")
    print("=" * 70)
    
    for test in test_cases:
        normalized, changes = normalizer.normalize_with_log(test)
        print(f"\nИсходный текст: {test}")
        print(f"Нормализован:   {normalized}")
        if changes:
            print(f"Изменения:      {', '.join(changes)}")
        else:
            print("Изменения:      нет")

