import asyncio
import logging

from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions
from aiogram.utils.markdown import hitalic, text, hcode, hbold

from states import Register
from sqliter import db
from config import CHANNEL


log = logging.getLogger(__name__)


async def is_user_subscribed(user_id: int, channel_username: str) -> bool:
    channel_member = await Bot.get_current().get_chat_member(channel_username, user_id)
    return channel_member['status'] != 'left'


async def user_exists_and_not_subscribed(message: types.Message) -> bool:
    return db.user_exists(message.from_user.id) and not await is_user_subscribed(message.from_user.id, CHANNEL)


async def confirm_subscription(message: types.Message):
    await Register.subscribe_channel.set()
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Kanalga o'tish", url='https://t.me/RKKimyo'))
    markup.add(InlineKeyboardButton('Tekshirish', callback_data='check_subscription'))
    await message.answer(hitalic('Botdan foydalanish uchun @RKKimyo kanaliga obuna bolishingiz kerak'),
                         reply_markup=markup)


def calc_correct_answers(results: str, answers: str) -> int:
    correct_answers = 0
    for i in range(len(results)):
        if results[i] == answers[i]:
            correct_answers += 1
    return correct_answers


def _format_user_result(user: tuple) -> str:
    num, user = user
    return f'{num}. {user[0]} - {user[1]} ta'


async def help_message(message: types.Message):
    await message.answer(
        text(
            hbold('1️⃣ Test yaratish uchun\n'),
            hcode("+test*Fan nomi*to'g'ri javoblar\n"),
            "ko`rinishida yuboring\n",
            hbold("Misol:"),
            hcode("+test*Kimyo*abbccabd...\n"),
            hbold('2️⃣ Test javoblarini yuborish uchun\n'),
            hcode("test kodi*abbcbccdd...\n"),
            "kabi ko`rinishlarda yuboring.\n",
            hbold("Misol:"),
            hcode("1234*abbcabcdd...\n"),

            sep='\n'
        )
    )


def get_test_status(subject: str, test_code, tests_number):
    status = f'Fan: {subject}\nTest kodi: {test_code}\nSavollar soni: {tests_number}\n\n'
    tests_results = db.get_test_results(test_code)
    results_str = "✅Natijalar:\n\n" + "\n".join(map(_format_user_result, enumerate(tests_results, 1)))
    return status + results_str


async def broadcast_test_results(test_id, result: str):
    students = db.get_students_passed_test(test_id)
    for student in students:
        await _send_test_result(student[0], result)


async def _send_test_result(user_id: int, message: str):
    """
    Safe messages sender
    :param user_id:
    :param message:
    :return:
    """
    try:
        await Bot.get_current().send_message(user_id, message)
    except exceptions.BotBlocked:
        log.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        log.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        log.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await _send_test_result(user_id, message)  # Recursive call
    except exceptions.UserDeactivated:
        log.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        log.exception(f"Target [ID:{user_id}]: failed")
