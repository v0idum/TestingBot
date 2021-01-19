from aiogram.dispatcher.filters.state import StatesGroup, State


class Register(StatesGroup):
    name = State()
    subscribe_channel = State()
