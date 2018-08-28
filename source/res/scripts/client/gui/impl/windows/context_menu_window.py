# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/impl/windows/context_menu_window.py
import logging
import BigWorld
from frameworks.wulf import View, ViewFlags, Window, WindowFlags
from gui.impl.gen import R
from gui.impl.gen.view_models.ui_kit.context_menu_item_model import ContextMenuItemModel
from gui.impl.gen.view_models.windows.context_menu_content_model import ContextMenuContentModel
from gui.impl.gen.view_models.windows.context_menu_window_model import ContextMenuWindowModel
from gui.impl.windows.window_view import WindowView
_logger = logging.getLogger(__name__)

class ContextMenuContent(View):

    def __init__(self):
        super(ContextMenuContent, self).__init__(R.views.contextMenuContent, ViewFlags.COMPONENT, ContextMenuContentModel)

    @property
    def viewModel(self):
        return super(ContextMenuContent, self).getViewModel()

    def _initialize(self):
        super(ContextMenuContent, self)._initialize()
        with self.viewModel.transaction() as tx:
            self._initItems()
            total = len(tx.getContextMenuList())
            separators = len([ element for element in tx.getContextMenuList() if element.getIsSeparator() ])
            tx.setItemsCount(total - separators)
            tx.setSeparatorsCount(separators)
        self.viewModel.onItemClicked += self.__onItemClicked

    def _finalize(self):
        self.viewModel.onItemClicked -= self.__onItemClicked
        super(ContextMenuContent, self)._finalize()

    def _addItem(self, actionID, label, icon=None, isEnabled=True):
        item = ContextMenuItemModel()
        item.setId(actionID)
        item.setLabel(label)
        item.setIsEnabled(isEnabled)
        if icon is not None:
            item.setIcon(icon)
        self.viewModel.getContextMenuList().addViewModel(item)
        return

    def _updateItem(self, actionID, label=None, icon=None, isEnabled=True):
        found = [ element for element in self.viewModel.getContextMenuList() if element.getId() == actionID ]
        if not found:
            _logger.error('%r: context menu item is not found by %r', self, actionID)
            return
        else:
            item = found[0]
            with item.transaction() as tx:
                if label is not None:
                    tx.setLabel(label)
                tx.setIsEnabled(isEnabled)
                if icon is not None:
                    item.setIcon(icon)
            return

    def _addSeparator(self):
        separator = ContextMenuItemModel()
        separator.setIsSeparator(True)
        self.viewModel.getContextMenuList().addViewModel(separator)

    def _initItems(self):
        raise NotImplementedError('Method _initItems should be overridden in {}'.format(self))

    def _onAction(self, actionID):
        raise NotImplementedError('Method _onAction should be overridden in {}'.format(self))

    def __onItemClicked(self, args=None):
        if 'actionID' not in args:
            _logger.error('%r: Argument "actionID" is not defined in %r', self, args)
            return
        else:
            self._onAction(int(args['actionID']))
            window = self.getParentWindow()
            if window is not None:
                BigWorld.callback(0.0, window.destroy)
            else:
                _logger.error('%r: This is unexpected case, content does not have parent window', self)
            return


class ContextMenuWindow(Window):
    __slots__ = ()

    def __init__(self, event, content, parent):
        super(ContextMenuWindow, self).__init__(wndFlags=WindowFlags.CONTEXT_MENU, decorator=WindowView(layoutID=R.views.contextMenuWindow, viewModelClazz=ContextMenuWindowModel), content=content, parent=parent)
        self.contextMenuModel.setX(event.mouse.positionX)
        self.contextMenuModel.setY(event.mouse.positionY)

    @property
    def contextMenuModel(self):
        return super(ContextMenuWindow, self)._getDecoratorViewModel()
