# run.py

import os
from acadstack_app import app

if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    # One process per deployment: sessions, active users, background job
    # state and the settings/policy caches all live in this process's
    # memory (see docs/architecture.md, "Deployment: one process").
    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('APP_PORT')}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
