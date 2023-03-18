import platform
import aiohttp
import asyncio
import datetime
import argparse

URL = "https://api.privatbank.ua/p24api/exchange_rates?date="
CURRENCY_LIST = ["EUR", "USD"]


parser = argparse.ArgumentParser(description="Script for withdrawing currencies")
parser.add_argument(
    "days",
    type=int,
    help="The number of days from today for which you need to withdraw the currency",
)
parser.add_argument(
    "--currency",
    "-c",
    help="Additional currencies (Besides EUR, USD)",
    default=CURRENCY_LIST,
)

args = vars(parser.parse_args())

days = args.get("days")
output = args.get("currency")

# Adding a currency to the main list of currencies
if output not in CURRENCY_LIST:
    CURRENCY_LIST.append(output)


# A function for connecting to the required link and displaying
# the currency for the required dates and in the required format
async def request(c_days: int) -> list:
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


async def convert_to_str(lst):
    result = []
    for d in lst:
        s = "\n".join([f"{key}: {value}" for key, value in d.items()])
        result.append(s)
    return "\n".join(result)

if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    result_str = asyncio.run(request(days))
    print(result_str)
