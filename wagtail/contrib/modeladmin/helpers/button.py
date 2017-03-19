from __future__ import absolute_import, unicode_literals

from django.utils.functional import cached_property
from django.utils.six import string_types

from wagtail.wagtailadmin.widgets import Button, BaseDropdownMenuButton


class ActionButton(Button):
    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        if title:
            if kwargs.get('attrs'):
                kwargs['attrs']['title'] = title
            else:
                kwargs['attrs'] = {'title': title}
        return super(ActionButton, self).__init__(*args, **kwargs)


class ActionButtonWithDropdown(BaseDropdownMenuButton):
    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        if title:
            if kwargs.get('attrs'):
                kwargs['attrs']['title'] = title
            else:
                kwargs['attrs'] = {'title': title}
        self.items = kwargs.pop('items', [])
        super(ActionButtonWithDropdown, self).__init__(*args, **kwargs)

    @cached_property
    def dropdown_buttons(self):
        return self.items


class IntrospectiveButtonHelper(object):

    button_class = ActionButton
    dropdown_button_class = ActionButtonWithDropdown
    index_view_list_template = 'modeladmin/includes/index_view_button_list.html'
    inspect_view_list_template = 'modeladmin/includes/inspect_view_button_list.html'

    @classmethod
    def modify_button_css_classes(cls, button, add, remove):
        button.classes.difference_update(remove)
        button.classes.update(add)

    def __init__(self, request, model_admin):
        self.request = request
        self.model_admin = model_admin
        self.permission_helper = model_admin.permission_helper

    def get_button_definition(self, codename, obj=None):
        """
        Attempt to find a method or attribute that will return a button
        definition for action `codename`, call it (if it's callable) and
        return the value.
        """
        attribute_name = '%s_button' % codename
        if hasattr(self.model_admin, attribute_name):
            attribute = getattr(self.model_admin, attribute_name)
        elif hasattr(self, attribute_name):
            attribute = getattr(self, attribute_name)
        else:
            return self.make_button_definition_for_action(codename, obj)

        if not callable(attribute):
            return attribute
        try:
            # Call the method with the standard `request` / `obj` arguments
            return attribute(request=self.request, obj=obj)
        except TypeError:
            # Some button definitions don't take an `obj` argument
            return attribute(request=self.request)
        return attribute()

    def make_button_definition_for_action(self, codename, obj=None):
        """
        Create a dictionary of arguments that can be used to create a button
        for action `codename` for `obj`
        """
        ma = self.model_admin
        permissions_required = None
        if self.permission_helper.has_methods_to_check_for_action(codename):
            permissions_required = codename

        # With the exception of 'permissions_required', these values
        # will be used as init kwargs to create a `self.button_class` instance
        return {
            'permissions_required': permissions_required,
            'url': ma.get_button_url_for_action(codename, obj),
            'label': ma.get_button_label_for_action(codename, obj),
            'title': ma.get_button_title_for_action(codename, obj),
            'classes': ma.get_button_css_classes_for_action(codename, obj),
        }

    def make_button_for_obj(self, obj, **button_kwargs):
        # Note: 'permissions_required' is popped from button_kwargs, and
        # so won't be passed as an init kwarg to `self.button_class`
        perms_required = button_kwargs.pop('permissions_required', [])
        perms_required = None
        if perms_required:
            # If perms_required is a single string, make it into a tuple
            if isinstance(perms_required, string_types):
                perms_required = (perms_required, )
            # Check that user must have all the necessary perms
            if not any(
                self.permission_helper.user_has_permission_for_action(
                    self.request.user, perm, obj
                ) for perm in perms_required
            ):
                return None
        # Always make 'classes' a set
        button_kwargs['classes'] = set(button_kwargs.get('classes', []))
        return self.button_class(**button_kwargs)

    def get_button_set_for_obj(self, obj, codename_list, classes_add=(),
                               classes_remove=()):
        button_definitions = []
        buttons = []

        for val in codename_list:
            if isinstance(val, tuple):
                items = self.get_button_set_for_obj(obj, val[1])
                title = self.model_admin.get_button_title_for_action(
                    'dropdown', obj
                )
                button_definitions.append(self.dropdown_button_class(
                    label=val[0], title=title, items=items
                ))
            else:
                button_definitions.append(self.get_button_definition(val, obj))

        for definition in button_definitions:
            # `definition` could be a `Button` instance
            if isinstance(definition, Button) and definition.show:
                buttons.append(definition)
            elif definition:
                # `definition` is a dict of init kwargs
                button = self.make_button_for_obj(obj, **definition)
                if button:
                    # `button` could be `None` if, for example, the user was
                    # found to have insufficient permissions
                    self.modify_button_css_classes(
                        button, classes_add, classes_remove
                    )
                    buttons.append(button)
        return buttons

    def add_button(self, request):
        return self.make_button_definition_for_action('add')

    def inspect_button(self, request, obj):
        if not self.model_admin.inspect_view_enabled:
            return None
        return self.make_button_definition_for_action('inspect', obj)

    def unpublish_button(self, request, obj):
        if not getattr(obj, 'live', False):
            return None
        return self.make_button_definition_for_action('unpublish', obj)

    def view_draft_button(self, request, obj):
        if not getattr(obj, 'has_unpublished_changes', False):
            return None
        return self.make_button_definition_for_action('view_draft', obj)

    def view_live_button(self, request, obj):
        if not getattr(obj, 'live', False):
            return None
        ma = self.model_admin
        return {
            'url': obj.relative_url(request.site),
            'label': ma.get_button_label_for_action('view_live', obj),
            'title': ma.get_button_title_for_action('view_live', obj),
            'classes': ma.get_button_css_classes_for_action('view_live', obj),
            'attrs': {'target': '_blank'},
        }
