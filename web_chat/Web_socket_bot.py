import asyncio
import logging
import datetime
import aiohttp

import websockets
import names
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK


URL = "https://api.privatbank.ua/p24api/exchange_rates?date="
CURRENCY_LIST = ["EUR", "USD"]


logging.basicConfig(level=logging.INFO)


# A function for connecting to the required link and displaying
# the currency for the required dates and in the required format
async def request(c_days: int = 1) -> list:
    if c_days > 10:
        c_days = 10
        print("The script displays data for no more than 10 days")
    async with aiohttp.ClientSession() as session:
        result = []
        for day in range(c_days):
            try:
                dat = get_date(day)
                print(dat)

                async with session.get(URL + f"{dat}") as resp:
                    if resp.status == 200:
                        data_from_pb = await resp.json()
                        res = await get_exchange(data_from_pb, CURRENCY_LIST)
                        result.append(res)
                    else:
                        print(f"Error status: {resp.status} for {URL}")

            except aiohttp.ClientConnectorError as err:
                print(f"Connection error: {URL}", str(err))

        return await convert_to_str(result)


# Function to get a filtered dictionary with the currencies we need
async def get_exchange(data: str, curr_lst: list) -> dict:
    currency = {}
    main_dict = {}

    for rec in data["exchangeRate"]:
        if rec["currency"] in curr_lst:
            currency[rec["currency"]] = {
                "Продаж": rec["saleRate"],
                "Купівля": rec["purchaseRate"],
            }

        main_dict[data["date"]] = currency

    return main_dict


# Function to get date relative to days starting from today
def get_date(day: str) -> str:
    today = datetime.datetime.today()
    day_ago = today - datetime.timedelta(days=day)
    return day_ago.strftime("%d.%m.%Y")


# Function to translate a list into a dictionary
async def convert_to_str(lst):
    result = []
    for d in lst:
        s = "\n".join([f"{key}: {value}" for key, value in d.items()])
        result.append(s)
    return "\n".join(result)


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f"{ws.remote_address} connects")

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f"{ws.remote_address} disconnects")

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            pars_mess = message.split()
            if message.startswith('exchange'):
                if pars_mess[1].isdigit():
                    answer = await request(int(pars_mess[1]))
                    await self.send_to_clients(answer)
                else:
                    answer = "The first argument can only be a digit"
                    await self.send_to_clients(answer)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")

async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, "localhost", 5501):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
