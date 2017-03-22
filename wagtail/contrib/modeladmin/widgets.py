from __future__ import absolute_import, unicode_literals

from django.utils.functional import cached_property

from wagtail.wagtailadmin.widgets import Button, BaseDropdownMenuButton


class ActionButton(Button):
    can_render_self = True  # Used by the `button.html`


class DropdownMenuButton(BaseDropdownMenuButton):
    """A subclass of BaseDropdownMenuButton that takes a list of buttons as an
    `items` argument, which display as a dropdown menu when rendered"""
    can_render_self = True  # Used by the `button.html`
    template_name = 'wagtailadmin/pages/listing/_button_with_dropdown.html'

    def __init__(self, *args, **kwargs):
        self.items = kwargs.pop('items', [])
        self.is_parent = False
        super(DropdownMenuButton, self).__init__(*args, **kwargs)

    @cached_property
    def dropdown_buttons(self):
        return self.items
