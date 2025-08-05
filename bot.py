import os
import pandas as pd
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
import re

# Вставьте сюда токен вашего бота
BOT_TOKEN = "8360015141:AAGOC_Y4SWIFMFnuiwhoeh7XVtViDv0A50k"

class TableProcessor:
    def __init__(self):
        pass
    
    def format_amount(self, amount):
        """Форматирует сумму в удобочитаемый вид"""
        if pd.isna(amount) or amount == '':
            return ''
        
        # Попробуем преобразовать в число
        try:
            if isinstance(amount, str):
                # Удаляем пробелы и заменяем запятые на точки
                amount_clean = amount.replace(' ', '').replace(',', '.')
                amount_num = float(amount_clean)
            else:
                amount_num = float(amount)
            
            # Форматируем с разделителями тысяч
            if amount_num == int(amount_num):
                return f"{int(amount_num):,}".replace(',', ' ')
            else:
                return f"{amount_num:,.2f}".replace(',', ' ')
        except:
            return str(amount)
    
    def process_table(self, file_path):
        """Обрабатывает таблицу и создает сообщения"""
        try:
            # Определяем формат файла и читаем
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)
            
            messages = []
            
            for index, row in df.iterrows():
                try:
                    # Получаем данные из нужных столбцов
                    # Используем iloc для доступа по номеру столбца (начиная с 0)
                    col_2 = str(row.iloc[1]) if len(row) > 1 and not pd.isna(row.iloc[1]) else ""
                    col_3 = str(row.iloc[2]) if len(row) > 2 and not pd.isna(row.iloc[2]) else ""
                    col_5 = str(row.iloc[4]) if len(row) > 4 and not pd.isna(row.iloc[4]) else ""
                    col_6 = str(row.iloc[5]) if len(row) > 5 and not pd.isna(row.iloc[5]) else ""
                    col_8 = self.format_amount(row.iloc[7]) if len(row) > 7 else ""
                    col_15 = str(row.iloc[14]) if len(row) > 14 and not pd.isna(row.iloc[14]) else ""
                    col_25 = str(row.iloc[24]) if len(row) > 24 and not pd.isna(row.iloc[24]) else ""
                    
                    # Проверяем, есть ли данные в столбце 25
                    if col_25 and col_25.lower() not in ['nan', '', 'none']:
                        # Формат с данными в столбце 25
                        message = f"""Заявка «{col_2}»: сумма {col_8}; получение у «{col_5}» («{col_25}»), ставка «{col_15}»; платить с «{col_3}» на «{col_6}» (см. счёт):"""
                    else:
                        # Формат без данных в столбце 25
                        message = f"""Заявка «{col_2}»: сумма {col_8}; получение у «{col_5}», ставка «{col_15}»; платить с «{col_3}» на «{col_6}» (см. счёт):"""
                    
                    messages.append(message)
                    
                except Exception as e:
                    messages.append(f"Ошибка в строке {index + 1}: {str(e)}")
            
            return messages
            
        except Exception as e:
            return [f"Ошибка при обработке файла: {str(e)}"]

# Создаем экземпляр процессора
processor = TableProcessor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Привет! Я бот для обработки таблиц.

📋 Что я умею:
• Обрабатывать Excel (.xlsx, .xls) и CSV файлы
• Создавать сообщения по заданному шаблону
• Форматировать суммы для удобства чтения

📤 Как использовать:
1. Отправьте мне файл с таблицей
2. Получите готовые сообщения

💡 Формат сообщений:
• Если столбец 25 пустой: стандартный формат
• Если столбец 25 заполнен: расширенный формат с дополнительной информацией

Отправьте файл, чтобы начать! 📊
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
ℹ️ Справка по использованию бота:

📋 Поддерживаемые форматы файлов:
• Excel: .xlsx, .xls
• CSV: .csv

📊 Структура таблицы:
Бот использует следующие столбцы (нумерация с 1):
• Столбец 2: номер заявки
• Столбец 3: откуда платить
• Столбец 5: у кого получать
• Столбец 6: куда платить
• Столбец 8: сумма (автоматически форматируется)
• Столбец 15: ставка
• Столбец 25: дополнительная информация (опционально)

⚙️ Шаблоны сообщений:
1. Без столбца 25:
   Заявка «номер»: сумма сумма; получение у «получатель», ставка «ставка»; платить с «откуда» на «куда» (см. счёт):

2. Со столбцом 25:
   Заявка «номер»: сумма сумма; получение у «получатель» («доп_инфо»), ставка «ставка»; платить с «откуда» на «куда» (см. счёт):

🔧 Если у вас возникли проблемы, проверьте:
• Правильность структуры таблицы
• Наличие данных в нужных столбцах
• Формат файла
    """
    await update.message.reply_text(help_text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов"""
    document = update.message.document
    
    # Проверяем тип файла
    if not (document.file_name.endswith(('.xlsx', '.xls', '.csv'))):
        await update.message.reply_text("❌ Поддерживаются только файлы Excel (.xlsx, .xls) и CSV (.csv)")
        return
    
    try:
        # Отправляем сообщение о начале обработки
        processing_msg = await update.message.reply_text("⏳ Обрабатываю файл...")
        
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document.file_name)[1]) as tmp_file:
            await file.download_to_drive(tmp_file.name)
            
            # Обрабатываем таблицу
            messages = processor.process_table(tmp_file.name)
            
            # Удаляем временный файл
            os.unlink(tmp_file.name)
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Отправляем результаты
        if not messages:
            await update.message.reply_text("❌ Не удалось обработать файл или файл пустой")
            return
        
        # Отправляем информацию о количестве записей
        await update.message.reply_text(f"✅ Обработано записей: {len(messages)}\n\n📋 Готовые сообщения:")
        
        # Отправляем каждое сообщение отдельно
        for i, message in enumerate(messages, 1):
            # Telegram имеет ограничение на длину сообщения (4096 символов)
            if len(message) > 4000:
                # Разбиваем длинное сообщение на части
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for j, part in enumerate(parts):
                    await update.message.reply_text(f"📄 Запись {i} (часть {j+1}):\n{part}")
            else:
                await update.message.reply_text(f"📄 Запись {i}:\n{message}")
            
            # Небольшая задержка, чтобы не спамить
            await asyncio.sleep(0.1)
        
        # Итоговое сообщение
        await update.message.reply_text(f"🎉 Готово! Обработано {len(messages)} записей.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    await update.message.reply_text(
        "📎 Пожалуйста, отправьте файл с таблицей (Excel или CSV).\n\n"
        "Используйте /help для получения подробной справки."
    )

def main():
    """Главная функция"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()