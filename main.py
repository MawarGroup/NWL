
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = "7867931574:AAH1xHAe8gChvRvRsZrT8no4Oxo4FwMjg4Y"
CHECK_INTERVAL_SECONDS = 60

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_nawala_status(domain: str) -> str:
    url = "https://cekipost.net/"
    payload = {'domain': domain}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        print(f"Memeriksa {domain}")
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        result_container = soup.find('div', class_='alert')
        if result_container and result_container.find('b'):
            return result_container.find('b').get_text(strip=True)
        elif "Domain yang anda masukkan salah" in response.text:
            return "Domain tidak valid"
        else:
            return "Gagal parsing hasil"
    except Exception as e:
        return f"ERROR saat cek {domain}: {e}"

async def periodic_checker(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    domains = context.bot_data.get('domains', [])

    if not domains:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Tidak ada domain untuk dicek.")
        return

    await context.bot.send_message(chat_id=chat_id, text="🔄 Mulai pengecekan domain...")

    report_lines = [
        f"🧾 <b>Laporan Status Nawala</b>",
        f"🕓 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "===================="
    ]

    try:
        tasks = [asyncio.to_thread(get_nawala_status, domain) for domain in domains]
        results = await asyncio.gather(*tasks)

        for domain, status in zip(domains, results):
            emoji = "✅" if "aman" in status.lower() else "❌"
            report_lines.append(f"{emoji} <code>{domain}</code>: <b>{status}</b>")

        full_report = "\n".join(report_lines)

        await context.bot.send_message(chat_id=chat_id, text=full_report, parse_mode='HTML')

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error saat pengecekan: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirimkan file .txt berisi daftar domain. "
        "Saya akan memantau status Nawala domain itu setiap 60 detik.

"
        "Gunakan /stop untuk menghentikan."
    )

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    context.bot_data.pop('domains', None)
    await update.message.reply_text("⛔ Pemantauan dihentikan.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    chat_id = update.message.chat_id

    if not document.file_name.lower().endswith('.txt'):
        await update.message.reply_text("❌ Harap kirim file .txt.")
        return

    try:
        txt_file = await document.get_file()
        content_bytes = await txt_file.download_as_bytearray()
        content = content_bytes.decode('utf-8')
        domains = [line.strip() for line in content.splitlines() if line.strip()]

        if not domains:
            await update.message.reply_text("⚠️ File kosong atau tidak valid.")
            return

        context.bot_data['domains'] = domains
        context.job_queue.run_repeating(
            callback=periodic_checker,
            interval=CHECK_INTERVAL_SECONDS,
            chat_id=chat_id,
            name=str(chat_id)
        )

        await update.message.reply_text(
            f"✅ Mulai memantau {len(domains)} domain.
Saya akan kirim laporan tiap {CHECK_INTERVAL_SECONDS} detik.
Gunakan /stop untuk berhenti."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error saat memproses file: {e}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_monitoring))
    application.add_handler(MessageHandler(filters.Document.TXT, handle_document))
    print("✅ Bot debug sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
