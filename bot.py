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
        self.images = []  # Список для хранения загруженных изображений
        self.waiting_for_table = False  # Флаг ожидания таблицы
    
    def reset_session(self):
        """Сброс сессии"""
        self.images = []
        self.waiting_for_table = False
    
    def add_image(self, photo_file_id):
        """Добавляет изображение в список"""
        self.images.append(photo_file_id)
    
    def format_amount(self, amount):
        """Форматирует сумму в удобочитаемый вид с обязательными двумя знаками после запятой"""
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
            
            # Форматируем с разделителями тысяч и обязательно 2 знака после запятой
            formatted = f"{amount_num:,.2f}"
            # Заменяем точку на запятую для десятичной части и запятые на точки для разделителей тысяч
            parts = formatted.split('.')
            integer_part = parts[0].replace(',', '.')
            decimal_part = parts[1]
            return f"{integer_part},{decimal_part}"
        except:
            return str(amount)
    
    def format_rate(self, rate):
        """Форматирует ставку как процент (0,205 => 20,50%)"""
        if pd.isna(rate) or rate == '':
            return ''
        
        try:
            if isinstance(rate, str):
                # Удаляем пробелы и заменяем запятые на точки
                rate_clean = rate.replace(' ', '').replace(',', '.')
                # Если уже содержит знак процента, оставляем как есть
                if '%' in rate_clean:
                    return rate_clean
                rate_num = float(rate_clean)
            else:
                rate_num = float(rate)
            
            # Конвертируем в проценты (умножаем на 100)
            percentage = rate_num * 100
            
            # Форматируем с двумя знаками после запятой
            return f"{percentage:.2f}%".replace('.', ',')
        except:
            return str(rate)
    
    def process_table(self, file_path):
        """Обрабатывает таблицу и создает сообщения"""
        try:
            # Определяем формат файла и читаем
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)
            
            # Пропускаем первые 2 строки
            df = df.iloc[2:].reset_index(drop=True)
            
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
                    col_15 = self.format_rate(row.iloc[14]) if len(row) > 14 else ""
                    col_25 = str(row.iloc[24]) if len(row) > 24 and not pd.isna(row.iloc[24]) else ""
                    
                    # Проверяем, есть ли данные в столбце 25
                    if col_25 and col_25.lower() not in ['nan', '', 'none']:
                        # Формат с данными в столбце 25 (без кавычек)
                        message = f"""Заявка {col_2}: сумма {col_8}; получение у {col_5} ({col_25}), ставка {col_15}; платить с {col_3} на {col_6} (см. счёт):"""
                    else:
                        # Формат без данных в столбце 25 (без кавычек)
                        message = f"""Заявка {col_2}: сумма {col_8}; получение у {col_5}, ставка {col_15}; платить с {col_3} на {col_6} (см. счёт):"""
                    
                    # Добавляем соответствующее изображение, если есть
                    image_file_id = None
                    if index < len(self.images):
                        image_file_id = self.images[index]
                    
                    messages.append({
                        'text': message,
                        'image': image_file_id
                    })
                    
                except Exception as e:
                    messages.append({
                        'text': f"Ошибка в строке {index + 1}: {str(e)}",
                        'image': None
                    })
            
            return messages
            
        except Exception as e:
            return [{'text': f"Ошибка при обработке файла: {str(e)}", 'image': None}]

# Создаем экземпляр процессора
processor = TableProcessor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    processor.reset_session()
    welcome_text = """
🤖 Привет! Я бот для обработки таблиц с изображениями.

📋 Что я умею:
• Обрабатывать Excel (.xlsx, .xls) и CSV файлы
• Сопоставлять изображения с записями таблицы
• Создавать сообщения по заданному шаблону
• Форматировать суммы и проценты

📤 Как использовать:
1. Отправьте изображения одно за другим (в нужной последовательности)
2. Отправьте файл с таблицей
3. Получите готовые сообщения с соответствующими изображениями

💡 Особенности:
• Первые 2 строки таблицы пропускаются
• Суммы форматируются с двумя знаками после запятой
• Ставки отображаются как проценты
• Каждая запись сопоставляется с изображением по порядку

Начните с отправки изображений! 📷
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
ℹ️ Справка по использованию бота:

📋 Поддерживаемые форматы файлов:
• Excel: .xlsx, .xls
• CSV: .csv

📷 Работа с изображениями:
• Отправляйте изображения по одному в нужной последовательности
• Каждое изображение будет сопоставлено с соответствующей записью таблицы
• Если изображений меньше записей, оставшиеся записи будут без изображений

📊 Структура таблицы:
Бот использует следующие столбцы (нумерация с 1):
• Столбец 2: номер заявки
• Столбец 3: откуда платить
• Столбец 5: у кого получать
• Столбец 6: куда платить
• Столбец 8: сумма (форматируется с .00)
• Столбец 15: ставка (отображается как %)
• Столбец 25: дополнительная информация (опционально)

⚙️ Особенности обработки:
• Первые 2 строки таблицы пропускаются
• Кавычки в названиях фирм убираются
• Суммы всегда с двумя знаками после запятой (например: 2.500.200,00)
• Ставки в процентах (например: 20,5%)

🔄 Сброс сессии:
Используйте /start для начала новой сессии
    """
    await update.message.reply_text(help_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изображений"""
    # Получаем самое большое изображение
    photo = update.message.photo[-1]
    processor.add_image(photo.file_id)
    
    await update.message.reply_text(
        f"📷 Изображение {len(processor.images)} получено!\n\n"
        f"Отправьте еще изображения или файл с таблицей для завершения."
    )

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
        images_info = f"📷 Изображений загружено: {len(processor.images)}\n" if processor.images else ""
        await update.message.reply_text(
            f"✅ Обработано записей: {len(messages)}\n"
            f"{images_info}"
            f"📋 Готовые сообщения:"
        )
        
        # Отправляем каждое сообщение отдельно
        for i, message_data in enumerate(messages, 1):
            message_text = message_data['text']
            
            # Проверяем длину сообщения
            if len(message_text) > 4000:
                # Разбиваем длинное сообщение на части
                parts = [message_text[j:j+4000] for j in range(0, len(message_text), 4000)]
                for k, part in enumerate(parts):
                    await update.message.reply_text(part)
                    
                # Отправляем изображение отдельно после текста, если есть
                if message_data['image']:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=message_data['image']
                    )
            else:
                # Сначала отправляем текст
                await update.message.reply_text(message_text)
                
                # Затем отправляем изображение, если есть
                if message_data['image']:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=message_data['image']
                    )
            
            # Небольшая задержка, чтобы не спамить
            await asyncio.sleep(0.1)
        
        # Итоговое сообщение
        await update.message.reply_text(f"🎉 Готово! Обработано {len(messages)} записей.")
        
        # Сбрасываем сессию после обработки
        processor.reset_session()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if processor.images:
        await update.message.reply_text(
            f"📷 У вас уже загружено {len(processor.images)} изображений.\n\n"
            f"📎 Теперь отправьте файл с таблицей (Excel или CSV) для завершения обработки.\n\n"
            f"Или используйте /start для начала новой сессии."
        )
    else:
        await update.message.reply_text(
            "📷 Начните с отправки изображений, а затем файла с таблицей.\n\n"
            "Используйте /help для получения подробной справки."
        )

def main():
    """Главная функция"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()