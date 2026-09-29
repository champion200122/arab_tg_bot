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
    await cq.message.edit_text(START_TEXT, reply_markup=menu_kb())
    await cq.answer()


@router.callback_query(F.data == "menu:lessons")
async def lessons_list(cq: CallbackQuery):
    b = InlineKeyboardBuilder()
    for l in LESSONS:
        b.button(text=l["title"], callback_data=f"lesson:{l['id']}")
    b.button(text="⬅️ Меню", callback_data="menu:main")
    b.adjust(1)
    await cq.message.edit_text("Выбери урок:", reply_markup=b.as_markup())
    await cq.answer()


@router.callback_query(F.data.startswith("lesson:"))
async def lesson_view(cq: CallbackQuery):
    lid = int(cq.data.split(":")[1])
    l = lesson_by_id(lid)
    text = l["title"] + "\n\n" + "\n".join("• " + n for n in l["notes"])
    text += "\n\nСлова урока:\n" + "\n".join(
        f"{w['ar']} — {w['tr']} — {w['ru']}" for w in l["words"]
    )
    await cq.message.edit_text(text, reply_markup=lesson_kb(lid))
    await cq.answer()


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
    _, lid, i = map(int, cq.data.split(":"))
    await show_card(cq, lid, i)
    await cq.answer()


@router.callback_query(F.data.startswith("reveal:"))
async def reveal(cq: CallbackQuery):
    _, lid, i = map(int, cq.data.split(":"))
    w = lesson_by_id(lid)["words"][i]
    b = InlineKeyboardBuilder()
    b.button(text="✅ Знаю", callback_data=f"know:{lid}:{i}:1")
    b.button(text="🔁 Учить", callback_data=f"know:{lid}:{i}:0")
    b.button(text="➡️ Далее", callback_data=f"cards:{lid}:{i + 1}" if i + 1 < len(lesson_by_id(lid)["words"]) else f"lesson:{lid}")
    b.adjust(2, 1)
    await cq.message.edit_text(f"{w['ar']}\n{w['tr']}\n{w['ru']}", reply_markup=b.as_markup())
    await cq.answer()


@router.callback_query(F.data.startswith("know:"))
async def know(cq: CallbackQuery):
    _, lid, i, ok = map(int, cq.data.split(":"))
    record(cq.from_user.id, f"{lid}:{i}", ok)
    l = lesson_by_id(lid)
    if i + 1 < len(l["words"]):
        await show_card(cq, lid, i + 1)
    else:
        await cq.message.edit_text("Карточки урока пройдены 🎉", reply_markup=lesson_kb(lid))
    await cq.answer("Записал")


def quiz_question(lid: int, i: int):
    l = lesson_by_id(lid)
    w = l["words"][i]
    others = [x["ru"] for x in l["words"] if x["ru"] != w["ru"]]
    rnd = random.Random(f"{lid}:{i}")  # детерминированно: без состояния
    rnd.shuffle(others)
    opts = [w["ru"]] + others[:3]
    rnd.shuffle(opts)
    return w, opts


@router.callback_query(F.data.startswith("quiz:"))
async def quiz(cq: CallbackQuery):
    _, lid, i = map(int, cq.data.split(":"))
    w, opts = quiz_question(lid, i)
    b = InlineKeyboardBuilder()
    for n, o in enumerate(opts):
        b.button(text=o, callback_data=f"ans:{lid}:{i}:{n}")
    b.button(text="⬅️ Выйти", callback_data="menu:main")
    b.adjust(1)
    await cq.message.edit_text(
        f"Вопрос {i + 1}: как переводится\n{w['ar']} ?", reply_markup=b.as_markup()
    )
    await cq.answer()


@router.callback_query(F.data.startswith("ans:"))
async def ans(cq: CallbackQuery):
    _, lid, i, n = map(int, cq.data.split(":"))
    w, opts = quiz_question(lid, i)
    ok = 1 if opts[n] == w["ru"] else 0
    record(cq.from_user.id, f"{lid}:{i}", ok)
    l = lesson_by_id(lid)
    b = InlineKeyboardBuilder()
    if i + 1 < len(l["words"]):
        b.button(text="➡️ Дальше", callback_data=f"quiz:{lid}:{i + 1}")
    else:
        b.button(text="🏁 Итоги", callback_data="menu:progress")
    b.button(text="⬅️ Урок", callback_data=f"lesson:{lid}")
    b.adjust(1)
    mark = "✅ Верно!" if ok else "❌ Мимо."
    await cq.message.edit_text(
        f"{mark}\n{w['ar']} — {w['tr']} — {w['ru']}", reply_markup=b.as_markup()
    )
    await cq.answer()


@router.callback_query(F.data == "menu:progress")
async def progress(cq: CallbackQuery):
    rows = stats(cq.from_user.id)
    total = sum(len(l["words"]) for l in LESSONS)
    answers = sum(cr + wr for _, cr, wr in rows)
    correct = sum(cr for _, cr, wr in rows)
    learned = sum(1 for _, cr, wr in rows if cr >= 2 and cr > wr)
    acc = f"{correct / answers:.0%}" if answers else "—"
    await cq.message.edit_text(
        f"📊 Прогресс\n\nОтветов: {answers}\nТочность: {acc}\n"
        f"Выучено слов: {learned} из {total}",
        reply_markup=menu_kb(),
    )
    await cq.answer()
