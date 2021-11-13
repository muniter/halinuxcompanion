from dbus_next.aio import MessageBus

Bus: MessageBus


async def init_bus():
    global Bus
    Bus = await MessageBus().connect()
    return Bus
