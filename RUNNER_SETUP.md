# Настройка GitHub Actions Runner

## Установка Runner

1. Перейдите в настройки вашего репозитория на GitHub
2. Выберите "Actions" -> "Runners"
3. Нажмите "New self-hosted runner"
4. Следуйте инструкциям для вашей операционной системы

## Настройка на Linux/macOS

```bash
# Создайте директорию для runner
mkdir actions-runner && cd actions-runner

# Скачайте последнюю версию runner
curl -o actions-runner-osx-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-x64-2.311.0.tar.gz

# Распакуйте архив
tar xzf ./actions-runner-osx-x64-2.311.0.tar.gz

# Настройте runner
./config.sh --url https://github.com/your-username/your-repo --token YOUR_TOKEN

# Запустите runner
./run.sh
```

## Настройка на Windows

1. Скачайте последнюю версию runner с GitHub
2. Распакуйте архив в удобную директорию
3. Запустите `config.cmd` и следуйте инструкциям
4. Запустите `run.cmd`

## Автозапуск Runner

### Linux/macOS (systemd)

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

### Windows (Service)

```bash
./svc.sh install
./svc.sh start
```

## Мониторинг

- Проверяйте статус runner в настройках GitHub
- Логи доступны в директории `_diag`
- Для остановки runner используйте Ctrl+C или команду `./svc.sh stop`

## Безопасность

- Храните токены в безопасном месте
- Регулярно обновляйте runner
- Используйте минимально необходимые разрешения для токенов 