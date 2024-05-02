import math
import iterm2
import asyncio

class OpenWorkTabs:
  SYNCER_READY_STR = "INFO: Ready!"

  class _Commands:
    def region(self):
      return self.REGION

  class _AUCommands(_Commands):
    REGION = "apac"

  class _EUCommands(_Commands):
    REGION = "eu"

  @classmethod
  def init_au(klass, app):
    return klass(app, klass._AUCommands())

  @classmethod
  def init_eu(klass, app):
    return klass(app, klass._EUCommands())

  def __init__(self, app, commands):
    self.app = app
    self.region = commands.region()

  async def execute(self):
    # _________
    # |       |
    # |       |
    # |       |
    # ---------
    current_tab = await self.__create_new_tab()
    main_session = current_tab.current_session

    # _________
    # |   |   |
    # |   |   |
    # |   |   |
    # ---------
    console_session = await self.__split_pane(main_session, vertical=True)

    # _________
    # |   |   |
    # |   |___|
    # |   |   |
    # ---------
    webpack_session = await self.__split_pane(console_session, vertical=False)

    # back to first pane so we can split off it
    await main_session.async_activate()

    # _________
    # |   |   |
    # |___|___|
    # |   |   |
    # ---------
    worker_session = await self.__split_pane(main_session, vertical=False)

    # _________
    # |   |   |
    # |___|___|
    # |___|   |
    # ---------
    tunnel_session = await self.__split_pane(worker_session, vertical=False)

    await asyncio.gather(
      self.__cdt(main_session),
      self.__cdt(console_session),
      self.__cdt(worker_session),
      self.__cdt(webpack_session),
      self.__cdt(tunnel_session),
    )

    # start tunnel
    await self.__run_dev_command(tunnel_session, "bin/tunnel")

    await self.divide_grid_height(tunnel_session, 2.0)
    await self.divide_grid_height(webpack_session, 5.0)
    await current_tab.async_update_layout()

    # wait for tunnel to finish syncing
    await self.__wait_for_text(tunnel_session, self.SYNCER_READY_STR)

    # run server and wait for bundle to finish before running the rest of the commands
    await self.__run_dev_command(main_session, "bin/dev server")
    await self.__wait_for_text(main_session, "Connection to", " closed")

    # run all other commands that depend on bundle
    await asyncio.gather(
      self.__run_dev_command(webpack_session, "bin/dev webpack"),
      self.__run_dev_command(worker_session, "bin/dev worker"),
      self.__run_dev_command(console_session, "bin/dev console"),
    )

  # This is janky AF and barely works
  async def divide_grid_height(self, session, amount):
    session_grid = session.grid_size
    # If we don't * 2 the width for some reason the width shrinks to about half
    new_grid_size = iterm2.util.Size(session_grid.width * 2, math.floor(session_grid.height / amount))
    session.preferred_size = new_grid_size

  async def __wait_for_text(self, session, text, second_text=None):
    if await self.__text_already_exists(session, text):
      if second_text:
        return self.__wait_for_text(session, second_text)
      else:
        return

    async with session.get_screen_streamer() as streamer:
      while True:
        screen_contents = await streamer.async_get()
        if screen_contents is None:
          continue

        max_lines = screen_contents.number_of_lines
        for i in range(max_lines - 1):
          if text in screen_contents.line(i).string:
            if second_text:
              return self.__wait_for_text(session, second_text)
            else:
              return

        if await self.__text_already_exists(session, text):
          if second_text:
            return self.__wait_for_text(session, second_text)
          else:
            return

  async def __text_already_exists(self, session, text):
    screen_contents = await session.async_get_screen_contents()
    max_lines = screen_contents.number_of_lines
    for i in range(max_lines - 1):
      if text in screen_contents.line(i).string:
        return True

    return False

  # async def __annotate_text(self, session, text_to_match, annotation_text):
  #   screen_contents = await session.async_get_screen_contents()
  #   cursor_point = screen_contents.cursor_coord
  #   from_ = iterm2.util.Point(cursor_point.x - len(text_to_match), cursor_point.y)
  #   to = iterm2.util.Point(cursor_point.x, cursor_point.y)
  #   point_range = iterm2.util.CoordRange(from_, to)
  #   await session.async_add_annotation(point_range, annotation_text)

  async def __create_new_tab(self):
    return await self.app.current_terminal_window.async_create_tab()

  async def __split_pane(self, session, vertical):
    return await session.async_split_pane(vertical=vertical)

  async def __run_command(self, session, command):
    await session.async_send_text(f'{command}\n')

  async def __run_dev_command(self, session, command):
    await self.__run_command(session, f'REGION={self.region} {command}')

  async def __cdt(self, session):
    await self.__run_command(session, "cdt")
