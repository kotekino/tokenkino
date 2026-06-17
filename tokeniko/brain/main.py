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

# main brain loop: here tokeniko cycle over his memory, searching for new knowledge (elaborating theorems), validating existing knowledge (inconsistencies over axioms)
# and creating ideas
async def idle_thinking_loop():
    logger.info("🧠 Brain loop started")
    try:
        while True:
            logger.info("🤖 tokeniko is thinking...")
            
            await asyncio.sleep(30) 
    except asyncio.CancelledError:
        logger.info("🧠 Brain loop interrupted...")

# priority evaluation loop
async def priorities_loop():
    logger.info("🧠 Priorities loop started")
    try:
        while True:
            logger.info("🤖 tokeniko is taking decisions...")
            
            await asyncio.sleep(30) 
    except asyncio.CancelledError:
        logger.info("🧠 Priorities loop interrupted...")

# action loop
async def actions_loop():
    logger.info("🧠 Action loop started")
    try:
        while True:
            logger.info("🤖 tokeniko is executing his wills...")
            
            await asyncio.sleep(30) 
    except asyncio.CancelledError:
        logger.info("🧠 Action loop interrupted...")


# main / init
async def main():
    logger.info("🚀 Init tokeniko: brain")
    
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
            # parallel tasks (so far, one task)
            thinking_task = tg.create_task(idle_thinking_loop())
            prio_task = tg.create_task(priorities_loop())
            actions_task = tg.create_task(actions_loop())
            
            # Waiting for sigterms
            await stop_event.wait()
            
            # Gently shutdown
            logger.info("Shutting down sub threads...")
            thinking_task.cancel()
            prio_task.cancel()
            actions_task.cancel()

            
    except* Exception as eg:
        logger.error(f"❌ Critical error: {eg}")
    finally:
        logger.info("🛑 tokeniko is deep sleeping. See ya'll")

if __name__ == "__main__":
    # main start
    asyncio.run(main())