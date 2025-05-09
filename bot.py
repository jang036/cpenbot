from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
import json
import logging
import os

# Увімкнення логування
logging.basicConfig(level=logging.INFO)

# === Налаштування ===
BOT_TOKEN = '8159278233:AAFJ6nwC_GuSogY_Un2D-u4sKQD4pLv9VQE'
ADMIN_ID = 6841298509

# === Ініціалізація ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# === Завантаження товарів ===


def load_products():
    with open("products.json", encoding='utf-8') as f:
        return json.load(f)


products = load_products()
user_carts = {}
user_orders = {}

# === Функція для надсилання повідомлення адміну ===


async def send_order_to_admin(user_id, order_data):
    user = await bot.get_chat(user_id)
    username = user.username if user.username else "Нік відсутній"
    order_text = f"Нове замовлення від користувача @{username}:\n"
    order_text += f"Імʼя та Прізвище: {order_data['name']}\n"
    order_text += f"Телефон: {order_data['phone']}\n"
    order_text += f"Місто: {order_data['city']}\n"
    order_text += f"Відділення НП: {order_data['np']}\n"
    order_text += f"Спосіб оплати: {order_data['payment']}\n"

    total = 0
    for entry in user_carts[user_id]:
        item = next(
            (x for x in products[entry['category']] if x['id'] == entry['item_id']), None)
        if item:
            subtotal = item['price'] * entry['quantity']
            total += subtotal
            order_text += f"{item['name']} — {entry['quantity']} шт x {item['price']} грн = {subtotal} грн\n"

    order_text += f"\n💰 Загальна сума: {total} грн"
    await bot.send_message(ADMIN_ID, order_text)

# === Головне меню ===


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 До магазину", callback_data="go_to_shop"))
    kb.add(InlineKeyboardButton("🛍 Мій кошик", callback_data="view_cart"))
    kb.add(InlineKeyboardButton("📱 Наш канал", url="https://t.me/CPEN_ua"))
    kb.add(InlineKeyboardButton("📖 Вікіпедія", url="https://t.me/CPEN_ua/509"))

    await message.answer("👋 Вітаємо! Виберіть одну з опцій:", reply_markup=kb)

# === Обробка натискання кнопок на головному меню ===


