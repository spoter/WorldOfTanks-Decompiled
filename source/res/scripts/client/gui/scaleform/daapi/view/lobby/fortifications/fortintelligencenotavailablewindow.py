# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/fortifications/FortIntelligenceNotAvailableWindow.py
from gui.Scaleform.genConsts.FORTIFICATION_ALIASES import FORTIFICATION_ALIASES
from gui.Scaleform.genConsts.TEXT_MANAGER_STYLES import TEXT_MANAGER_STYLES
from gui.shared import events, EVENT_BUS_SCOPE
from gui.shared.formatters import icons
from gui.Scaleform.daapi.view.lobby.fortifications.fort_utils.FortViewHelper import FortViewHelper
from gui.Scaleform.daapi.view.meta.FortIntelligenceNotAvailableWindowMeta import FortIntelligenceNotAvailableWindowMeta
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework import AppRef
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.TextManager import TextIcons
from gui.Scaleform.locale.FORTIFICATIONS import FORTIFICATIONS
from helpers import i18n
TEXTS = (FORTIFICATIONS.FORTINTELLIGENCE_HEADERBLOCK,
 FORTIFICATIONS.FORTINTELLIGENCE_TOPBLOCK,
 FORTIFICATIONS.FORTINTELLIGENCE_MIDDLEBLOCK,
 FORTIFICATIONS.FORTINTELLIGENCE_BOTTOMBLOCK)

class FortIntelligenceNotAvailableWindow(AbstractWindowView, View, FortIntelligenceNotAvailableWindowMeta, FortViewHelper, AppRef):

    def __init__(self, ctx):
        super(FortIntelligenceNotAvailableWindow, self).__init__()
        self.__isDefenceHourEnabled = ctx.get('isDefenceHourEnabled')

    def onWindowClose(self):
        self.destroy()

    def onDefenceHourChanged(self, hour):
        if self.fortCtrl.getFort().isDefenceHourEnabled():
            self.fireEvent(events.LoadViewEvent(FORTIFICATION_ALIASES.FORT_INTELLIGENCE_WINDOW, ctx={'isDefenceHourEnabled': True}), EVENT_BUS_SCOPE.LOBBY)
            self.destroy()

    def _populate(self):
        super(FortIntelligenceNotAvailableWindow, self)._populate()
        self.startFortListening()
        self.__makeData()

    def _dispose(self):
        self.stopFortListening()
        super(FortIntelligenceNotAvailableWindow, self)._dispose()

    def __makeData(self):
        data = []
        countIteration = 0
        for item in TEXTS:
            if countIteration == 0 and not self.__isDefenceHourEnabled:
                item = FORTIFICATIONS.FORTINTELLIGENCE_HEADERBLOCKNODEFPERIOD
            data.extend(self.__getLocalize(item, countIteration))
            countIteration += 1

        if self.__isDefenceHourEnabled:
            data.append(self.app.utilsManager.textManager.getText(TEXT_MANAGER_STYLES.NEUTRAL_TEXT, self.__getText(FORTIFICATIONS.FORTINTELLIGENCE_ADDITIONALTEXT_COMINGSOON)))
        self.as_setDataS(data)

    def __getLocalize(self, value, countIteration):
        headerText = TEXT_MANAGER_STYLES.PROMO_SUB_TITLE
        bodyText = TEXT_MANAGER_STYLES.MAIN_TEXT
        alertIcon = ''
        if countIteration == 0:
            headerText = TEXT_MANAGER_STYLES.PROMO_TITLE
            if not self.__isDefenceHourEnabled:
                bodyText = TEXT_MANAGER_STYLES.ALERT_TEXT
                alertIcon = icons.alert() + ' '
        valueHeader = self.app.utilsManager.textManager.getText(headerText, self.__getText(value + '/header'))
        valueBody = self.app.utilsManager.textManager.getText(bodyText, alertIcon + self.__getText(value + '/body'))
        return (valueHeader, valueBody)

    def __getText(self, value):
        return i18n.makeString(value)
