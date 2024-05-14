import asyncio
import logging
import multiprocessing
import threading
from fastapi import FastAPI
import uvicorn
import os
import stripe
from fastapi import HTTPException
from fastapi import Header, Request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.command import Command

from load_dotenv import load_dotenv

load_dotenv()

from aiogram.types import PreCheckoutQuery, ShippingQuery, SuccessfulPayment
from aiogram.methods.answer_pre_checkout_query import AnswerPreCheckoutQuery
from aiogram.methods.answer_shipping_query import AnswerShippingQuery
from aiogram.enums.content_type import ContentType
from aiogram import F


# those two is important for a webhook
stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRIPE_LINK = os.getenv("STRIPE_LINK")
PAYMENTS_PROVIDER_TOKEN = os.getenv("PAYMENTS_PROVIDER_TOKEN")
photo_url = (
    """https://stripe-camo.global.ssl.fastly.net/49f5fa9057b6e8cbd766bb826b196557402870b98afc364636679d13453bc56b/68747470733a2f2f66696c65732e7374726970652e636f6d2f6c696e6b732f4d44423859574e6a64463878544664714d6d78445a4670614e46525363304e7066475a735833526c633352666231644e637a56544e6b747263316f335255786f4e46686a566d4a53593056743030426c493253306266""",
)


# Initialize Bot instance with default bot properties which will be passed to all API calls
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# add commands for the bot
async def set_commands(new_bot: Bot):
    # set commands
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "get_link", "description": "Get the payment link"},
        {
            "command": "my_shoes",
            "description": "How much of the shoes you bought from me?",
        },
    ]
    await new_bot.set_my_commands(commands)


# command "start"
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        """Hello! I am a bot that can generate a payment link for you. And you can buy shoes from me. Isn't it awesome? 
        
Use the command /get_link to get the paymet link outside of the telegram.

Use the command /pay_by_telegram to pay directly from the telegram.
"""
    )


@dp.message(Command("about"))
async def about(message: types.Message):
    await message.answer(
        """Hello! I am a bot that can generate a payment link for you. And you can buy shoes from me. Isn't it awesome? 
        
Use the command /get_link to get the paymet link outside of the telegram.

Use the command /pay_by_telegram to pay directly from the telegram.
"""
    )


@dp.message(Command("stop"))
async def about(message: types.Message):
    await message.answer(
        """Command is not implemented yet.
"""
    )


# command "get_link" to get the link
@dp.message(Command("get_link"))
async def link(message: types.Message):
    await message.answer(
        f"""Here is your link: {StripeEventClass.use_existing_payment_link(message.from_user.id)}.

You can use a fake credit card number 4242 4242 4242 4242 to test the payment.

Data of expiration date and CVC can be any future date and any 3 digits respectively.

Email can be any email address. You can use a fake email address to test the payment.
        
        """
    )


# Setup prices
prices = [
    types.LabeledPrice(label="Working Time Machine", amount=200),
    types.LabeledPrice(label="Gift wrapping", amount=100),
]

# Setup shipping options
shipping_options = [
    types.ShippingOption(
        id="instant",
        title="WorldWide Teleporter",
        prices=[types.LabeledPrice(label="Teleporter", amount=1000)],
    ),
    types.ShippingOption(
        id="pickup",
        title="Local pickup",
        prices=[types.LabeledPrice(label="Pickup", amount=300)],
    ),
]


@dp.message(Command("pay_by_telegram"))
async def pay(message: types.Message, bot: Bot):
    """
    Start payment process
    """

    await bot.send_invoice(
        message.chat.id,
        title="Awesome Shoes",
        description="""Want to buy a pair of shoes?
        We have the best shoes in the world!""",
        provider_token=PAYMENTS_PROVIDER_TOKEN,
        currency="usd",
        photo_url=photo_url[0],
        photo_height=512,  # !=0/None or picture won't be shown
        photo_width=512,
        photo_size=512,
        is_flexible=True,  # True If you need to set up Shipping Fee
        prices=prices,
        start_parameter="shoes-example",
        payload="HAPPY FRIDAYS COUPON",
    )


