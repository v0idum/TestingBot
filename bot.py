from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hcode, text

from datetime import datetime

import config
import logging

from sqliter import db
from aiogram import Bot, Dispatcher, executor, types, filters

from services import (is_user_subscribed, user_exists_and_not_subscribed, confirm_subscription, calc_correct_answers,
                      help_message, get_test_status, broadcast_test_results)
from states import Register

logging.basicConfig(level=logging.INFO, filename='logs.log')

bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=JSONStorage('states.json'))


async def shutdown_storage(dispatcher: Dispatcher):
    db.close()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


@dp.message_handler(user_exists_and_not_subscribed)
async def check_subscription(message: types.Message):
    await confirm_subscription(message)


@dp.callback_query_handler(state=Register.subscribe_channel)
@dp.message_handler(state=Register.subscribe_channel)
async def process_subscription(query: types.CallbackQuery, state: FSMContext):
    if type(query) == types.Message:
        await query.delete()
        return

    if not await is_user_subscribed(query.from_user.id, config.CHANNEL):
        await query.answer('Kanalimizga obuna bolishingiz lozim!', show_alert=True)
        return

    await query.answer()
    await query.message.answer('Kanalimizga obuna bolganiz bilan tabriklimiz!')
    await help_message(query.message)
    await state.finish()


@dp.message_handler(filters.CommandStart())
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` command
    """
    if db.user_exists(message.from_user.id):
        await help_message(message)
        return

    await message.answer("Bizning Test botimizga xush kelibsiz!")

    await Register.name.set()

    await message.answer(text(
        hbold("Foydalanishni boshlash uchun ism va familiyangizni jo'nating"),
        sep=" ")
    )


@dp.message_handler(lambda message: message.text.startswith('fio*'), state='*')
@dp.message_handler(state=Register.name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text[4:].title() if message.text.startswith('fio*') else message.text
    joined_at = datetime.now()
    db.add_user(user_id, name, joined_at)
    await message.answer('Malumotlaringiz yozildi!')
    await state.finish()
    if not await is_user_subscribed(user_id, config.CHANNEL):
        await confirm_subscription(message)
        return
    await help_message(message)


@dp.message_handler(regexp=r'^\+test\*[a-zA-Z ]+\*[a-fA-F]+$')
async def create_test(message: types.Message):
    parts = message.text.split('*')
    subject = parts[1].title()
    answers = parts[2].lower()
    tests_num = len(answers)
    test_code = db.add_test(subject, answers, message.from_user.id, tests_num)
    await message.answer(text(
        hbold('✅Test bazaga qo`shildi!'),
        f'Test kodi: {test_code}\nFan: {subject}\nSavollar soni: {tests_num} ta',
        'Testda qatnashuvchilar quyidagi ko`rinishda javob yuborishlari mumkin:',
        hcode(f'{test_code}*abcdab... ({tests_num} ta)'),
        sep='\n\n'
    ))


@dp.message_handler(regexp=r'^[0-9]+\*[a-fA-F]+$')
async def check_test(message: types.Message):
    # Extract test info
    test_info = message.text.split('*')
    test_code = test_info[0]
    answers = test_info[1].lower()

    test = db.get_test(test_code)
    if not test:
        await message.answer(
            'Xatolik!\nTest bazadan topilmadi.\nTest kodini noto`g`ri yuborgan bo`lishingiz mumkin, iltimos tekshirib '
            'qaytadan yuboring. '
        )
        return
    if test[5]:
        await message.answer(
            'Xatolik!\nTest yakunlangan!'
        )
        return
    if db.user_passed_test(message.from_user.id, test_code):
        await message.answer(
            '❗️❗️❗Siz oldinroq bu testga javob yuborgansiz.\nBitta testga faqat bir marta javob yuborish mumkin!'
        )
        return
    if test[4] != len(answers):
        await message.answer(f"Xatolik! Testlar soni {test[4]} ta bo'lishi kerak!")
        return

    correct_answers = calc_correct_answers(answers, test[2])
    ratio = correct_answers / test[4]
    db.add_test_result(test_code, message.from_user.id, answers, correct_answers)

    user = db.get_user(message.from_user.id)
    await message.answer(text(
        text(hbold(f'👤Foydalanuvchi: '), hcode(f'{user[1]}\n')),
        f'📚 Fan: {test[1]}',
        text(f'📖 Test kodi: ', hbold(test_code)),
        f'✏ Jami savollar soni: {test[4]} ta',
        f"✅ To'g'ri javoblar soni: {correct_answers} ta",
        f'🔣 Foiz: {ratio:.1%}\n',
        f'🕐 Sana, vaqt: {datetime.now().strftime(config.DATETIME_FORMAT)}',
        sep='\n'
    ))

    # Notify test author about passage of his test
    test_author = test[3]

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Joriy holat', callback_data=f'status*{test[1]}*{test_code}*{test[4]}'))
    markup.add(InlineKeyboardButton('Yakunlash', callback_data=f'finish*{test[1]}*{test_code}*{test[4]}*{test[2]}'))

    await bot.send_message(
        test_author, f'{user[1]} {test[1]} fanidan {test_code} kodli testning javoblarini yubordi',
        reply_markup=markup
    )


@dp.callback_query_handler(lambda query: query.data.startswith('status'))
async def show_test_status(query: types.CallbackQuery):
    await query.answer()
    test_info = query.data.split('*')
    subject = test_info[1]
    test_code = test_info[2]
    tests_number = test_info[3]

    status = 'Test holati.\n\n' + get_test_status(subject, test_code, tests_number)

    await query.message.answer(status)


@dp.callback_query_handler(lambda query: query.data.startswith('finish'))
async def finish_test(query: types.CallbackQuery):
    await query.answer()
    test_info = query.data.split('*')
    subject = test_info[1]
    test_code = test_info[2]
    tests_number = test_info[3]
    answers = test_info[4]

    db.finish_test(test_code)

    status = '🔐Test yakunlandi.\n\n' + get_test_status(subject, test_code, tests_number) + '\n\n'

    correct_answers = "To`g`ri javoblar:\n" + " ".join(
        map(lambda answer: f'{answer[0]}.{answer[1]}', enumerate(list(answers), 1))
    )

    result = status + correct_answers

    await query.message.answer(result)
    await broadcast_test_results(test_code, result)


@dp.message_handler(commands='myinfo')
async def my_info(message: types.Message):
    user = db.get_user(message.from_user.id)
    await message.answer(text(
        hbold("Sizning ma'lumotlaringiz:\n"),
        '👤 Ism familiya:',
        hcode(f'{user[1]}\n'),
        f'Sana, vaqt: {datetime.strptime(user[2], "%Y-%m-%d %H:%M:%S.%f")}',
        sep='\n'
    ))
    await message.answer(text(
        hbold("Agar Ism familiyangizni o'zgartirishni xoxlasangiz\n"),
        hcode('fio*ism familiya\n'),
        "👆 ko'rinishda yozib yuboring.\n",
        hbold('Misol:'),
        hcode('fio*Valijon Alijonov'),
        sep='\n'
    ))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown_storage)
