from __future__ import absolute_import, unicode_literals

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import cached_property

from wagtail.wagtailcore.models import Page, UserPagePermissionsProxy


class BasePermissionHelper(object):

    def __init__(self, user, model, inspect_view_enabled=False):
        self.user = user
        self.model = model
        self.opts = model._meta
        self.inspect_view_enabled = inspect_view_enabled

    def action_is_permitted(self, codename, obj=None):
        """Return a boolean to indicate whether self.user has permission to
        perform an 'action' (specified by `codename`), potentially on a
        specific model instance (specified by `obj`)."""
        object_specific_method_name = 'can_%s_obj' % codename
        blanket_method_name = 'can_%s' % codename

        # Attempt to find and call a method with a name matching the
        # 'object_specific_method_name' pattern
        if obj and hasattr(self, object_specific_method_name):
            method = getattr(self, object_specific_method_name)
            try:
                return method(obj=obj)
            except TypeError:
                raise TypeError(
                    "The '%s' method on your '%s' class should accept "
                    "'self' and 'obj' as arguments only" % (
                        object_specific_method_name, self.__class__.__name__,
                    )
                )

        # Attempt to find and call a method with a name matching the
        # 'blanket_method_name' pattern
        elif hasattr(self, blanket_method_name):
            attr = getattr(self, blanket_method_name)
            if callable(attr):
                try:
                    return attr()
                except TypeError:
                    raise TypeError(
                        "The '%s' method on your '%s' class should accept "
                        "'self' and no other arguments" % (
                            blanket_method_name, self.__class__.__name__,
                        )
                    )
            return attr

        return self.generic_permission_check(codename, obj)

    def generic_permission_check(self, codename, obj):
        """When `action_is_permitted` cannot find a specifically named method
        to check for action `codename`, this method is called to attempt a
        more 'generic' permission enquiry
        """
        raise NotImplementedError(
            "Permission helper classes must implement their own "
            "'fallback_permission_check' method"
        )

    def can_list(self):
        raise NotImplementedError(
            "Permission helper classes must implement their own "
            "'can_list' method"
        )

    def can_inspect_obj(self, obj):
        if not self.inspect_view_enabled:
            return False
        return self.can_list()


class PermissionHelper(BasePermissionHelper):
    """
    Provides permission-related helper functions to help determine what a
    user can do with a 'typical' model (where permissions are granted
    model-wide), and to a specific instance of that model.
    """

    # Accounts for differences in terminology between modeladmin/wagtail and
    # django's auth module
    perm_codename_corrective_mappings = {
        'create': 'add',
        'edit': 'change',
    }

    def get_all_model_permissions(self):
        """
        Return a queryset of all Permission objects pertaining to the `model`
        specified at initialisation
        """
        content_type = ContentType.objects.get_for_model(self.model)
        return Permission.objects.filter(content_type=content_type)

    def get_perm_codename(self, action_codename):
        codename = self.action_perm_codename_mappings.get(action_codename, action_codename)
        return get_permission_codename(codename, self.opts)

    def has_perm(self, action_codename=None, perm_codename=None):
        if action_codename:
            perm_codename = self.get_perm_codename(action_codename)
        if perm_codename:
            # Combine `perm_codename` with `self.opts.app_label` to call the
            # self.user's `has_perm` method
            perm_check_string = "%s.%s" % (self.opts.app_label, perm_codename)
            return self.user.has_perm(perm_check_string)
        return False  # No codename supplied

    @cached_property
    def user_has_any_permissions(self):
        """
        Return a boolean to indicate whether `self.user` has any model-wide
        permissions.
        """
        for perm in self.get_all_model_permissions().values('codename'):
            if self.has_perm(perm_codename=perm['codename']):
                return True
        return False

    def generic_permission_check(self, codename, obj):
        """When 'user_has_permission_permission_for_action()' fails to find a
        specifically named method for checking permission for an action, resort
        to a standard django auth model-wide permission check"""
        return self.has_perm(action_codename=codename)

    def can_list(self):
        """Return a boolean to indicate whether `self.user` is permitted to
        access the list/index view for `self.model`"""
        return self.user_has_any_permissions

    @cached_property
    def inspect_permission_exists(self):
        """Return a boolean to indicate whether a custom 'inspect' auth
        permission has been defined for `self.model`"""
        perm_codename = get_permission_codename('inspect', self.opts)
        return self.get_all_model_permissions().filter(
            codename__exact=perm_codename).exists()

    def can_inspect_obj(self, obj):
        if self.inspect_view_enabled and self.inspect_permission_exists:
            return self.has_perm(action_codename='inspect')
        return super(PermissionHelper, self).can_inspect_obj(obj)


class PagePermissionHelper(BasePermissionHelper):
    """
    Provides permission-related helper functions to help determine what
    a user can do with a model extending Wagtail's Page model. It differs
    from `PermissionHelper`, because model-wide permissions aren't really
    relevant. We generally need to determine permissions on an
    object-specific basis.
    """

    def get_valid_parent_pages(self):
        """Identifies possible parent pages for the current user by first
        looking at allowed_parent_page_models() on self.model to limit options
        to the correct type of page, then checking permissions on those
        individual pages to make sure we have permission to add a subpage to
        it."""

        # Get queryset of pages where this page type can be added
        allowed_parent_page_content_types = list(ContentType.objects.get_for_models(*self.model.allowed_parent_page_models()).values())
        allowed_parent_pages = Page.objects.filter(content_type__in=allowed_parent_page_content_types)

        # Get queryset of pages where the user has permission to add subpages
        if self.user.is_superuser:
            pages_where_user_can_add = Page.objects.all()
        else:
            pages_where_user_can_add = Page.objects.none()
            user_perms = UserPagePermissionsProxy(self.user)

            for perm in user_perms.permissions.filter(permission_type='add'):
                # user has add permission on any subpage of perm.page
                # (including perm.page itself)
                pages_where_user_can_add |= Page.objects.descendant_of(perm.page, inclusive=True)

        # Combine them
        return allowed_parent_pages & pages_where_user_can_add

    def generic_permission_check(self, codename, obj):
        """When action_is_permitted() fails to find a specifically named
        method for checking permission for an action, and a page object is
        supplied, use the page object to create a PagePermissionTester
        instance, and attempt to find and call a relevant method on that"""
        if obj:
            page_perm_tester = obj.permissions_for_user(self.user)
            method_name = 'can_%s' % codename
            if hasattr(page_perm_tester, method_name):
                return getattr(page_perm_tester, method_name)()
        return False

    def user_can_list(self, user):
        """
        For models extending Page, permitted actions are determined by
        permissions on individual objects. Rather than check for change
        permissions on every object individually (which would be quite
        resource intensive), we simply always allow the list view to be
        viewed, and limit further functionality when relevant.
        """
        return True

    def user_can_create(self, user):
        """
        For models extending Page, whether or not a page of this type can be
        added somewhere in the tree essentially determines the add permission,
        rather than actual model-wide permissions
        """
        return self.get_valid_parent_pages(user).exists()

    def user_can_copy_obj(self, user, obj):
        parent_page = obj.get_parent()
        return parent_page.permissions_for_user(user).can_publish_subpage()
