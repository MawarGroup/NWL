import asyncio
import json
import os
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from flask import Flask
import threading

# --- Config ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.WARNING)

API_ID = 22903537
API_HASH = 'db3a26e7eef0470c61419a6f1b3a58c5'
PHONE_NUMBER = '+62 817 70546513'
SESSION_NAME = 'userbot_broadcast_session'
DATA_FILE = 'bot_data.json'

# --- Data ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"caption": "", "groups": [], "is_active": False, "media_message_id": None, "buttons": [], "forward_link": None}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"caption": "", "groups": [], "is_active": False, "media_message_id": None, "buttons": [], "forward_link": None}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

bot_data = load_data()
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# --- Flask uptime ---
app = Flask(__name__)
@app.route('/')
def index(): return "✅ Bot aktif 24 jam"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080)), daemon=True).start()

# --- Command ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^/on$'))
async def on_broadcast(event):
    if not bot_data['is_active']:
        bot_data['is_active'] = True
        save_data(bot_data)
        await event.respond("🚀 Broadcast dimulai.")
        asyncio.create_task(broadcast_loop())
    else:
        await event.respond("⚠️ Broadcast sudah aktif.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/off$'))
async def off_broadcast(event):
    bot_data['is_active'] = False
    save_data(bot_data)
    await event.respond("⛔ Broadcast dihentikan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/addgroup(?:\s+(@\w+))+'))
async def add_group(event):
    groups = event.raw_text.split()[1:]
    added = []
    for group in groups:
        group = group.lower()
        if group not in bot_data['groups']:
            bot_data['groups'].append(group)
            added.append(group)
    save_data(bot_data)
    if added:
        await event.respond(f"✅ Grup ditambahkan: {', '.join(added)}")
    else:
        await event.respond("⚠️ Tidak ada grup baru yang ditambahkan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/delgroup (@\w+)$'))
async def del_group(event):
    group = event.pattern_match.group(1).lower()
    if group in bot_data['groups']:
        bot_data['groups'].remove(group)
        save_data(bot_data)
        await event.respond(f"🗑️ Grup {group} dihapus.")
    else:
        await event.respond(f"⚠️ Grup {group} tidak ditemukan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/listgroup$'))
async def list_group(event):
    if not bot_data['groups']:
        await event.respond("📭 Belum ada grup yang terdaftar.")
    else:
        await event.respond("📌 Grup terdaftar:\n" + "\n".join(bot_data['groups']))

@client.on(events.NewMessage(outgoing=True, pattern=r'^/setcaption$'))
async def set_caption(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.respond("⚠️ Balas perintah ini ke pesan berisi caption.")
        return
    bot_data['caption'] = reply.text
    bot_data['forward_link'] = None
    save_data(bot_data)
    await event.respond("✅ Caption disimpan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/setbutton$'))
async def set_button(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.respond("⚠️ Balas perintah ini ke pesan tombol format Text|URL||Text2|URL2.")
        return
    raw_buttons = reply.text
    new_buttons = []
    lines = raw_buttons.split("||")
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) == 2:
            text, url = parts
            new_buttons.append([Button.url(text.strip(), url.strip())])
        else:
            await event.respond("⚠️ Format salah. Gunakan: Text|URL||Text2|URL2")
            return
    bot_data['buttons'] = new_buttons
    save_data(bot_data)
    await event.respond("✅ Tombol disimpan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/setmedia$'))
async def set_media(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.respond("⚠️ Balas perintah ini ke pesan media.")
        return
    if isinstance(reply.media, (MessageMediaPhoto, MessageMediaDocument)):
        bot_data['media_message_id'] = reply.id
        bot_data['forward_link'] = None
        save_data(bot_data)
        await event.respond("✅ Media disimpan.")
    else:
        await event.respond("⚠️ Hanya gambar atau video yang didukung.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/forward (https://t\.me/\S+/\d+)$'))
async def set_forward(event):
    bot_data['forward_link'] = event.pattern_match.group(1)
    bot_data['media_message_id'] = None
    bot_data['caption'] = ""
    bot_data['buttons'] = []
    save_data(bot_data)
    await event.respond("✅ Mode forward diaktifkan.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/status$'))
async def status_command(event):
    status = "AKTIF ✅" if bot_data['is_active'] else "NONAKTIF ❌"
    mode = "FORWARD 🔁" if bot_data['forward_link'] else "MEDIA/CAPTION 📝"
    text = f"📡 Status: {status}\n🎯 Grup: {len(bot_data['groups'])}\n📝 Mode: {mode}"
    await event.respond(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^/help$'))
async def help_command(event):
    help_text = (
        "<b>📘 Panduan Bot Broadcast Telegram</b>\n\n"
        "<b>🔹 Utama:</b>\n"
        "<code>/on</code> - Mulai broadcast\n"
        "<code>/off</code> - Stop broadcast\n"
        "<code>/status</code>\n"
        "<code>/help</code>\n\n"
        "<b>🔹 Grup:</b>\n"
        "<code>/addgroup @g1 @g2</code>\n"
        "<code>/delgroup @g1</code>\n"
        "<code>/listgroup</code>\n\n"
        "<b>🔹 Konten:</b>\n"
        "<code>/setcaption</code> (balas caption panjang)\n"
        "<code>/setmedia</code> (balas media)\n"
        "<code>/setbutton</code> (balas tombol Text|URL||Text2|URL2)\n"
        "<code>/forward https://t.me/.../123</code>"
    )
    await event.respond(help_text, parse_mode='html')

# --- Broadcast Loop ---
async def broadcast_loop():
    while bot_data['is_active']:
        for group in bot_data['groups']:
            if not bot_data['is_active']:
                break
            try:
                if bot_data['forward_link']:
                    parts = bot_data['forward_link'].split('/')
                    msg = await client.get_messages(parts[-2], ids=int(parts[-1]))
                    if msg:
                        await client.forward_messages(group, msg)
                        await client.send_message("me", f"✅ Forward ke {group} sukses.")
                elif bot_data['media_message_id']:
                    msg = await client.get_messages("me", ids=bot_data['media_message_id'])
                    if msg and msg.media:
                        await client.send_file(group, msg.media, caption=bot_data['caption'], buttons=bot_data['buttons'])
                        await client.send_message("me", f"✅ Media ke {group} sukses.")
                elif bot_data['caption']:
                    await client.send_message(group, bot_data['caption'], buttons=bot_data['buttons'])
                    await client.send_message("me", f"✅ Teks ke {group} sukses.")
                else:
                    await client.send_message("me", f"⚠️ Tidak ada konten untuk {group}.")
            except Exception as e:
                await client.send_message("me", f"❌ Gagal kirim ke {group}: {e}")
            await asyncio.sleep(300)  # Jeda 5 menit per grup
        if bot_data['is_active']:
            await asyncio.sleep(1800)  # Jeda 30 menit antar putaran

# --- Main ---
async def main():
    await client.start(phone=PHONE_NUMBER)
    if bot_data['is_active']:
        asyncio.create_task(broadcast_loop())
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Error: {e}")