@dp.callback_query_handler(lambda c: c.data == "go_to_shop")
async def go_to_shop(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    for category in products:
        kb.add(InlineKeyboardButton(category, callback_data=f"cat_{category}"))
    kb.add(InlineKeyboardButton("🛒 Мій кошик", callback_data="view_cart"))
    await bot.send_message(callback.message.chat.id, "👋 Вітаємо у магазині! Оберіть категорію:", reply_markup=kb)

# === Вибір категорії ===


@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def category_handler(callback: types.CallbackQuery):
    category = callback.data.split("cat_")[1]
    kb = InlineKeyboardMarkup()
    for item in products[category]:
        kb.add(InlineKeyboardButton(
            item['name'], callback_data=f"item_{category}_{item['id']}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    kb.add(InlineKeyboardButton("🛒 Мій кошик", callback_data="view_cart"))
    await bot.send_message(callback.message.chat.id, f"📦 {category}", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "back_main")
async def back_to_main(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    for category in products:
        kb.add(InlineKeyboardButton(category, callback_data=f"cat_{category}"))
    kb.add(InlineKeyboardButton("🛒 Мій кошик", callback_data="view_cart"))
    await bot.send_message(callback.message.chat.id, "👋 Вітаємо у магазині! Оберіть категорію:", reply_markup=kb)

# === Вибір товару ===


@dp.callback_query_handler(lambda c: c.data.startswith("item_"))
async def item_handler(callback: types.CallbackQuery):
    _, category, item_id = callback.data.split("_", 2)
    item = next((x for x in products[category] if x['id'] == item_id), None)
    if not item:
        await callback.answer("Товар не знайдено")
        return
    photo = InputFile(item['image'])
    caption = f"<b>{item['name']}</b>\n\n{item['description']}\n<b>Ціна:</b> {item['price']} грн"
    kb = InlineKeyboardMarkup(row_width=3)
    for qty in [1, 2, 3]:
        kb.insert(InlineKeyboardButton(
            f"➕ {qty} шт", callback_data=f"add_{category}_{item_id}_{qty}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{category}"))
    kb.add(InlineKeyboardButton("🏷 До категорій",
           callback_data="back_to_categories"))
    # Кнопка "Мій кошик"
    kb.add(InlineKeyboardButton("🛒 Мій кошик", callback_data="view_cart"))
    await bot.send_photo(callback.message.chat.id, photo=photo, caption=caption, parse_mode='HTML', reply_markup=kb)

# === Додавання до кошика ===


@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    _, category, item_id, qty = callback.data.split("_", 3)
    user_id = callback.from_user.id
    qty = int(qty)
    user_carts.setdefault(user_id, [])

    for entry in user_carts[user_id]:
        if entry['item_id'] == item_id:
            entry['quantity'] += qty
            break
    else:
        user_carts[user_id].append(
            {"category": category, "item_id": item_id, "quantity": qty})

    await callback.answer(f"Додано {qty} шт до кошика ✅")

# === Перегляд кошика ===


@dp.callback_query_handler(lambda c: c.data == "view_cart")
async def view_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.message.answer("🛒 Ваш кошик порожній")
        return

    text = "🛒 Ваш кошик:\n"
    total = 0
    kb = InlineKeyboardMarkup()

    for i, entry in enumerate(cart):
        item = next(
            (x for x in products[entry['category']] if x['id'] == entry['item_id']), None)
        if not item:
            continue
        subtotal = item['price'] * entry['quantity']
        total += subtotal
        text += f"{i+1}. {item['name']} — {entry['quantity']} шт x {item['price']} грн = {subtotal} грн\n"
        kb.add(
            InlineKeyboardButton(
                f"➖ {item['name']}", callback_data=f"remove_{entry['item_id']}"),
            InlineKeyboardButton(
                f"➕1", callback_data=f"addqty_{entry['item_id']}"),
            InlineKeyboardButton(
                f"➖1", callback_data=f"subqty_{entry['item_id']}")
        )

    text += f"\n💰 Всього: {total} грн"
    kb.add(InlineKeyboardButton("📦 Оформити замовлення", callback_data="checkout"))
    kb.add(InlineKeyboardButton("⬅️ Назад до категорій",
           callback_data="back_to_categories"))
    kb.add(InlineKeyboardButton("🗑 Очистити кошик", callback_data="clear_cart"))
    await callback.message.answer(text, reply_markup=kb)

# === Повернення до категорій ===


@dp.callback_query_handler(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    for category in products:
        kb.add(InlineKeyboardButton(category, callback_data=f"cat_{category}"))
    # Кнопка "Мій кошик"
    kb.add(InlineKeyboardButton("🛒 Мій кошик", callback_data="view_cart"))
    await bot.send_message(callback.message.chat.id, "👋 Вітаємо у магазині! Оберіть категорію:", reply_markup=kb)

# === Очищення кошика ===


@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = []
    await callback.answer("Ваш кошик очищено! 🧹", show_alert=True)
    await view_cart(callback)

# === Редагування кількості ===


@dp.callback_query_handler(lambda c: c.data.startswith("addqty_"))
async def increase_qty(callback: types.CallbackQuery):
    item_id = callback.data.split("addqty_")[1]
    for entry in user_carts.get(callback.from_user.id, []):
        if entry['item_id'] == item_id:
            entry['quantity'] += 1
            break
    await view_cart(callback)


@dp.callback_query_handler(lambda c: c.data.startswith("subqty_"))
async def decrease_qty(callback: types.CallbackQuery):
    item_id = callback.data.split("subqty_")[1]
    for entry in user_carts.get(callback.from_user.id, []):
        if entry['item_id'] == item_id:
            entry['quantity'] -= 1
            if entry['quantity'] <= 0:
                user_carts[callback.from_user.id].remove(entry)
            break
    await view_cart(callback)


@dp.callback_query_handler(lambda c: c.data.startswith("remove_"))
async def remove_item(callback: types.CallbackQuery):
    item_id = callback.data.split("remove_")[1]
    user_carts[callback.from_user.id] = [
        x for x in user_carts[callback.from_user.id] if x['item_id'] != item_id]
    await view_cart(callback)

# === Оформлення замовлення ===


@dp.callback_query_handler(lambda c: c.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_orders[callback.from_user.id] = {"step": 1, "data": {}}
    await callback.message.answer("✍️ Введіть ваше <b>Імʼя та Прізвище</b>:", parse_mode='HTML')


@dp.message_handler(lambda m: m.from_user.id in user_orders)
async def process_order_data(message: types.Message):
    user_id = message.from_user.id
    order = user_orders[user_id]

    if order['step'] == 1:
        order['data']['name'] = message.text
        order['step'] = 2
        await message.answer("📞 Введіть <b>номер телефону</b>:", parse_mode='HTML')
    elif order['step'] == 2:
        order['data']['phone'] = message.text
        order['step'] = 3
        await message.answer("🏙️ Введіть <b>місто</b> доставки:", parse_mode='HTML')
    elif order['step'] == 3:
        order['data']['city'] = message.text
        order['step'] = 4
        await message.answer("🏤 Введіть <b>відділення Нової Пошти</b>:", parse_mode='HTML')
    elif order['step'] == 4:
        order['data']['np'] = message.text
        order['step'] = 5
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💳 На картку", callback_data="pay_card"),
            InlineKeyboardButton("📦 Накладений платіж",
                                 callback_data="pay_cod")
        )
        await message.answer("💳 Виберіть спосіб оплати:", reply_markup=kb)

# === Платіж ===


@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def payment_method(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    order = user_orders[user_id]
    order['data']['payment'] = callback.data.split("_")[1]

    # Надсилаємо замовлення адміну з нікнеймом користувача
    await send_order_to_admin(user_id, order['data'])

    start_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔄 Start", callback_data="start_menu")
    )
    await callback.message.answer(
        "✅ Замовлення оформлено! Очікуйте підтвердження.\n\nУ разі будь-яких питань звертайтесь до @PETERhhcPEN",
        reply_markup=start_kb
    )

    del user_orders[user_id]  # Очистка замовлення
    user_carts[user_id] = []  # Очистка кошика


@dp.callback_query_handler(lambda c: c.data == "start_menu")
async def start_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 До магазину", callback_data="go_to_shop"))
    kb.add(InlineKeyboardButton("🛍 Мій кошик", callback_data="view_cart"))
    kb.add(InlineKeyboardButton("📱 Наш канал", url="https://t.me/CPEN_ua"))
    kb.add(InlineKeyboardButton("📖 Вікіпедія", url="https://t.me/CPEN_ua/509"))

    await callback.message.answer("👋 Вітаємо! Виберіть одну з опцій:", reply_markup=kb)
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

