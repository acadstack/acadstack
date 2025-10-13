# run.py

import os
from app.api import app

if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('FREC_PORT')}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
