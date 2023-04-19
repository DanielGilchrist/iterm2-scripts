class OpenWorkTabs:
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
    main_pane = await self.__create_new_tab()
    main_session = main_pane.current_session
    await self.__run_command(main_session, self.ssh_command)

    repo_session = await self.__split_pane(main_session, True)
    await self.__run_command(repo_session, "cdt")

    sync_session = await self.__split_pane(repo_session, False)
    await self.__run_command(sync_session, self.sync_command)

    await main_session.async_activate()
    await self.__run_command(main_session, self.export_db_command)

    # Enter command but do not run - this allows time for syncer to finish
    await self.__enter_command(main_session, "tanda-server")

  async def __create_new_tab(self):
    return await self.app.current_terminal_window.async_create_tab()

  async def __split_pane(self, session, vertical):
    return await session.async_split_pane(vertical=vertical)

  async def __run_command(self, session, command):
    return await session.async_send_text(f'{command}\n')

  async def __enter_command(self, session, command):
    return await session.async_send_text(command)
