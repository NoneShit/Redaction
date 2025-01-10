import logging
import random
import asyncio
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены
BOT_TOKEN = "7530160908:AAEZDoqK5NaYs1U_0If7M1XTldzyN8r9L5A"

# Список товаров
PRODUCTS = {
    "1": {"name": "Prosto Amf", "price": 50.0},
    "2": {"name": "Invisible Cocaine", "price": 50.0},
    "3": {"name": "Devil Mef", "price": 25.0},
    "4": {"name": "Demon Sativa", "price": 35.0},
}

# Список городов, районов и диапазонов координат
CITIES = {
    "Кишинев": {
        "districts": ["Центр", "Ботаника", "Рышкановка", "Буюканы"],
        "coordinates": {"lat_min": 47.0, "lat_max": 47.1, "lon_min": 28.8, "lon_max": 29.0},
    },
    "Бельцы": {
        "districts": ["Центр", "Дачия", "Энгельса"],
        "coordinates": {"lat_min": 47.7, "lat_max": 47.8, "lon_min": 27.8, "lon_max": 28.0},
    },
    "Кагул": {
        "districts": ["Центр", "Садовое", "Юг"],
        "coordinates": {"lat_min": 45.8, "lat_max": 45.9, "lon_min": 28.1, "lon_max": 28.3},
    },
}

# Bitcoin-адрес
BTC_ADDRESS = "bc1qpgrg2jl6q8qcsr8t2p842md30z4ukn37cxqxtz"

# Сохранение данных заказа в файл
def save_order(user_data: dict) -> None:
    """Сохраняет данные заказа в файл."""
    with open("orders.txt", "a", encoding="utf-8") as file:
        file.write("Новый заказ:\n")
        file.write(f"Товар: {user_data['product']}\n")
        file.write(f"Количество: {user_data['quantity']}\n")
        file.write(f"Город: {user_data['city']}\n")
        file.write(f"Район: {user_data['district']}\n")
        file.write(f"Username: {user_data['username']}\n")
        file.write(f"Полное имя: {user_data['full_name']}\n")
        file.write(f"Стоимость: {user_data['price_usd']} USD\n")
        file.write(f"Bitcoin-адрес: {BTC_ADDRESS}\n")
        file.write("----\n")


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню с товарами."""
    keyboard = [
        [InlineKeyboardButton(PRODUCTS[key]["name"], callback_data=f"product:{key}")]
        for key in PRODUCTS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите товар:", reply_markup=reply_markup)

# Обработчик выбора товара
async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет выбранный товар и переходит к выбору количества."""
    query = update.callback_query
    await query.answer()

    product_id = query.data.split(":")[1]
    product = PRODUCTS[product_id]
    context.user_data["product"] = product["name"]
    context.user_data["price_per_unit"] = product["price"]

    keyboard = [
        [InlineKeyboardButton(f"{i} Г", callback_data=f"quantity:{i}") for i in range(1, 6)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"Вы выбрали: {product['name']} (${product['price']:.2f}). Выберите количество:",
        reply_markup=reply_markup
    )

# Обработчик выбора количества
async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет выбранное количество и переходит к выбору города."""
    query = update.callback_query
    await query.answer()

    quantity = int(query.data.split(":")[1])
    context.user_data["quantity"] = quantity
    context.user_data["price_usd"] = context.user_data["price_per_unit"] * quantity

    keyboard = [
        [InlineKeyboardButton(city, callback_data=f"city:{city}")] for city in CITIES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"Вы выбрали количество: {quantity} Г. Теперь выберите ваш город:",
        reply_markup=reply_markup
    )

# Обработчик выбора города
async def select_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню районов выбранного города."""
    query = update.callback_query
    await query.answer()

    city = query.data.split(":")[1]
    context.user_data["city"] = city

    keyboard = [
        [InlineKeyboardButton(district, callback_data=f"district:{district}")]
        for district in CITIES[city]["districts"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"Вы выбрали: {city}. Теперь выберите район:",
        reply_markup=reply_markup
    )

# Обработчик выбора района
async def select_district(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали заказа с кнопкой 'Оплатить'."""
    query = update.callback_query
    await query.answer()

    district = query.data.split(":")[1]
    context.user_data["district"] = district

    keyboard = [[InlineKeyboardButton("Оплачено", callback_data="pay")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    username = update.effective_user.username or "unknown"
    context.user_data["username"] = f"@{username}"
    context.user_data["full_name"] = update.effective_user.full_name or "Не указано"

    await query.edit_message_text(
        text=(f"Вы выбрали:\n"
              f"Товар: {context.user_data['product']}\n"
              f"Количество: {context.user_data['quantity']} Г\n"
              f"Город: {context.user_data['city']}\n"
              f"Район: {district}\n"
              f"Стоимость: ${context.user_data['price_usd']:.2f}\n\n"
              f"Для оплаты переведите сумму на адрес:\n\n\n"
              f"4356960067147535\n"
              f"После оплаты нажмите кнопку 'Оплачено'."), 
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# Обработчик кнопки "Оплачено"
async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет заказ и отправляет сообщение ожидания."""
    query = update.callback_query
    await query.answer()

    # Удаляем кнопку и заменяем текст
    try:
        await query.edit_message_text(
            "Оплата обрабатывается. Пожалуйста, подождите..."
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}")

    # Сохраняем данные заказа
    save_order(context.user_data)

    # Ожидание 10 минут
    await asyncio.sleep(2400)

    # Генерация случайных координат
    city_data = CITIES[context.user_data["city"]]["coordinates"]
    lat = round(random.uniform(city_data["lat_min"], city_data["lat_max"]), 6)
    lon = round(random.uniform(city_data["lon_min"], city_data["lon_max"]), 6)

    await query.message.reply_text(
        f"Оплата подтверждена!\nКоординаты для города {context.user_data['city']}, "
        f"района {context.user_data['district']}:\n"
        f"Широта: {lat}\nДолгота: {lon}\n\n"
        f"Спасибо за использование нашего сервиса!"
    )


# Основной блок
def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(select_product, pattern=r"^product:.+"))
    application.add_handler(CallbackQueryHandler(select_quantity, pattern=r"^quantity:.+"))
    application.add_handler(CallbackQueryHandler(select_city, pattern=r"^city:.+"))
    application.add_handler(CallbackQueryHandler(select_district, pattern=r"^district:.+"))
    application.add_handler(CallbackQueryHandler(process_payment, pattern="^pay$"))

    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling()

if __name__ == "__main__":
    main()
