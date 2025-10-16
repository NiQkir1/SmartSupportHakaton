# Инструкция по развертыванию T1 SmartSupport v2.4.0

## Системные требования

### Минимальные требования:
- **ОС:** Windows 10/11, Linux (Ubuntu 20.04+), macOS 11+
- **RAM:** 4 GB
- **Диск:** 2 GB свободного места
- **Docker:** 20.10+ и Docker Compose 2.0+

### Рекомендуемые требования:
- **ОС:** Linux (Ubuntu 22.04)
- **RAM:** 8 GB
- **Диск:** 5 GB SSD
- **CPU:** 4 cores

## Установка Docker

### Windows
1. Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop
2. Установите и перезагрузите систему
3. Запустите Docker Desktop

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### macOS
1. Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop
2. Установите через .dmg файл
3. Запустите Docker Desktop

## Развертывание системы

### Шаг 1: Получение кода

```bash
git clone https://github.com/OrDinaD/SmartSupport.git
cd SmartSupport/support_system
```

### Шаг 2: Настройка окружения

Создайте файл `.env` в директории `support_system`:

```bash
# Linux/Mac
echo "SCIBOX_API_KEY=your_api_key_here" > .env

# Windows (PowerShell)
echo "SCIBOX_API_KEY=your_api_key_here" | Out-File -Encoding utf8 .env
```

### Шаг 3: Сборка и запуск

```bash
# Сборка образа
docker compose build

# Запуск в фоновом режиме
docker compose up -d

# Просмотр логов
docker compose logs -f
```

### Шаг 4: Проверка работы

Откройте в браузере: `http://localhost:5000`

## Управление контейнером

### Остановка системы
```bash
docker compose stop
```

### Перезапуск системы
```bash
docker compose restart
```

### Полное удаление
```bash
docker compose down
docker rmi t1_smartsupport
```

### Просмотр статуса
```bash
docker compose ps
docker compose logs
```

## Обновление базы знаний

1. Остановите контейнер:
```bash
docker compose stop
```

2. Отредактируйте файл:
```
data/smart_support_vtb_belarus_faq_final.xlsx
```

3. Удалите кэш embeddings:
```bash
rm data/embeddings_cache.npy
```

4. Запустите снова:
```bash
docker compose up -d
```

## Развертывание на сервере (Production)

### Nginx как reverse proxy

Установите Nginx:
```bash
sudo apt install nginx
```

Создайте конфигурацию `/etc/nginx/sites-available/smartsupport`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

Активируйте конфигурацию:
```bash
sudo ln -s /etc/nginx/sites-available/smartsupport /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL сертификат (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Автозапуск при перезагрузке

Docker Compose автоматически настраивает перезапуск через параметр `restart: unless-stopped`

## Мониторинг

### Проверка здоровья контейнера
```bash
docker inspect t1_smartsupport | grep -A 10 State
```

### Использование ресурсов
```bash
docker stats t1_smartsupport
```

### Логи в реальном времени
```bash
docker compose logs -f --tail=100
```

## Решение проблем

### Контейнер не запускается
```bash
# Проверьте логи
docker compose logs

# Проверьте .env файл
cat .env

# Пересоберите образ
docker compose build --no-cache
docker compose up -d
```

### Ошибка подключения к API
- Проверьте API ключ в `.env`
- Убедитесь, что есть интернет-соединение
- Проверьте лимиты API на dashboard.scibox.ru

### База знаний не загружается
```bash
# Проверьте наличие файла
ls -lh data/smart_support_vtb_belarus_faq_final.xlsx

# Удалите кэш
rm data/embeddings_cache.npy

# Перезапустите
docker compose restart
```

## Контакты технической поддержки

**Email:** support@t1-integration.ru  
**Telegram:** @t1_integration_bot  
**Документация:** https://docs.t1-integration.ru

---

© 2025 T1 Integration

