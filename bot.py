import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from groq import AsyncGroq

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = AsyncGroq(api_key=GROQ_API_KEY)


class MustaqilIshState(StatesGroup):
    waiting_for_topic = State()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "Men Mustaqil ish tayyorlab beruvchi botman.\n"
        "Yangi mustaqil ish tayyorlash uchun quyidagi tugmani bosing.",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📝 Mustaqil ish yozish",
                        callback_data="start_generate",
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data == "start_generate")
async def process_callback_start(
    callback: types.CallbackQuery, state: FSMContext
):
    await callback.message.answer(
        "Mavzuni kiriting:\n*(Masalan: O'zbekistonda raqamli iqtisodiyotni rivojlantirish)*"
    )
    await state.set_state(MustaqilIshState.waiting_for_topic)
    await callback.answer()


@dp.message(MustaqilIshState.waiting_for_topic)
async def generate_work(message: types.Message, state: FSMContext):
    topic = message.text
    status_msg = await message.answer(
        "⏳ Mustaqil ish tayyorlanmoqda, iltimos biroz kuting..."
    )

    prompt = f"""
    Siz akademik darajadagi mutaxassissiz. Quyidagi mavzu bo'yicha mukammal va to'liq mustaqil ish rejasini va matnini tayyorlang:
    Mavzu: {topic}

    Tuzilishi:
    1. Kirish
    2. Asosiy qism (2-3 ta kichik reja va ularning batafsil yoritilishi)
    3. Xulosa
    4. Foydalanilgan adabiyotlar

    Format o'zbek tilida, professional va tushunarli uslubda bo'lsin.
    """

    # Groq'dagi eng faol modellar ro'yxati (biri ishlamasa avtomatik keyingisiga o'tadi)
    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    result_text = None

    for model_name in models_to_try:
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.choices[0].message.content
            break  # Muvaffaqiyatli javob olinsa sikldan chiqiladi
        except Exception as e:
            logging.warning(
                f"Model {model_name} ishlamadi: {e}. Keyingi model sinab ko'rilmoqda..."
            )
            continue

    if result_text:
        if len(result_text) > 4000:
            for i in range(0, len(result_text), 4000):
                await message.answer(result_text[i : i + 4000])
        else:
            await message.answer(result_text)
    else:
        await message.answer(
            "Xatolik yuz berdi: Hozircha birorta AI model javob bera olmadi. Iltimos, Groq API kalitini va ulangan modellarni tekshiring."
        )

    await status_msg.delete()
    await state.clear()


async def handle(request):
    return web.Response(text="Bot is running!")


async def main():
    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
