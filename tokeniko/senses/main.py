# senses: this is the I/O of tokeniko
# - discord connector, to process messages and send messages
# - atproto connector, to process trusted sources and be aware of the events happening in the world

import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv
from lib.core.io import init_io
from lib.llc.decompiler import decompiler_init
from senses.outbound import outbound_executor_task

load_dotenv()

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tokeniko-brain")

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
    logger.info("🚀 Init tokeniko: senses")
    
    # 1. Init — senses needs Mongo (the action queue) + Ollama (the decompiler, raw -> fluent English).
    #    No spaCy/Stanza pipeline: the brain compiled the input; senses only DECOMPILES the reply.
    db, db_memory, ai_client = init_io()
    await decompiler_init(ai_client)

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
            atproto_task = tg.create_task(atproto_listener_task())
            discord_task = tg.create_task(discord_bot_task())
            # D3b: the outbound actions executor — carries the brain's decisions to Discord (dry-run
            # by default; sender=None until a live DiscordClient is connected with the inbound listener).
            outbound_task = tg.create_task(outbound_executor_task())

            # Waiting for sigterms
            await stop_event.wait()

            # Gently shutdown
            logger.info("Shutting down sub threads...")
            atproto_task.cancel()
            discord_task.cancel()
            outbound_task.cancel()
            
    except* Exception as eg:
        logger.error(f"❌ Critical error: {eg}")
    finally:
        logger.info("🛑 tokeniko: senses are deep sleeping")

if __name__ == "__main__":
    # main start
    asyncio.run(main())