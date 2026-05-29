import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv
from lib.core.io import init_io

load_dotenv()

# Configurazione del logging per vedere cosa succede in console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tokeniko-brain")

# main brain loop
async def idle_thinking_loop():
    logger.info("🧠 Brain loop started")
    try:
        while True:
            logger.info("🤖 tokeniko is thinking...")
            
            await asyncio.sleep(30) 
    except asyncio.CancelledError:
        logger.info("🧠 Brain loop interrupted...")

# atproto listenere
async def atproto_listener_task():

    logger.info("🦋 ATProto Listener (Jetstream) started")
    try:
        while True:

            await asyncio.sleep(5)  # Simulazione attesa dati
    except asyncio.CancelledError:
        logger.info("🦋 LATProto Listener interrupted...")

# discord bot
async def discord_bot_task():
    logger.info("💬 Discord interface started")
    try:
        while True:
            # Qui si aggancerebbe il client di Discord (es. discord.py)
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logger.info("💬 Discord interface interrupted...")

# main / init
async def main():
    logger.info("🚀 Init tokeniko")
    
    # 1. Init
    db, db_memory, ai_client = init_io()
    
    # 2. Graceful Shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def shutdown_handler():
        logger.warning("⚠️ SIGTERM. Time to go to deep sleep...")
        stop_event.set()

    # Listen for termination signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    # 3. Tasks launcher
    try:
        async with asyncio.TaskGroup() as tg:
            # Creiamo i processi paralleli che gireranno contemporaneamente
            thinking_task = tg.create_task(idle_thinking_loop())
            atproto_task = tg.create_task(atproto_listener_task())
            discord_task = tg.create_task(discord_bot_task())
            
            # Waiting for sigterms
            await stop_event.wait()
            
            # Gently shutdown
            logger.info("Shutting down sub threads...")
            thinking_task.cancel()
            atproto_task.cancel()
            discord_task.cancel()
            
    except* Exception as eg:
        logger.error(f"❌ Critical error: {eg}")
    finally:
        logger.info("🛑 tokeniko is deep sleeping. See ya'll")

if __name__ == "__main__":
    # main start
    asyncio.run(main())