# Source Code of the Stripe Integrated Telegram Bot

Welcome to the source code repository of the [Shoe shop :)](https://t.me/example_mert_1_bot). This bot is designed to be an example of telegram/stripe integration.

Why do you use a custome code for stripe integration, if you can use build in Stripe payment processor in telegram?
Answer : You can do what. But only for one-time purchase products, not for subscriptions. So this bot is actually intended to work with subscriptions after  being connected to a database. Purchase of a single product this way - is overkill, and this code just serve as an example of webhook integration.

If you sell one-time purchase products, use implemented telegram payment system, its much better.

# How to Start a Bot

## 1. Download the Repository

Download the repository using either the GitHub UI or the command line:

```bash
git clone https://github.com/Corots/antivirusbot.git
```

## 2. Install python libralies.

First, set up a Python virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment and install the required Python libraries:

```bash
source venv/bin/activate  # On Unix/macOS
venv\Scripts\activate.bat  # On Windows
pip install -r requirements.txt
```

## 3. Create Configuration File

Create a file named .env in the main folder:

```bash
BOT_TOKEN = "515234234234:AAHnsdfsdgfsdfgdfgdfgdfg"
STRIPE_WEBHOOK_SECRET = "whsec_Psdffgbfghfhfhthgrthfghfgh"
STRIPE_API_KEY = "sk_test_51LWj2lCdZZ4TRsCin0sdfscdfsefscfsfgscfsdcfsdfcsdfcsdcf"
STRIPE_LINK = "https://buy.stripe.com/test_bxgrdgergergergerg"
```

Replace placeholders with your actual bot data.

## 4. install a connection between api endpoint and EC2 instance.

Follow the instructions in this [video tutorial](https://www.youtube.com/watch?v=UKP0AkAoJiE) to set up a connection between the API endpoint and your EC2 instance.

Use the provided nginx_config file to connect the endpoint and your EC2 instance.

```bash
server {
    listen 80;
    server_name *my_public_ip*;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 9000;
    server_name *my_private_ip*;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

## 5. Add a webhook to your stripe dashboard

```bash
https://dashboard.stripe.com/webhooks
```

Navigate to [Stripe Dashboard](https://dashboard.stripe.com/webhooks) and add a webhook.

Add the webhook secret to the STRIPE_WEBHOOK_SECRET variable in the .env file.

## 6. Add a payment link

Go to [Stripe Payment Links](https://dashboard.stripe.com/payment-links) and create a payment link.

Add the payment link to the STRIPE_LINK variable in the .env file.

## 7. Start the Bot

Start the bot using the following command:

```bash
python stripebot.py
```

Enjoy!
