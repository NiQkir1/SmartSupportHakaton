"""
Клиент для работы с SciBox LLM API
"""

from openai import OpenAI
from config import SCIBOX_API_KEY, SCIBOX_BASE_URL, CHAT_MODEL, EMBEDDING_MODEL
import time


class LLMClient:
    """Клиент для взаимодействия с LLM моделями"""
    
    def __init__(self, api_key=None):
        # Используем переданный ключ или из конфига
        key = api_key or SCIBOX_API_KEY
        if not key:
            raise ValueError("API ключ не установлен. Передайте api_key или установите в config.")
        
        self.client = OpenAI(
            api_key=key,
            base_url=SCIBOX_BASE_URL
        )
    
    def validate_key(self):
        """
        Проверка валидности API ключа
        Делает тестовый запрос на embedding
        
        Returns:
            tuple: (bool, str) - (успех, сообщение об ошибке если есть)
        """
        try:
            # Пробуем получить embedding для короткой строки
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input="test"
            )
            # Если дошли сюда - ключ рабочий
            return (True, None)
        except Exception as e:
            error_msg = str(e)
            # Проверяем типичные ошибки API ключа
            if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
                return (False, "Неверный API ключ")
            elif "403" in error_msg or "Forbidden" in error_msg:
                return (False, "API ключ не имеет необходимых прав доступа")
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return (False, "Не удалось подключиться к API. Проверьте интернет-соединение")
            else:
                return (False, f"Ошибка проверки ключа: {error_msg}")
    
    def generate_response(self, messages, temperature=0.3, max_tokens=500, max_retries=2, progress_callback=None):
        """
        Генерирует ответ от чат-модели с retry при перегрузке
        
        Args:
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0-1)
            max_tokens: Максимальное количество токенов
            max_retries: Количество повторных попыток при 429
            progress_callback: Функция для отслеживания прогресса (опционально)
            
        Returns:
            str или dict: Сгенерированный ответ или информация об ошибке
        """
        # Прогрессивное увеличение времени ожидания: 10, 20, 30 секунд
        wait_times = [10, 20, 30]
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e)
                # Проверяем на 429 (Rate Limit)
                if "429" in error_str and attempt < max_retries:
                    # Используем прогрессивное время ожидания
                    wait_time = wait_times[attempt] if attempt < len(wait_times) else 30
                    
                    print(f"[RETRY] API перегружен, ожидание {wait_time}s... (попытка {attempt + 1}/{max_retries})")
                    
                    # Если передан callback, уведомляем о состоянии
                    if progress_callback:
                        progress_callback({
                            'status': 'rate_limited',
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'wait_time': wait_time
                        })
                    
                    time.sleep(wait_time)
                    continue
                
                print(f"[ERROR] Ошибка при генерации ответа: {e}")
                
                # Возвращаем информацию об ошибке для обработки на уровне API
                if "429" in error_str:
                    return {
                        'error': 'rate_limit',
                        'message': 'API перегружен',
                        'attempts': attempt + 1
                    }
                
                return None
        
        print(f"[ERROR] Превышено количество попыток ({max_retries})")
        
        # Возвращаем информацию о превышении лимита попыток
        return {
            'error': 'max_retries_exceeded',
            'message': f'API перегружен. Превышено количество попыток ({max_retries})',
            'attempts': max_retries + 1
        }
    
    def get_embedding(self, text):
        """
        Получает векторное представление текста
        
        Args:
            text: Текст для векторизации
            
        Returns:
            list: Вектор эмбеддинга
        """
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[ERROR] Ошибка при получении эмбеддинга: {e}")
            return None
    
    def get_embeddings_batch(self, texts):
        """
        Получает векторные представления для списка текстов
        
        Args:
            texts: Список текстов
            
        Returns:
            list: Список векторов эмбеддингов
        """
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"[ERROR] Ошибка при получении эмбеддингов: {e}")
            return None

