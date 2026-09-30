import random

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from content import LESSONS, lesson_by_id
from storage import record, stats

router = Router()

START_TEXT = (
    "Привет! Учим арабский точно и по порядку.\n"
    "Слова даны с огласовками и проверенной транслитерацией.\n\n"
    "Выбери раздел:"
)


def menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📚 Уроки", callback_data="menu:lessons")
    b.button(text="⚡️ Тест", callback_data="quiz:1:0")
    b.button(text="📊 Прогресс", callback_data="menu:progress")
    b.adjust(1)
    return b.as_markup()


def lesson_kb(lid: int):
    b = InlineKeyboardBuilder()
    b.button(text="🃏 Карточки", callback_data=f"cards:{lid}:0")
    b.button(text="⚡️ Тест по уроку", callback_data=f"quiz:{lid}:0")
    b.button(text="⬅️ Все уроки", callback_data="menu:lessons")
    b.adjust(2, 1)
    return b.as_markup()


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(m: Message):
    await m.answer(START_TEXT, reply_markup=menu_kb())


@router.message(F.text)
async def fallback(m: Message):
    await m.answer("Используй кнопки меню 👇", reply_markup=menu_kb())


@router.callback_query(F.data == "menu:main")
async def menu_main(cq: CallbackQuery):
    await cq.answer()
    await cq.message.edit_text(START_TEXT, reply_markup=menu_kb())


@router.callback_query(F.data == "menu:lessons")
async def lessons_list(cq: CallbackQuery):
    await cq.answer()
    b = InlineKeyboardBuilder()
    for l in LESSONS:
        b.button(text=l["title"], callback_data=f"lesson:{l['id']}")
    b.button(text="⬅️ Меню", callback_data="menu:main")
    b.adjust(1)
    await cq.message.edit_text("Выбери урок:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("lesson:"))
async def lesson_view(cq: CallbackQuery):
    await cq.answer()
    lid = int(cq.data.split(":")[1])
    l = lesson_by_id(lid)
    text = l["title"] + "\n\n" + "\n".join("• " + n for n in l["notes"])
    text += "\n\nСлова урока:\n" + "\n".join(
        f"{w['ar']} — {w['tr']} — {w['ru']}" for w in l["words"]
    )
    await cq.message.edit_text(text, reply_markup=lesson_kb(lid))


async def show_card(cq: CallbackQuery, lid: int, i: int):
    l = lesson_by_id(lid)
    w = l["words"][i]
    text = f"{l['title']}\nКарточка {i + 1}/{len(l['words'])}\n\n{w['ar']}\n\nЧто это значит?"
    b = InlineKeyboardBuilder()
    b.button(text="👁 Показать", callback_data=f"reveal:{lid}:{i}")
    if i + 1 < len(l["words"]):
        b.button(text="➡️ Далее", callback_data=f"cards:{lid}:{i + 1}")
    b.button(text="⬅️ Урок", callback_data=f"lesson:{lid}")
    b.adjust(1)
    await cq.message.edit_text(text, reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("cards:"))
async def cards(cq: CallbackQuery):
    await cq.answer()
    _, lid, i = map(int, cq.data.split(":"))
    await show_card(cq, lid, i)


@router.callback_query(F.data.startswith("reveal:"))
async def reveal(cq: CallbackQuery):
    await cq.answer()
    _, lid, i = map(int, cq.data.split(":"))
    l = lesson_by_id(lid)
    w = l["words"][i]
    b = InlineKeyboardBuilder()
    b.button(text="✅ Знаю", callback_data=f"know:{lid}:{i}:1")
