from .url import AdminURLHelper, PageAdminURLHelper
from .permission import PermissionHelper, PagePermissionHelper
from .button import IntrospectiveButtonHelper
from .deprecated import ButtonHelper as BH, PageButtonHelper as PBH


# TODO - Add deprecation warnings when importing the below

class ButtonHelper(BH):
    pass


class PageButtonHelper(PBH):
    pass
