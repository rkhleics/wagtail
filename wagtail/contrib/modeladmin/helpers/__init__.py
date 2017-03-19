from .url import AdminURLHelper, PageAdminURLHelper
from .permission import PermissionHelper, PagePermissionHelper
from .button import GenericButtonHelper
from .deprecated import ButtonHelper as Bh, PageButtonHelper as Pbh

# TODO - Add deprecation warnings when importing the below


class ButtonHelper(Bh):
    pass


class PageButtonHelper(Pbh):
    pass
