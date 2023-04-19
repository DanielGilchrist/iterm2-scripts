class OpenWorkTabs:
  class Commands:
    def ssh(self):
      return self.SSH

    def sync(self):
      return self.SYNC

  class AUCommands(Commands):
    SSH = "tssh"
    SYNC = "tsr"

  class EUCommands(Commands):
    SSH = "eutssh"
    SYNC = "eutsr"

  @classmethod
  def init_au(klass, app):
    return klass(app, klass.AUCommands())

  @classmethod
  def init_eu(klass, app):
    return klass(app, klass.EUCommands())

  def __init__(self, app, commands):
    self.app = app
    self.ssh_command = commands.ssh()
    self.sync_command = commands.sync()

  async def execute(self):
    main_pane = await self.__create_new_tab()
    main_session = main_pane.current_session
    await self.__run_command(main_session, self.ssh_command)

    repo_session = await self.__split_pane(main_session, True)
    await self.__run_command(repo_session, "cdt")

    sync_session = await self.__split_pane(repo_session, False)
    await self.__run_command(sync_session, self.sync_command)

    await main_session.async_activate()
    await self.__run_command(main_session, "tanda-server")

  async def __create_new_tab(self):
    return await self.app.current_terminal_window.async_create_tab()

  async def __split_pane(self, session, vertical):
    return await session.async_split_pane(vertical=vertical)

  async def __run_command(self, session, command):
    return await session.async_send_text(f'{command}\n')
