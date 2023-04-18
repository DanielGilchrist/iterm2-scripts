class OpenWorkTabs:
  AU = "au"
  EU = "eu"

  @classmethod
  def init_au(klass, app):
    return klass(app, klass.AU)

  @classmethod
  def init_eu(klass, app):
    return klass(app, klass.EU)

  def __init__(self, app, type):
    self.app = app
    self.type = type

  async def execute(self):
    main_pane = await self.__create_new_tab()
    main_session = main_pane.current_session
    await self.__run_command(main_session, self.__ssh_command())

    clockin_session = await self.__split_pane(main_session, True)
    await self.__run_command(clockin_session, "tanda_cli clockin start")

    sync_session = await self.__split_pane(clockin_session, False)
    await self.__run_command(sync_session, self.__sync_command())

    await main_session.async_activate()
    await self.__run_command(main_session, "tanda-server")

  async def __create_new_tab(self):
    return await self.app.current_terminal_window.async_create_tab()

  async def __split_pane(self, session, vertical):
    return await session.async_split_pane(vertical=vertical)

  async def __run_command(self, session, command):
    return await session.async_send_text(f'{command}\n')

  def __ssh_command(self):
    if self.type == self.EU:
      return 'eutssh'
    elif self.type == self.AU:
      return 'tssh'
    else:
      raise Exception('Invalid type')

  def __sync_command(self):
    if self.type == self.EU:
      return 'eutsr'
    elif self.type == self.AU:
      return 'tsr'
    else:
      raise Exception('Invalid type')
