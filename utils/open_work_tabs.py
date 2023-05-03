import math
import iterm2

class OpenWorkTabs:
  SYNCER_READY_STR = "INFO: Ready!"
  LOGIN_MATCH_STR = "ruby@"

  class _Commands:
    def ssh(self):
      return self.SSH

    def sync(self):
      return self.SYNC

    def db_type(self):
      return self.EXPORT_TYPE

  class _AUCommands(_Commands):
    SSH = "tssh"
    SYNC = "tsr"
    EXPORT_TYPE = "apac"

  class _EUCommands(_Commands):
    SSH = "eutssh"
    SYNC = "eutsr"
    EXPORT_TYPE = "eu"

  @classmethod
  def init_au(klass, app):
    return klass(app, klass._AUCommands())

  @classmethod
  def init_eu(klass, app):
    return klass(app, klass._EUCommands())

  def __init__(self, app, commands):
    self.app = app
    self.ssh_command = commands.ssh()
    self.sync_command = commands.sync()
    self.export_db_command = f'export DB_CREDS_TYPE={commands.db_type()}'

  async def execute(self):
    current_tab = await self.__create_new_tab()
    main_session = current_tab.current_session

    # split vertically for console pane
    console_session = await self.__split_pane(main_session, vertical=True)

    # split horizontally for sync pane
    sync_session = await self.__split_pane(console_session, vertical=False)
    await self.__run_command(sync_session, self.sync_command)
    sync_grid = sync_session.grid_size
    # If we don't * 2 the width for some reason the width shrinks to about half
    new_sync_size = iterm2.util.Size(sync_grid.width * 2, math.floor(sync_grid.height / 3.0))
    sync_session.preferred_size = new_sync_size

    # back to first pane
    await main_session.async_activate()
    # split horizontally for worker pane
    worker_session = await self.__split_pane(main_session, vertical=False)

    # back to first pane
    await main_session.async_activate()

    await current_tab.async_update_layout()

    await self.__ssh_and_wait_for((
      (main_session, "tanda-server"),
      (console_session, "tanda-console"),
      (worker_session, "tanda-worker")
    ))

    await self.__wait_for_syncer(sync_session)

    # run commands
    await self.__run_command(main_session, "\n")
    await self.__run_command(console_session, "\n")
    await self.__run_command(worker_session, "\n")

  async def __ssh_and_wait_for(self, sessions_with_commands):
    for session, command in sessions_with_commands:
      await self.__ssh(session)
      await self.__enter_command(session, command)

    for session, command in sessions_with_commands:
      await self.__wait_for_text(session, self.LOGIN_MATCH_STR)
      await self.__annotate_wait_for_syncer(session, command)

  async def __wait_for_text(self, session, text):
    if await self.__text_already_exists(session, text):
      return

    async with session.get_screen_streamer() as streamer:
      while True:
        screen_contents = await streamer.async_get()
        if screen_contents is None:
          continue

        max_lines = screen_contents.number_of_lines
        for i in range(max_lines - 1):
          if text in screen_contents.line(i).string:
            return

        if await self.__text_already_exists(session, text):
          return

  async def __text_already_exists(self, session, text):
    screen_contents = await session.async_get_screen_contents()
    max_lines = screen_contents.number_of_lines
    for i in range(max_lines - 1):
      if text in screen_contents.line(i).string:
        return True

    return False

  async def __wait_for_syncer(self, session):
    await self.__wait_for_text(session, self.SYNCER_READY_STR)

  async def __annotate_wait_for_syncer(self, session, text_to_match):
    screen_contents = await session.async_get_screen_contents()
    cursor_point = screen_contents.cursor_coord
    from_ = iterm2.util.Point(cursor_point.x - len(text_to_match), cursor_point.y)
    to = iterm2.util.Point(cursor_point.x, cursor_point.y)
    point_range = iterm2.util.CoordRange(from_, to)
    await session.async_add_annotation(point_range, "Waiting on syncer before running commands...")

  async def __create_new_tab(self):
    return await self.app.current_terminal_window.async_create_tab()

  async def __split_pane(self, session, vertical):
    return await session.async_split_pane(vertical=vertical)

  async def __run_command(self, session, command):
    await session.async_send_text(f'{command}\n')

  async def __enter_command(self, session, command):
    await session.async_send_text(command)

  async def __export_db_type(self, session):
    await self.__run_command(session, self.export_db_command)

  async def __export_disable_spring(self, session):
    await self.__run_command(session, "export DISABLE_SPRING=true")

  async def __ssh(self, session):
    await self.__run_command(session, self.ssh_command)
    await self.__export_disable_spring(session)
    await self.__export_db_type(session)
