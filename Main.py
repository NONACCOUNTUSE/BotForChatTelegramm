import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleImageBot:
    def __init__(self, token):
        self.token = token
        self.image_storage = {}
        self.setup_bot()
        
    def setup_bot(self):
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.handle_image)
        )
        
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/generate'), self.generate_collage)
        )
        
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/stats'), self.show_stats)
        )
        
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/help'), self.show_help)
        )

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            photo_file = await update.message.photo[-1].get_file()
            
            chat_folder = f"chat_images/{chat_id}"
            os.makedirs(chat_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{chat_folder}/{user_id}_{timestamp}.jpg"
            
            await photo_file.download_to_drive(filename)
            
            if chat_id not in self.image_storage:
                self.image_storage[chat_id] = []
            
            self.image_storage[chat_id].append({
                'user_id': user_id,
                'filename': filename,
                'timestamp': timestamp,
                'username': update.effective_user.username or "Unknown"
            })
            
            self.save_metadata()
            
            await update.message.reply_text(
                f"✅ Изображение сохранено! Всего: {len(self.image_storage[chat_id])}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка при сохранении")

    async def generate_collage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            
            if chat_id not in self.image_storage or len(self.image_storage[chat_id]) < 2:
                await update.message.reply_text("❌ Нужно как минимум 2 изображения для создания коллажа")
                return
            
            await update.message.reply_text("🔄 Создаю коллаж...")
            
            # Берем последние 4 изображения
            recent_images = self.image_storage[chat_id][-4:]
            images = []
            
            for img_data in recent_images:
                img = Image.open(img_data['filename'])
                img = img.resize((200, 200))
                images.append(img)
            
            # Создаем коллаж 2x2
            collage = Image.new('RGB', (400, 400))
            
            for i, img in enumerate(images):
                x = (i % 2) * 200
                y = (i // 2) * 200
                collage.paste(img, (x, y))
            
            # Сохраняем и отправляем
            bio = io.BytesIO()
            collage.save(bio, format='JPEG')
            bio.seek(0)
            
            await update.message.reply_photo(
                photo=bio,
                caption=f"🎨 Коллаж из {len(images)} последних изображений чата"
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания коллажа: {e}")
            await update.message.reply_text("❌ Ошибка при создании коллажа")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if chat_id in self.image_storage and self.image_storage[chat_id]:
            count = len(self.image_storage[chat_id])
            
            # Статистика по пользователям
            user_stats = {}
            for img in self.image_storage[chat_id]:
                user_id = img['user_id']
                if user_id not in user_stats:
                    user_stats[user_id] = 0
                user_stats[user_id] += 1
            
            stats_text = f"📊 Статистика чата:\n"
            stats_text += f"Всего изображений: {count}\n"
            stats_text += f"Участников: {len(user_stats)}\n\n"
            
            stats_text += "Топ участников:\n"
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            
            for i, (user_id, img_count) in enumerate(sorted_users, 1):
                stats_text += f"{i}. Участник {user_id}: {img_count} фото\n"
            
        else:
            stats_text = "📊 В этом чате еще нет сохраненных изображений."
        
        await update.message.reply_text(stats_text)

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🤖 **Команды бота:**

📸 **Просто отправьте фото** - бот сохранит его
🔄 **/generate** - создать коллаж из последних фото
📊 **/stats** - показать статистику
❓ **/help** - эта справка

Бот автоматически сохраняет все изображения из чата и может создавать коллажи!
        """
        await update.message.reply_text(help_text)

    def save_metadata(self):
        try:
            with open('image_metadata.json', 'w', encoding='utf-8') as f:
                serializable_data = {}
                for chat_id, images in self.image_storage.items():
                    serializable_data[str(chat_id)] = images
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")

    def load_metadata(self):
        try:
            if os.path.exists('image_metadata.json'):
                with open('image_metadata.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.image_storage = {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")

    def run(self):
        self.load_metadata()
        logger.info("Бот запущен...")
        self.application.run_polling()

# Использование
if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    os.makedirs("chat_images", exist_ok=True)
    
    bot = SimpleImageBot(BOT_TOKEN)
    bot.run()
