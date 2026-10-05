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

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.choices[0].message.content

        if len(result_text) > 4000:
            for i in range(0, len(result_text), 4000):
                await message.answer(result_text[i : i + 4000])
        else:
            await message.answer(result_text)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

    await status_msg.delete()
    await state.clear()


# Render'ning bepul Web Service rejimi uchun soxta veb-server
async def handle(request):
    return web.Response(text="Bot is running!")


async def main():
    logging.basicConfig(level=logging.INFO)

    # Veb-serverni Render ajratgan PORT bilan ishga tushirish
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())
