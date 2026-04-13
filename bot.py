import asyncio
import pandas as pd
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# 🔑 التوكن و API
TOKEN = "8778099794:AAFJ_EGXMtN2oaUVcVjrzclaTloDutuAHyk"
API_KEY = "d1f205e03ae5429480a031872ca1ca1b"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# تخزين الزوج لكل مستخدم
user_pair = {}

# الأزواج
pairs = [
    ["EURUSD", "GBPUSD", "USDJPY"],
    ["AUDUSD", "USDCAD", "USDCHF"],
    ["NZDUSD", "EURGBP", "EURJPY"],
    ["GBPJPY", "AUDJPY", "EURAUD"],
]

# الكيبورد
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=p) for p in row] for row in pairs
    ] + [[KeyboardButton(text="تحليل 📊")]],
    resize_keyboard=True
)

# بدء البوت
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("🔥 اختر الزوج ثم اضغط تحليل", reply_markup=keyboard)

# اختيار الزوج (مصحح)
@dp.message(F.text.in_([
    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF",
    "NZDUSD","EURGBP","EURJPY","GBPJPY","AUDJPY","EURAUD"
]))
async def choose_pair(message: Message):
    user_pair[message.from_user.id] = message.text
    await message.answer(f"✅ تم اختيار: {message.text}")

# التحليل
@dp.message(F.text == "تحليل 📊")
async def analyze(message: Message):
    pair = user_pair.get(message.from_user.id)

    if not pair:
        await message.answer("❌ اختر زوج أولاً")
        return

    await message.answer("📡 جاري التحليل...")

    try:
        pair_api = pair[:3] + "/" + pair[3:]
        url = f"https://api.twelvedata.com/time_series?symbol={pair_api}&interval=1min&outputsize=50&apikey={API_KEY}"

        # جلب البيانات (async)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        # تحقق من البيانات
        if "values" not in data:
            await message.answer(f"❌ API Error:\n{data}")
            return

        df = pd.DataFrame(data["values"])
        df["close"] = df["close"].astype(float)

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        last_rsi = rsi.dropna().iloc[-1]

        # EMA (فلتر الاتجاه)
        df["ema"] = df["close"].ewm(span=20).mean()
        last_price = df["close"].iloc[-1]
        last_ema = df["ema"].iloc[-1]

        # إشارات احتراف
        if last_rsi < 30 and last_price > last_ema:
            signal = "🟢 شراء قوي 🔥"
        elif last_rsi < 45:
            signal = "🟢 شراء"
        elif last_rsi > 70 and last_price < last_ema:
            signal = "🔴 بيع قوي 🔥"
        elif last_rsi > 55:
            signal = "🔴 بيع"
        else:
            signal = "⏸️ انتظار"

        await message.answer(
            f"""
📊 الزوج: {pair_api}
📉 RSI: {round(last_rsi,2)}
📈 السعر: {last_price}
📊 EMA20: {round(last_ema,5)}

🎯 الإشارة: {signal}
"""
        )

    except Exception as e:
        await message.answer(f"❌ خطأ: {e}")

# تشغيل البوت
async def main():
    print("🚀 Bot Running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())