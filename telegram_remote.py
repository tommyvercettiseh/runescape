import io
import time

import mss
from PIL import Image

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from pynput.keyboard import Controller as KeyboardController



keyboard = KeyboardController()


def grab_screen_png_bytes(monitor=1) -> bytes:
    with mss.mss() as sct:
        mon = sct.monitors[monitor]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("pong ✅")


async def cmd_shot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    png = grab_screen_png_bytes(monitor=1)
    await update.effective_message.reply_photo(photo=png, caption="📸 Screenshot")


async def cmd_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text or ""
    payload = text[len("/type") :].lstrip()

    if not payload:
        await update.effective_message.reply_text("Gebruik: /type jouw tekst")
        return

    time.sleep(0.15)
    for ch in payload:
        keyboard.type(ch)
        time.sleep(0.01)

    await update.effective_message.reply_text(f"Getypt ✅ ({len(payload)} chars)")


async def on_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (update.effective_message.text or "").strip()
    if not msg:
        return

    if update.effective_chat and update.effective_chat.id != CHAT_ID:
        return

    if msg.lower().startswith("t:"):
        payload = msg[2:].lstrip()
        for ch in payload:
            keyboard.type(ch)
            time.sleep(0.01)
        await update.effective_message.reply_text("Getypt ✅")


async def on_startup(app: Application):
    # stuurt bericht zodra polling draait
    await app.bot.send_message(chat_id=CHAT_ID, text="Bot gestart 🚀")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("shot", cmd_shot))
    app.add_handler(CommandHandler("type", cmd_type))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_plain_text))

    print("Telegram remote draait ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
