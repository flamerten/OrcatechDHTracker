#Code for the telegram bot where residents interact with the bot to find out the capacity


import logging
import pandas as pd
import time
import subprocess
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

bot_token = 'CAPACITY_BOT_TOKEN'
csv_records = 'DHCapacityRecords.csv'
capacity_text_file = 'capacity.txt'

max_capacity = 400 #estimated

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def read_text_file():
    f = open(capacity_text_file,'r')
    res = f.read()
    f.close()
    return(int(res))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = KeyboardButton( text = '/getCapacity')
    reply_markup = ReplyKeyboardMarkup([[keyboard,]])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the RC4/CAPT DH capacity bot",reply_markup=reply_markup) #easy to press and get capacity


#Resident Telegram Bot Commands
async def capacityKey(update:Update, context: ContextTypes.DEFAULT_TYPE):
    curr_capac = read_text_file()
    percentage = int(curr_capac/max_capacity * 100)
    time_now = time.localtime()

    text = time.strftime("%d %b %Y - %H:%M:%S",time_now)

    text += "\nThe number of people in the RC4 Capt DH is: " + str(curr_capac) +"."
    text += "\nThe capacity is "+ str(percentage) +"%."
    text += "\nNote that this number has been doubled as sensors have not been integrated on the CAPT side yet."

    await context.bot.send_message(chat_id = update.effective_chat.id,text = text)


#Admin Telegram Bot commands START
#should probably set some restriction to specific users
async def downloadRecords(update:Update,context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_document(
        chat_id = update.effective_chat.id,
        document = open(csv_records, 'rb'),
        filename = "DHCapacityRecords.csv",
        caption = "Capacity Records"
        )

async def changeMaxCapac(update:Update,context: ContextTypes.DEFAULT_TYPE):
    global max_capacity
    try:
        max_capac = float(context.args[0])
        max_capacity = max_capac


        text = f"MaxCapacity successfully set to {int(max_capacity)}."
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /changeMaxCapac <MaxCapacity>")

async def clearCSV(update:Update,context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_csv(csv_records,index_col = 0)
    cleared_file = df[df['Number'] == -10] #we program number to be -1, 0, 1
    cleared_file.to_csv("DHCapacityRecords.csv")

    text = "CSV file cleared"
    await context.bot.send_message(chat_id = update.effective_chat.id,text = text)


async def adminCommands(update:Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
/admin - admin commands
/downloadFiles - download the csv datafiles
/changeMaxCapac - Usage: /changeMaxCapac <MaxCapacity>
/clearCSV - clear the CSV file
/checkConnected - do a scan for the connected devices
 """

    await context.bot.send_message(chat_id = update.effective_chat.id,text = text)


#Admin Telegram Bot Commands - END

async def checkConnected(update:Update, context: ContextTypes.DEFAULT_TYPE):
    result = subprocess.Popen("bash nmap_script.sh", shell=True, stdout=subprocess.PIPE).stdout.read().decode()
    text = f"""
Connected devices:
{result}
"""
    await context.bot.send_message(chat_id = update.effective_chat.id,text = text)


if __name__ == '__main__':
    application = ApplicationBuilder().token(bot_token).build()
    
    start_handler = CommandHandler('start', start)
    capacity_handler = CommandHandler('getCapacity',capacityKey)
    downloader_handler = CommandHandler('downloadFiles',downloadRecords)
    adminCommands_handler = CommandHandler('admin',adminCommands)
    change_max_capac_handler = CommandHandler('changeMaxCapac',changeMaxCapac)
    checkConnected_handler = CommandHandler('checkConnected',checkConnected)

    application.add_handler(start_handler)
    application.add_handler(capacity_handler)
    application.add_handler(downloader_handler)
    application.add_handler(adminCommands_handler)
    application.add_handler(change_max_capac_handler)
    application.add_handler(checkConnected_handler)

    application.run_polling()
