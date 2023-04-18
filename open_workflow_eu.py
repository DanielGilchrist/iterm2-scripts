#!/usr/bin/env python3

import iterm2
from utils.open_work_tabs import OpenWorkTabs

async def main(connection):
  app = await iterm2.async_get_app(connection)
  await OpenWorkTabs.init_eu(app).execute()

iterm2.run_until_complete(main)
