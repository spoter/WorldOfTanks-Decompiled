# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/RadialMenuMeta.py
from gui.Scaleform.framework.entities.BaseDAAPIComponent import BaseDAAPIComponent

class RadialMenuMeta(BaseDAAPIComponent):
    """
    DO NOT MODIFY!
    Generated with yaml.
    __author__ = 'yaml_processor'
    @extends BaseDAAPIComponent
    null
    """

    def onSelect(self):
        """
        :return :
        """
        self._printOverrideError('onSelect')

    def onAction(self, action):
        """
        :param action:
        :return :
        """
        self._printOverrideError('onAction')

    def as_buildDataS(self, data):
        """
        :param data:
        :return :
        """
        return self.flashObject.as_buildData(data) if self._isDAAPIInited() else None

    def as_showS(self, radialState, offset, ratio):
        """
        :param radialState:
        :param offset:
        :param ratio:
        :return :
        """
        return self.flashObject.as_show(radialState, offset, ratio) if self._isDAAPIInited() else None

    def as_hideS(self):
        """
        :return :
        """
        return self.flashObject.as_hide() if self._isDAAPIInited() else None
