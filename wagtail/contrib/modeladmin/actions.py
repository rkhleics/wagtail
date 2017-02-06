from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.core.exceptions import ImproperlyConfigured


class ModelAdminAction(object):

    def __init__(
        self,
        codename,
        model_admin,
        button_text='',
        button_title='',
        button_url='',
        button_classnames=[],
        register_url=True,
        instance_specific=False,
        url_pattern='',
        permissions_required=[],
        view_class=None,
    ):
        self.codename = codename
        self.ma = model_admin
        self.button_text = button_text
        self.button_title = button_title
        self.button_url = button_url
        self.button_classnames = button_classnames
        self.register_url = register_url
        self.instance_specific = instance_specific
        self.permissions_required = permissions_required
        self.view_class = view_class
        self.url_pattern = url_pattern

    def get_url_pattern(self):
        return self.url_pattern or self.ma.url_helper.get_action_url_pattern(
            self.codename)

    def get_url_name(self):
        return self.ma.url_helper.get_action_url_name(self.codename)

    def get_templates(self):
        template = getattr(self.ma, '%s_template' % self.codename, None)
        return template or self.ma.get_templates(self.codename)

    def get_view_class(self):
        ma_attr_name = '%s_view_class' % self.codename
        return self.view_class or getattr(self.ma, ma_attr_name, None)

    def connect_to_view(self, **kwargs):
        view_class = self.get_view_class()
        if view_class is None:
            raise ImproperlyConfigured(
                "No view class could be identified for the '%s' action. "
                "Please either add a '%s_view_class' attribute to %s "
                "specifying the correct view to use, or provide a "
                "'view_class' value in the '%s' action definition." % (
                    self.codename,
                    self.codename,
                    type(self.ma),
                    self.codename,
                )
            )
        return self.view_class.as_view(self.ma)(**kwargs)

    @property
    def url(self):
        return url(
            self.get_url_pattern(), self.connect_to_view, self.get_url_name()
        )
