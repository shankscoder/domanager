import sys, os, subprocess, gc
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from sys import platform

from domanager.config import config
from domanager.resources import rPath
from domanager.core import DOHandler, UpdateThread
from domanager.ui.PreferencesDialog import PreferencesDialog
from domanager.ui.AboutDialog import AboutDialog
from domanager.ui.RenameDialog import RenameDialog
from domanager.ui.UpdateChecker import UpdateChecker
from domanager.ui.CustomMenu import CustomMenu

class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, mWindow):
        super(TrayIcon, self).__init__(mWindow)
        self.setIcon(self._icon(config.mainIcon))
        self.setVisible(True)

        self._mainWindow = mWindow
        self._mainWindow.setWindowIcon(self._icon("main_logo_color.png"))

        self._doHandler = DOHandler()
        self._updateChecker = UpdateChecker(self._mainWindow)
        self._updateChecker.quitProgram.connect(self._quit)

        self._data = []
        self._dInfos = []
        self._menu = None

        self._quitAction = QtWidgets.QAction("Quit", self)
        self._quitAction.setIcon(self._icon("quit.png"))
        self._quitAction.triggered.connect(self._quit)

        self._aboutAction = QtWidgets.QAction("About", self)
        self._aboutAction.setIcon(self._icon("about.png"))
        self._aboutAction.triggered.connect(self._about)

        self._settingsAction = QtWidgets.QAction("Preferences", self)
        self._settingsAction.setIcon(self._icon("settings.png"))
        self._settingsAction.triggered.connect(self._settings)

        self._createAction = QtWidgets.QAction("Create droplet (web)", self)
        self._createAction.setIcon(self._icon("create.png"))
        self._createAction.triggered.connect(self._createDroplet)

        self._bugAction = QtWidgets.QAction("Report bug/request", self)
        self._bugAction.setIcon(self._icon("bug.png"))
        self._bugAction.triggered.connect(self._report)

        self._updateAction = QtWidgets.QAction("Check for update", self)
        self._updateAction.setIcon(self._icon("update.png"))
        self._updateAction.triggered.connect(self.update)

        self._helpMenu = QtWidgets.QMenu(self._mainWindow)
        self._helpMenu.addAction(self._updateAction)
        self._helpMenu.addAction(self._bugAction)
        self._helpMenu.addAction(self._aboutAction)

        self._helpAction = QtWidgets.QAction("Help", self)
        self._helpAction.setIcon(self._icon("help.png"))
        self._helpAction.setMenu(self._helpMenu)

        self._updateThread = UpdateThread(self)
        self._updateThread.updated.connect(self._updateData)
        self._updateThread.start()

        clientId = config.value('clientId', "")
        apiKey = config.value('apiKey', "")

        self.activated.connect(self._popupMenu)

        if not clientId or not apiKey:
            self._settings()

        self._updateMenu()

    def _icon(self, filename):
        return QtGui.QIcon(rPath(filename))

    def _dropletMenu(self, idx):
        dropletMenu = QtWidgets.QMenu(self._mainWindow)

        copyIPAction = QtWidgets.QAction("Copy IP to clipboard", self._menu)
        copyIPAction.setIcon(self._icon("ip.png"))
        copyIPAction.triggered.connect(lambda y, x=idx: self._ipToClipboard(x))

        resetRootAction = QtWidgets.QAction("Reset root password", self._menu)
        resetRootAction.setIcon(self._icon("password.png"))
        resetRootAction.triggered.connect(lambda y, x=idx: self._resetRoot(x))

        renameDropletAction = QtWidgets.QAction("Rename", self._menu)
        renameDropletAction.setIcon(self._icon("rename.png"))
        renameDropletAction.triggered.connect(lambda y, x=idx: self._renameDroplet(x))

        destroyDropletAction = QtWidgets.QAction("Destroy", self._menu)
        destroyDropletAction.setIcon(self._icon("destroy.png"))
        destroyDropletAction.triggered.connect(lambda y, x=idx: self._destroyDroplet(x))

        dropletMenu.addAction(copyIPAction)

        if self._dInfos[idx]['status'] == 'active':

            sshAction = QtWidgets.QAction("Open SSH connection", self._menu)
            sshAction.setIcon(self._icon("ssh.png"))
            sshAction.triggered.connect(lambda y, x=idx: self._openSSH(x))

            rebootAction = QtWidgets.QAction("Power cycle", self._menu)
            rebootAction.setIcon(self._icon("reboot.png"))
            rebootAction.triggered.connect(lambda y, x=idx: self._powerCycle(x))

            shutDownAction = QtWidgets.QAction("Power Off", self._menu)
            shutDownAction.setIcon(self._icon("shutdown.png"))
            shutDownAction.triggered.connect(lambda y, x=idx: self._powerOff(x))

            dropletMenu.addAction(sshAction)
            dropletMenu.addSeparator()
            dropletMenu.addAction(renameDropletAction)
            dropletMenu.addAction(resetRootAction)
            dropletMenu.addAction(rebootAction)
            dropletMenu.addAction(shutDownAction)

        else:
            startAction = QtWidgets.QAction("Power On", self._menu)
            startAction.setIcon(self._icon("start.png"))
            startAction.triggered.connect(lambda y, x=idx: self._powerOn(x))

            dropletMenu.addSeparator()
            dropletMenu.addAction(renameDropletAction)
            dropletMenu.addAction(resetRootAction)
            dropletMenu.addAction(startAction)

        dropletMenu.addSeparator()
        dropletMenu.addAction(destroyDropletAction)

        return dropletMenu

    def _checkResult(self, commandName, dropletName, result):
        if result['status'] != "OK":
            if 'message' in result:
                if 'pending' in result['message']:
                    msg = "%s is in pending stage. Please try again later" % dropletName
                else:
                    msg = result['message']
                self._message(msg)

    def _renameDroplet(self, idx):
        dropletName = self._dInfos[idx]['name']
        dropletId = self._dInfos[idx]['id']
        rd = RenameDialog(dropletName, self._mainWindow)
        rd.showNormal()
        rd.activateWindow()
        rd.exec_()
        if rd.result:
            result = self._doHandler.rename(dropletId, rd.result)
            self._checkResult("Rename", dropletName, result)

    def _resetRoot(self, idx):
        dropletName = self._dInfos[idx]['name']
        action = "reboot" if self._dInfos[idx]['status'] == 'active' else "power on"
        result = self._question("Reset root password command will %s the %s. Proceed?" % (action, dropletName))
        if result:
            dropletId = self._dInfos[idx]['id']
            result = self._doHandler.resetRoot(dropletId)
            self._checkResult("Reset root", dropletName, result)

    def _openSSH(self, idx):
        userName = config.value('userName', "root")
        ipAddress = self._dInfos[idx]['ip_address']
        sshPort = config.value('sshPort', 22)
        command = config.sshCommand
        if platform == "win32":
            command = command % (userName, ipAddress, sshPort)
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(command.split(' '), creationflags=DETACHED_PROCESS)
        else:
            command = command % (sshPort, userName, ipAddress)
            os.system(command)

    def _powerOn(self, idx):
        dropletName = self._dInfos[idx]['name']
        dropletId = self._dInfos[idx]['id']
        result = self._doHandler.powerOn(dropletId)
        self._checkResult("Power on", dropletName, result)

    def _powerCycle(self, idx):
        dropletName = self._dInfos[idx]['name']
        result = self._question("Are you sure that you want to power cycle the %s?" % dropletName)
        if result:
            dropletId = self._dInfos[idx]['id']
            result = self._doHandler.powerCycle(dropletId)
            self._checkResult("Power cycle", dropletName, result)

    def _destroyDroplet(self, idx):
        dropletName = self._dInfos[idx]['name']
        result = self._question("Are you sure that you want to DESTROY the %s? This command is irreversible!" % dropletName)
        if result:
            dropletName = self._dInfos[idx]['name']
            dropletId = self._dInfos[idx]['id']
            result = self._doHandler.destroy(dropletId)
            self._checkResult("Destroy", dropletName, result)

    def _powerOff(self, idx):
        dropletName = self._dInfos[idx]['name']
        result = self._question("Are you sure that you want to power off the %s?" % dropletName)
        if result:
            dropletName = self._dInfos[idx]['name']
            dropletId = self._dInfos[idx]['id']
            result = self._doHandler.powerOff(dropletId)
            self._checkResult("Power off", dropletName, result)

    def _updateData(self, result):
        if self._data != result:
            self._dInfos = []
            self._data = result
            if self._data and 'droplets' in self._data:
                self._dInfos = self._data['droplets']
            self._updateMenu()
        gc.collect()

    def _updateMenu(self):
        menuVisible = False
        if self._menu:
            self._menu.removeAction(self._createAction)
            self._menu.removeAction(self._settingsAction)
            self._menu.removeAction(self._quitAction)
            self._menu.removeAction(self._aboutAction)
            self._menu.removeAction(self._updateAction)
            self._menu.removeAction(self._helpAction)
            menuVisible = self._menu.isVisible()
            self._menu.hide()
            self._menu.setParent(None)
            self._menu.deleteLater()

        self._menu = CustomMenu()

        if not self._data:
            infoMsg = "Connecting..."
            self.setIcon(self._icon("main_logo_gray_error.png"))
        elif "OK" in self._data['status']:
            infoMsg = "Connected"
            self.setIcon(self._icon(config.mainIcon))
        elif "ERROR" in self._data['status']:
            infoMsg = self._data['message']
            self.setIcon(self._icon("main_logo_gray_error.png"))
        else:
            infoMsg = self._data['status']
            self.setIcon(self._icon("main_logo_gray_error.png"))

        infoAction = QtWidgets.QAction("  Status: %s" % infoMsg, self._menu)
        infoAction.setEnabled(False)

        self._menu.addAction(infoAction)
        self._menu.addSeparator()

        if len(self._dInfos) > 0:
            for idx, dInfo in enumerate(self._dInfos):
                dropletAction = QtWidgets.QAction(dInfo['name'], self._menu)

                if dInfo['status'] == 'active':
                    if dInfo['locked']:
                        dropletAction.setIcon(self._icon("locked.png"))
                        dropletAction.setToolTip("Locked (operation in progress)")
                    else:
                        dropletAction.setIcon(self._icon("active.png"))
                        dropletAction.setToolTip("Running")
                else:
                    dropletAction.setIcon(self._icon("inactive.png"))
                    dropletAction.setToolTip("Stopped")

                if not dInfo['locked']:
                    dropletAction.setMenu(self._dropletMenu(idx))

                self._menu.addAction(dropletAction)

            self._menu.addSeparator()

        self._menu.addAction(self._createAction)
        self._menu.addSeparator()
        self._menu.addAction(self._settingsAction)
        self._menu.addAction(self._helpAction)
        self._menu.addSeparator()
        self._menu.addAction(self._quitAction)

        if menuVisible:
            self._popupMenu()

    def _popupMenu(self):
        if self._menu:
            if self._menu.isVisible():
                self._menu.hide()
            rect = self.geometry()
            self._menu.popup(QtCore.QPoint(rect.x(), rect.y()))
            if sys.platform == "win32":
                self._menu.activateWindow()

    def _ipToClipboard(self, idx):
        ipAddress = self._dInfos[idx]['ip_address']
        clipboard = QtWidgets.QApplication.clipboard()
        mimeData = QtCore.QMimeData()
        mimeData.setText(ipAddress)
        clipboard.setMimeData(mimeData)
        QtWidgets.QApplication.processEvents()

    def __messageBox(self, msg, mIcon):
        mBox = QtWidgets.QMessageBox(self._mainWindow)
        mBox.setWindowTitle("DO Manager")
        mBox.setText(msg)
        mBox.setWindowFlags(mBox.windowFlags() | Qt.WindowStaysOnTopHint)
        mBox.setIcon(mIcon)
        return mBox

    def _message(self, msg, error=False):
        self.showMessage("DO Manager", msg)

    def _question(self, msg):
        mBox = self.__messageBox(msg, QtWidgets.QMessageBox.Question)
        mBox.setStandardButtons(mBox.Yes | mBox.No)
        return mBox.exec_() == mBox.Yes

    def _createDroplet(self):
        os.system("%s https://cloud.digitalocean.com/droplets/new" % config.openCommand)

    def _settings(self):
        pd = PreferencesDialog(self._mainWindow)
        pd.showNormal()
        pd.activateWindow()
        pd.exec_()

    def _about(self):
        ad = AboutDialog(self._mainWindow)
        ad.showNormal()
        ad.activateWindow()
        ad.exec_()

    def _report(self):
        os.system("%s %s" % (config.openCommand, config.reportUrl))

    def update(self, silent=False):
        self._updateChecker.check(silent)

    def _quit(self):
        if sys.platform == "win32":
            self.hide()
            QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.quit()