import math
import iterm2
import subprocess

class OpenWorkTabs:
  SYNCER_READY_STR = "INFO: Ready!"
  LOGIN_MATCH_STR = "ruby@"

  class _Commands:
    def tunnel(self):
      return self.TUNNEL

  class _AUCommands(_Commands):
    TUNNEL = "REGION=apac bin/tunnel"

  class _EUCommands(_Commands):
    TUNNEL = "REGION=eu bin/tunnel"

  @classmethod
  def init_au(klass, app):
    return klass(app, klass._AUCommands())

  @classmethod
  def init_eu(klass, app):
    return klass(app, klass._EUCommands())

  def __init__(self, app, commands):
    self.app = app
    self.tunnel_command = commands.tunnel()

  async def execute(self):
    current_tab = await self.__create_new_tab()
    main_session = current_tab.current_session
    await self.__cdt(main_session)

    # split vertically for console pane
    console_session = await self.__split_pane(main_session, vertical=True)
    await self.__cdt(console_session)

    # split horizontally off console session for worker pane
    worker_session = await self.__split_pane(console_session, vertical=False)
    await self.__cdt(worker_session)

    # split horizontally off worker session for webpack pane
    webpack_session = await self.__split_pane(worker_session, vertical=False)
    await self.__cdt(webpack_session)

    # back to first pane
    await main_session.async_activate()

    # split horizontally from the left for tunnel pane
    tunnel_session = await self.__split_pane(main_session, vertical=False)
    await self.__cdt(tunnel_session)

    # Run tunnel and wait for docker auth and open in browser
    await self.__run_command(tunnel_session, self.tunnel_command)
    code = await self.__wait_for_and_get_code(tunnel_session)
    if code:
      url = f'https://device.sso.ap-southeast-2.amazonaws.com/?user_code={code}'
      subprocess.run(["open", url])

    # wait for tunnel to finish syncing
    await self.__wait_for_text(tunnel_session, self.SYNCER_READY_STR)

    # run bundle and wait for it to finish
    await self.__run_command(console_session, "bin/dev bundle")
    await self.__wait_for_text(console_session, "yarn install", "Done in")

    # run all other commands
    await self.__run_command(webpack_session, "bin/dev webpack")
    await self.__run_command(main_session, "bin/dev server")

    await self.__wait_for_text(console_session, "Connection to", " closed.")
    await self.__run_command(console_session, "bin/dev console")

    await self.__run_command(worker_session, "bin/dev worker")

    # sync_grid = tunnel_session.grid_size
    # # If we don't * 2 the width for some reason the width shrinks to about half
    # new_sync_size = iterm2.util.Size(sync_grid.width * 2, math.floor(sync_grid.height / 3.0))
    # tunnel_session.preferred_size = new_sync_size

    # await current_tab.async_update_layout()

    # await self.__ssh_and_wait_for((
    #   (main_session, "tanda-server"),
    #   (console_session, "tanda-console"),
    #   (worker_session, "tanda-worker")
    # ))

    # await self.__wait_for_syncer(tunnel_session)

    # # run commands
    # await self.__run_command(main_session, "\n")
    # await self.__run_command(console_session, "\n")
    # await self.__run_command(worker_session, "\n")

  async def __wait_for_and_get_code(self, session):
    text = "Then enter the code:"
    already_authed_text = "Bootstrapping remote setup"

    while True:
      screen_contents = await session.async_get_screen_contents()
      max_lines = screen_contents.number_of_lines

      for i in range(max_lines - 1):
        line_text = screen_contents.line(i).string

        if already_authed_text in line_text:
          return
        elif text in line_text:
          code_index = i + 2
          if code_index <= max_lines - 1:
            code = screen_contents.line(code_index).string
            if len(code) != 0:
              return code

  # async def __ssh_and_wait_for(self, sessions_with_commands):
  #   for session, command in sessions_with_commands:
  #     await self.__ssh(session)
  #     await self.__enter_command(session, command)

  #   for session, command in sessions_with_commands:
  #     await self.__wait_for_text(session, self.LOGIN_MATCH_STR)
  #     await self.__annotate_wait_for_syncer(session, command)

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

  async def __cdt(self, session):
    await self.__run_command(session, "cdt")
