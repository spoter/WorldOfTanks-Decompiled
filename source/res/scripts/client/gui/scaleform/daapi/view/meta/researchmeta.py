# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/ResearchMeta.py
from gui.Scaleform.daapi.view.lobby.techtree.ResearchView import ResearchView

class ResearchMeta(ResearchView):

    def requestNationData(self):
        self._printOverrideError('requestNationData')

    def getResearchItemsData(self, vehCD, rootChanged):
        self._printOverrideError('getResearchItemsData')

    def onResearchItemsDrawn(self):
        self._printOverrideError('onResearchItemsDrawn')

    def goToTechTree(self, nation):
        self._printOverrideError('goToTechTree')

    def exitFromResearch(self):
        self._printOverrideError('exitFromResearch')

    def as_drawResearchItemsS(self, nation, vehCD):
        return self.flashObject.as_drawResearchItems(nation, vehCD) if self._isDAAPIInited() else None

    def as_setFreeXPS(self, freeXP):
        return self.flashObject.as_setFreeXP(freeXP) if self._isDAAPIInited() else None

    def as_setInstalledItemsS(self, data):
        return self.flashObject.as_setInstalledItems(data) if self._isDAAPIInited() else None

    def as_setWalletStatusS(self, walletStatus):
        return self.flashObject.as_setWalletStatus(walletStatus) if self._isDAAPIInited() else None
