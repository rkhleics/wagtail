from __future__ import absolute_import, unicode_literals

from django.contrib.admin.utils import quote
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from django.utils.http import urlquote

wagtailadmin_page_actions = (
    'add', 'edit', 'delete', 'copy', 'move', 'preview', 'view_draft',
    'unpublish', 'revisions_index', 'add_subpage'
)


class AdminURLHelper(object):

    def __init__(self, model):
        self.model = model
        self.opts = model._meta

    def _get_action_url_pattern(self, action):
        if action == 'index':
            return r'^%s/%s/$' % (self.opts.app_label, self.opts.model_name)
        return r'^%s/%s/%s/$' % (self.opts.app_label, self.opts.model_name,
                                 action)

    def _get_object_specific_action_url_pattern(self, action):
        return r'^%s/%s/%s/(?P<instance_pk>[-\w]+)/$' % (
            self.opts.app_label, self.opts.model_name, action)

    def get_action_url_pattern(self, action):
        if action in ('create', 'choose_parent', 'index'):
            return self._get_action_url_pattern(action)
        return self._get_object_specific_action_url_pattern(action)

    def get_action_url_name(self, action):
        return '%s_%s_modeladmin_%s' % (
            self.opts.app_label, self.opts.model_name, action)

    def get_action_url(self, action, *args, **kwargs):
        if action in ('create', 'choose_parent', 'index'):
            return reverse(self.get_action_url_name(action))
        url_name = self.get_action_url_name(action)
        return reverse(url_name, args=args, kwargs=kwargs)

    def get_action_url_for_obj(self, action, obj, *args):
        if obj is None:
            return self.get_action_url(action, *args)
        args = (quote(getattr(obj, self.opts.pk.attname)),) + args
        return self.get_action_url(action, *args)

    @cached_property
    def index_url(self):
        return self.get_action_url('index')

    @cached_property
    def create_url(self):
        return self.get_action_url('create')


class PageAdminURLHelper(AdminURLHelper):

    def get_action_url(self, action, *args, **kwargs):
        # Note: 'add' is used below, because that's the terminology used by
        # wagtail's page editing urls / views. For pages, if the action is
        # 'create', this method should supply the URL for `ChooseParentView`,
        # rather than going straight to 'wagtailadmin_pages:add'
        if action in wagtailadmin_page_actions:
            url_name = 'wagtailadmin_pages:%s' % action
            target_url = reverse(url_name, args=args, kwargs=kwargs)
            return '%s?next=%s' % (target_url, urlquote(self.index_url))
        return super(PageAdminURLHelper, self).get_action_url(action, *args,
                                                              **kwargs)
