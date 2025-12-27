# This script configures a Telegram bot to ask new members questions to avoid spam accounts.
# New members have 30 seconds to answer the questions. If they don't, they are kicked out.
# Install dependency: pip install python-telegram-bot

import os
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

pending_users = {}

questions = {
    1: {"question": "Hvilken by spiller vi FS i? (Du har 30 sekunder på å svare)", "correct_answers": ["Oslo"]},
    2: {"question": "Hvilken farve er det på laget ditt? (Du har 30 sekunder på å svare)", "correct_answers": ["grønn", "blå"]}
}

async def do_kick(bot, chatid, userid):
    """Helper function to kick a user and clean up."""
    if userid in pending_users:
        await bot.ban_chat_member(chatid, userid)
        del pending_users[userid]

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sender første spørsmål når en ny bruker blir med i gruppen."""
    userid = update.message.new_chat_members[0].id
    chatid = update.message.chat.id
    pending_users[userid] = {"chatid": chatid, "question_stage": 1}
    await context.bot.send_message(chatid, questions[1]["question"])
    context.job_queue.run_once(kick_user_timeout, 30, data=(chatid, userid))

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kontrollerer brukerens svar og sender neste spørsmål eller fjerner dem."""
    userid = update.message.from_user.id
    if userid in pending_users:
        stage = pending_users[userid]["question_stage"]
        user_answer = update.message.text.strip().lower()

        if user_answer in [answer.lower() for answer in questions[stage]["correct_answers"]]:
            if stage == 1:
                pending_users[userid]["question_stage"] = 2
                await context.bot.send_message(update.message.chat.id, questions[2]["question"])
                context.job_queue.run_once(kick_user_timeout, 30, data=(update.message.chat.id, userid))
            else:
                del pending_users[userid]
        else:
            await do_kick(context.bot, update.message.chat.id, userid)

async def kick_user_timeout(context: ContextTypes.DEFAULT_TYPE):
    """Fjerner brukere som ikke har svart innen fristen."""
    chatid, userid = context.job.data
    await do_kick(context.bot, chatid, userid)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set the TELEGRAM_BOT_TOKEN environment variable")

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

application.run_polling()