# * Send payment cofirmation
@dp.pre_checkout_query()
async def confirm_pay(query: types.PreCheckoutQuery, bot: Bot):
    """
    Confirmed payment method
    """

    await bot(
        AnswerPreCheckoutQuery(
            pre_checkout_query_id=query.id,
            ok=True,
            error_message="Aliens tried to steal your card's CVV,"
            " but we successfully protected your credentials,"
            " try to pay again in a few minutes, we need a small rest.",
        )
    )


# * Send shipping confirmation
@dp.shipping_query()
async def shipping(shipping_query: types.ShippingQuery):

    await bot(
        AnswerShippingQuery(
            shipping_query_id=shipping_query.id,
            shipping_options=shipping_options,
            ok=True,
            error_message="Oh, seems like our Dog couriers are having a lunch right now."
            " Try again later!",
        )
    )


@dp.message(F.successful_payment)
async def got_payment(message: types.Message):
    await message.answer_photo(
        photo=photo_url[0],
        caption="Hoooooray! Thanks for payment! We will proceed your order for `{} {}`"
        " as fast as possible! Stay in touch."
        "\n\nUse /start again to get a pair of shoes for your friend!".format(
            message.successful_payment.total_amount / 100,
            message.successful_payment.currency,
        ),
        parse_mode="Markdown",
    )


class StripeEventClass:
    def __init__(self, payload: bytes, sig_header: str):
        event = None
        try:
            # construct event
            event = stripe.Webhook.construct_event(
                payload, sig_header, stripe_webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            raise HTTPException(status_code=401, detail="Invalid payload")
        except stripe.SignatureVerificationError as e:
            # Invalid signature
            raise HTTPException(status_code=402, detail="Invalid signature")

        self.event = event
        self.data_object = event["data"]["object"]

    def handle_event(self):

        success_response = {"status": "success"}
        not_handled_response = {"status": "this event is not handled"}

        if self.event.type == "checkout.session.completed":
            client_id = self._handle_checkout_session_complete()
            # add client_id to the response
            success_response["client_id"] = client_id
            return success_response

        # return not_handled_response

    def _handle_checkout_session_complete(self):

        client_reference_id = self._get_client_reference_id()

        logging.info(f"client_reference_id: {client_reference_id}")
        return client_reference_id

    def _get_client_reference_id(self):
        # get reference if ["data"]["object"]["client_reference_id"] keys exists
        if "client_reference_id" in self.data_object:
            client_reference_id = self.data_object["client_reference_id"]
            return str(client_reference_id)
        else:
            raise HTTPException(status_code=411, detail="client_reference_id not found")

    @staticmethod
    def use_existing_payment_link(client_reference_id: str) -> str:
        link = f"{STRIPE_LINK}?client_reference_id={client_reference_id}"

        return link


# Create a FastAPI application
app = FastAPI(root_path="/webhook")


@app.get("/")
async def read_root():
    return {
        "message": "Hello, World! This is my FastAPI web application. This is the root path."
    }


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    event = StripeEventClass(payload, stripe_signature)
    result = event.handle_event()

    if result:
        # Open the photo file
        await bot.send_photo(
            chat_id=result["client_id"],
            caption=f"Enjoy your shoes!",
            # photo=types.FSInputFile("shoes.png"),
            photo=photo_url[0],
        )
    logging.info(f"Stripe event is sent to the bot.")
    return result


# method to send data to the bot
@app.post("/send-message")
async def send_message(chat_id: str):

    await bot.send_photo(
        chat_id=chat_id,
        caption=f"Enjoy your shoes!",
        photo=types.FSInputFile("shoes.png"),
    )
    logging.info(f"Message is sent to the bot.")
    return {"status": "success"}


def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def run_bot():
    # set commands
    # asyncio.run(set_commands(bot))
    async def run_instance_bot():
        await set_commands(bot)
        await dp.start_polling(bot)

    asyncio.run(run_instance_bot())


async def main():
    process1 = multiprocessing.Process(target=run_fastapi)
    process2 = multiprocessing.Process(target=run_bot)

    # Start both processes
    process1.start()
    process2.start()

    # Wait for both processes to finish
    process1.join()
    process2.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
