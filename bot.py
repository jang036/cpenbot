from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
import json
import logging

# Увімкнення логування
logging.basicConfig(level=logging.INFO)

# === Налаштування ===
BOT_TOKEN = '8159278233:AAFJ6nwC_GuSogY_Un2D-u4sKQD4pLv9VQE'  # Замініть на свій токен
ADMIN_ID = 6841298509    # Куди надсилати замовлення (Telegram user ID)

# === Ініціалізація ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# === Завантаження товарів ===
def load_products():
    with open("products.json", encoding='utf-8') as f:
        return json.load(f)

products = load_products()

# === Головне меню ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    for category in products:
        kb.add(InlineKeyboardButton(category, callback_data=f"cat_{category}"))
    await message.answer("👋 Вітаємо у магазині! Оберіть категорію:", reply_markup=kb)

# === Вибір категорії ===
@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def category_handler(callback: types.CallbackQuery):
    category = callback.data.split("cat_")[1]
    kb = InlineKeyboardMarkup()
    for item in products[category]:
        kb.add(InlineKeyboardButton(item['name'], callback_data=f"item_{category}_{item['id']}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    await callback.message.edit_text(f"📦 {category}", reply_markup=kb)

# === Повернення на головну ===
@dp.callback_query_handler(lambda c: c.data == "back_main")
async def back_to_main(callback: types.CallbackQuery):
    await start_handler(callback.message)

# === Вибір товару ===
@dp.callback_query_handler(lambda c: c.data.startswith("item_"))
async def item_handler(callback: types.CallbackQuery):
    _, category, item_id = callback.data.split("_", 2)
    item = next((x for x in products[category] if x['id'] == item_id), None)
    if not item:
        await callback.answer("Товар не знайдено")
        return

    photo = InputFile(item['image'])
    caption = f"<b>{item['name']}</b>\n\n{item['description']}\n💸 <b>Ціна:</b> {item['price']} грн"
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🛒 Замовити", callback_data=f"order_{category}_{item['id']}"),
        InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{category}")
    )
    await bot.send_photo(callback.message.chat.id, photo=photo, caption=caption, parse_mode='HTML', reply_markup=kb)

# === Початок замовлення ===
user_orders = {}

@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def order_start(callback: types.CallbackQuery):
    _, category, item_id = callback.data.split("_", 2)
    user_orders[callback.from_user.id] = {"category": category, "item_id": item_id, "step": 1, "data": {}}
    await callback.message.answer("✍️ Введіть ваше <b>Ім’я та Прізвище</b>:", parse_mode='HTML')

@dp.message_handler(lambda m: m.from_user.id in user_orders)
async def order_process(message: types.Message):
    order = user_orders[message.from_user.id]
    step = order['step']

    if step == 1:
        order['data']['name'] = message.text
        order['step'] = 2
        await message.answer("📞 Введіть <b>номер телефону</b>:", parse_mode='HTML')
    elif step == 2:
        order['data']['phone'] = message.text
        order['step'] = 3
        await message.answer("🏩 Введіть <b>місто</b> доставки:", parse_mode='HTML')
    elif step == 3:
        order['data']['city'] = message.text
        order['step'] = 4
        await message.answer("🏤 Введіть <b>відділення Нової Пошти</b>:", parse_mode='HTML')
    elif step == 4:
        order['data']['np'] = message.text
        order['step'] = 5
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💳 На картку", callback_data="pay_card"),
            InlineKeyboardButton("📦 Накладений платіж", callback_data="pay_cod")
        )
        await message.answer("💰 Оберіть спосіб оплати:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def order_confirm(callback: types.CallbackQuery):
    pay_method = "На картку" if callback.data == "pay_card" else "Накладений платіж"
    order = user_orders.pop(callback.from_user.id)
    item = next((x for x in products[order['category']] if x['id'] == order['item_id']), None)

    text = f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ</b> 🔥\n\n" \
           f"🛕️ Товар: {item['name']}\n💰 Ціна: {item['price']} грн\n💳 Оплата: {pay_method}\n\n" \
           f"👤 Ім’я: {order['data']['name']}\n📞 Телефон: {order['data']['phone']}\n" \
           f"🏩 Місто: {order['data']['city']}\n🏤 Відділення НП: {order['data']['np']}"

    await bot.send_message(callback.from_user.id, "✅ Ваше замовлення оформлено! Очікуйте звізку. 💚")
    await bot.send_message(ADMIN_ID, text, parse_mode='HTML')

# === Запуск ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

