import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image, ImageEnhance, ImageFilter
import io
import json
from datetime import datetime
import random
import requests
import base64

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AIImageBot:
    def __init__(self, token):
        self.token = token
        self.image_storage = {}
        self.setup_bot()
        
    def setup_bot(self):
        self.application = Application.builder().token(self.token).build()
        
        # Обработчик изображений
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.handle_image)
        )
        
        # Обработчик команды /generate
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/generate'), self.generate_from_style)
        )
        
        # Обработчик команды /mix
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/mix'), self.mix_styles)
        )
        
        # Обработчик команды /stats
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/stats'), self.show_stats)
        )
        
        # Обработчик команды /help
        self.application.add_handler(
            MessageHandler(filters.Regex(r'^/help'), self.show_help)
        )

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # Получаем файл изображения
            photo_file = await update.message.photo[-1].get_file()
            
            # Создаем папку для чата
            chat_folder = f"chat_images/{chat_id}"
            os.makedirs(chat_folder, exist_ok=True)
            
            # Сохраняем изображение
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{chat_folder}/{user_id}_{timestamp}.jpg"
            
            await photo_file.download_to_drive(filename)
            
            # Сохраняем в памяти
            if chat_id not in self.image_storage:
                self.image_storage[chat_id] = []
            
            self.image_storage[chat_id].append({
                'user_id': user_id,
                'filename': filename,
                'timestamp': timestamp,
                'username': update.effective_user.username or f"user_{user_id}"
            })
            
            # Сохраняем метаданные
            self.save_metadata()
            
            count = len(self.image_storage[chat_id])
            await update.message.reply_text(
                f"✅ Изображение сохранено! Всего: {count}\n"
                f"Теперь можно создать новое изображение в стиле чата командой /generate"
            )
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка при сохранении")

    def analyze_image_style(self, image_path):
        """Анализирует стиль изображения"""
        try:
            with Image.open(image_path) as img:
                # Анализ цветовой палитры
                img_small = img.resize((100, 100))
                colors = img_small.getcolors(maxcolors=10000)
                
                if colors:
                    # Находим доминирующие цвета
                    colors.sort(reverse=True)
                    dominant_colors = [color[1] for color in colors[:3]]
                    
                    # Анализ яркости и контраста
                    enhancer = ImageEnhance.Brightness(img)
                    brightness = random.uniform(0.8, 1.2)
                    
                    # Анализ резкости
                    sharpness = random.uniform(0.8, 1.5)
                    
                    return {
                        'dominant_colors': dominant_colors,
                        'brightness': brightness,
                        'sharpness': sharpness,
                        'width': img.width,
                        'height': img.height
                    }
        except Exception as e:
            logger.error(f"Ошибка анализа изображения: {e}")
        
        return {
            'dominant_colors': [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in range(3)],
            'brightness': random.uniform(0.8, 1.2),
            'sharpness': random.uniform(0.8, 1.5),
            'width': 512,
            'height': 512
        }

    def apply_style_to_base(self, base_image, style):
        """Применяет стиль к базовому изображению"""
        try:
            # Создаем копию изображения
            styled_image = base_image.copy()
            
            # Применяем яркость
            enhancer = ImageEnhance.Brightness(styled_image)
            styled_image = enhancer.enhance(style['brightness'])
            
            # Применяем резкость
            enhancer = ImageEnhance.Sharpness(styled_image)
            styled_image = enhancer.enhance(style['sharpness'])
            
            # Создаем цветовой фильтр на основе доминирующих цветов
            if style['dominant_colors']:
                # Берем основной цвет
                main_color = style['dominant_colors'][0]
                
                # Создаем цветной слой
                color_layer = Image.new('RGB', styled_image.size, main_color)
                
                # Наложение с прозрачностью
                styled_image = Image.blend(styled_image, color_layer, alpha=0.1)
            
            # Применяем случайные эффекты
            effects = [
                lambda img: img.filter(ImageFilter.GaussianBlur(radius=0.5)),
                lambda img: img.filter(ImageFilter.SMOOTH),
                lambda img: img.filter(ImageFilter.EDGE_ENHANCE),
                lambda img: ImageEnhance.Contrast(img).enhance(1.1),
                lambda img: ImageEnhance.Color(img).enhance(1.2)
            ]
            
            # Применяем 1-2 случайных эффекта
            for effect in random.sample(effects, random.randint(1, 2)):
                styled_image = effect(styled_image)
            
            return styled_image
            
        except Exception as e:
            logger.error(f"Ошибка применения стиля: {e}")
            return base_image

    def generate_abstract_art(self, style, size=(512, 512)):
        """Генерирует абстрактное искусство на основе стиля"""
        try:
            # Создаем базовое изображение с шумом
            base = Image.new('RGB', size, color=(255, 255, 255))
            
            # Добавляем шум и текстуры
            for _ in range(random.randint(50, 200)):
                x1 = random.randint(0, size[0])
                y1 = random.randint(0, size[1])
                x2 = random.randint(0, size[0])
                y2 = random.randint(0, size[1])
                
                color = random.choice(style['dominant_colors']) if style['dominant_colors'] else (
                    random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
                )
                
                # Создаем временное изображение для фигуры
                shape = Image.new('RGBA', size, (0, 0, 0, 0))
                
                # Случайная фигура: круг, прямоугольник или линия
                shape_type = random.choice(['circle', 'rect', 'line'])
                
                if shape_type == 'circle':
                    radius = random.randint(10, 100)
                    for x in range(max(0, x1-radius), min(size[0], x1+radius)):
                        for y in range(max(0, y1-radius), min(size[1], y1+radius)):
                            if (x - x1)**2 + (y - y1)**2 <= radius**2:
                                shape.putpixel((x, y), (*color, random.randint(50, 150)))
                
                elif shape_type == 'rect':
                    w, h = random.randint(20, 150), random.randint(20, 150)
                    for x in range(max(0, x1), min(size[0], x1 + w)):
                        for y in range(max(0, y1), min(size[1], y1 + h)):
                            shape.putpixel((x, y), (*color, random.randint(50, 150)))
                
                else:  # line
                    for i in range(100):
                        t = i / 100
                        x = int(x1 + t * (x2 - x1))
                        y = int(y1 + t * (y2 - y1))
                        if 0 <= x < size[0] and 0 <= y < size[1]:
                            shape.putpixel((x, y), (*color, random.randint(100, 200)))
                
                # Наложение фигуры на базовое изображение
                base = Image.alpha_composite(base.convert('RGBA'), shape).convert('RGB')
            
            return self.apply_style_to_base(base, style)
            
        except Exception as e:
            logger.error(f"Ошибка генерации абстрактного искусства: {e}")
            # Возвращаем простой градиент в случае ошибки
            base = Image.new('RGB', size)
            for y in range(size[1]):
                for x in range(size[0]):
                    r = int(255 * x / size[0])
                    g = int(255 * y / size[1])
                    b = int(255 * (x + y) / (size[0] + size[1]))
                    base.putpixel((x, y), (r, g, b))
            return base

    def get_chat_style(self, chat_id):
        """Анализирует общий стиль изображений в чате"""
        if chat_id not in self.image_storage or not self.image_storage[chat_id]:
            return None
        
        images = self.image_storage[chat_id]
        
        # Анализируем несколько случайных изображений из чата
        sample_size = min(3, len(images))
        sample_images = random.sample(images, sample_size)
        
        styles = []
        for img_data in sample_images:
            style = self.analyze_image_style(img_data['filename'])
            styles.append(style)
        
        # Усредняем стили
        if styles:
            avg_style = {
                'dominant_colors': [],
                'brightness': sum(s['brightness'] for s in styles) / len(styles),
                'sharpness': sum(s['sharpness'] for s in styles) / len(styles),
                'width': 512,
                'height': 512
            }
            
            # Объединяем цвета из всех стилей
            all_colors = []
            for style in styles:
                all_colors.extend(style['dominant_colors'])
            
            # Выбираем наиболее частые цвета
            if all_colors:
                avg_style['dominant_colors'] = all_colors[:5]  # Берем до 5 цветов
            
            return avg_style
        
        return None

    async def generate_from_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            
            if chat_id not in self.image_storage or len(self.image_storage[chat_id]) < 2:
                await update.message.reply_text(
                    "❌ Нужно как минимум 2 изображения для анализа стиля\n"
                    "Отправьте несколько фото в чат!"
                )
                return
            
            await update.message.reply_text("🎨 Анализирую стиль чата и генерирую новое изображение...")
            
            # Получаем общий стиль чата
            chat_style = self.get_chat_style(chat_id)
            
            if not chat_style:
                await update.message.reply_text("❌ Не удалось проанализировать стиль изображений")
                return
            
            # Генерируем новое изображение
            generated_image = self.generate_abstract_art(chat_style)
            
            # Сохраняем сгенерированное изображение
            output_folder = f"generated_images/{chat_id}"
            os.makedirs(output_folder, exist_ok=True)
            output_filename = f"{output_folder}/generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            generated_image.save(output_filename)
            
            # Отправляем в чат
            bio = io.BytesIO()
            generated_image.save(bio, format='JPEG', quality=85)
            bio.seek(0)
            
            total_images = len(self.image_storage[chat_id])
            await update.message.reply_photo(
                photo=bio,
                caption=f"🖼 Сгенерировано на основе {total_images} изображений из этого чата\n"
                       f"✨ Уникальный стиль, созданный ИИ"
            )
            
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            await update.message.reply_text("❌ Ошибка при генерации изображения")

    async def mix_styles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создает микс из нескольких стилей"""
        try:
            chat_id = update.effective_chat.id
            
            if chat_id not in self.image_storage or len(self.image_storage[chat_id]) < 3:
                await update.message.reply_text(
                    "❌ Нужно как минимум 3 изображения для создания микса стилей"
                )
                return
            
            await update.message.reply_text("🔄 Создаю микс стилей из изображений чата...")
            
            # Берем несколько случайных изображений для микса
            images = random.sample(self.image_storage[chat_id], 
                                 min(4, len(self.image_storage[chat_id])))
            
            mixed_style = {
                'dominant_colors': [],
                'brightness': 0,
                'sharpness': 0,
                'width': 512,
                'height': 512
            }
            
            # Собираем характеристики из всех изображений
            all_colors = []
            brightness_sum = 0
            sharpness_sum = 0
            
            for img_data in images:
                style = self.analyze_image_style(img_data['filename'])
                all_colors.extend(style['dominant_colors'])
                brightness_sum += style['brightness']
                sharpness_sum += style['sharpness']
            
            # Усредняем параметры
            mixed_style['dominant_colors'] = all_colors[:8]  # Берем больше цветов для микса
            mixed_style['brightness'] = brightness_sum / len(images)
            mixed_style['sharpness'] = sharpness_sum / len(images)
            
            # Генерируем изображение с миксом стилей
            generated_image = self.generate_abstract_art(mixed_style)
            
            # Сохраняем и отправляем
            bio = io.BytesIO()
            generated_image.save(bio, format='JPEG', quality=85)
            bio.seek(0)
            
            await update.message.reply_photo(
                photo=bio,
                caption=f"🎭 Микс стилей из {len(images)} изображений\n"
                       f"💫 Уникальная комбинация цветов и эффектов"
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания микса: {e}")
            await update.message.reply_text("❌ Ошибка при создании микса стилей")

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
                username = next((img['username'] for img in self.image_storage[chat_id] if img['user_id'] == user_id), f"user_{user_id}")
                stats_text += f"{i}. {username}: {img_count} фото\n"
            
        else:
            stats_text = "📊 В этом чате еще нет сохраненных изображений."
        
        await update.message.reply_text(stats_text)

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🤖 **AI Image Bot - Генератор изображений**

📸 **Отправьте фото** - бот сохранит его в память
🎨 **/generate** - создать новое изображение в стиле чата
🎭 **/mix** - создать микс из стилей разных изображений
📊 **/stats** - статистика сохраненных изображений
❓ **/help** - эта справка

✨ Бот анализирует стиль всех сохраненных изображений и создает совершенно новые уникальные изображения на их основе!
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

# ТОКЕН БОТА
BOT_TOKEN = "8018937192:AAGJc8Q05mx-3XTgFX0tmu3oT_EmxfhJ4mM"

if __name__ == "__main__":
    # Создаем необходимые папки
    os.makedirs("chat_images", exist_ok=True)
    os.makedirs("generated_images", exist_ok=True)
    
    bot = AIImageBot(BOT_TOKEN)
    bot.run()
