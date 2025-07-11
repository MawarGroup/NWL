import logging
import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Gunakan token kamu langsung (jika tidak pakai env)
TELEGRAM_BOT_TOKEN = "7867931574:AAH1xHAe8gChvRvRsZrT8no4Oxo4FwMjg4Y"

# Waktu jeda antar pengecekan (dalam detik)
CHECK_INTERVAL_SECONDS = 60

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fungsi pengecekan domain
def get_nawala_status(domain: str) -> str:
    url = "https://cekipost.net/"
    payload = {'domain': domain}
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
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
    except requests.exceptions.Timeout:
        return "Timeout"
    except requests.exceptions.RequestException:
        return "Error Koneksi"
    except Exception:
        return "Error Tak Terduga"

# Fungsi periodic checker
async def periodic_checker(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    domains = context.bot_data.get('domains', [])
    if not domains:
        return

    report_lines = [
        f"🧾 <b>Laporan Status Nawala</b>",
        f"🕓 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "===================="
    ]
    tasks = [asyncio.to_thread(get_nawala_status, domain) for domain in domains]
    results = await asyncio.gather(*tasks)

    for domain, status in zip(domains, results):
        emoji = "✅" if "aman" in status.lower() else "❌"
        report_lines.append(f"{emoji} <code>{domain}</code>: <b>{status}</b>")

    full_report = "\n".join(report_lines)
    await context.bot.send_message(chat_id=chat_id, text=full_report, parse_mode='HTML')

# Handler /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirimkan file .txt yang berisi daftar domain (satu per baris). Saya akan memantau status Nawala dari domain tersebut.\n\nGunakan /stop untuk menghentikan."
    )

# Handler /stop
async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    context.bot_data.pop('domains', None)
    await update.message.reply_text("Pemantauan dihentikan.")

# Handler file .txt
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    chat_id = update.message.chat_id

    if not document.file_name.lower().endswith('.txt'):
        await update.message.reply_text("❌ Harap kirim file .txt yang valid.")
        return

    txt_file = await document.get_file()
    content_bytes = await txt_file.download_as_bytearray()
    content = content_bytes.decode('utf-8')
    domains = [line.strip() for line in content.splitlines() if line.strip()]

    if not domains:
        await update.message.reply_text("File kosong atau tidak berisi domain.")
        return

    context.bot_data['domains'] = domains
    context.job_queue.run_repeating(periodic_checker, interval=CHECK_INTERVAL_SECONDS, chat_id=chat_id, name=str(chat_id))

    await update.message.reply_text(
        f"✅ Saya akan mulai memantau {len(domains)} domain.\nGunakan /stop untuk menghentikan."
    )

# Fungsi utama
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_monitoring))
    application.add_handler(MessageHandler(filters.Document.TXT, handle_document))
    print("✅ Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
