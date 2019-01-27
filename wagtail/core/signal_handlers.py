import logging

import django
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_delete, post_migrate

from wagtail.core.models import Page, Site


logger = logging.getLogger('wagtail.core')


# Clear the wagtail_site_root_paths from the cache whenever Site records are updated.
def post_save_site_signal_handler(instance, update_fields=None, **kwargs):
    cache.delete('wagtail_site_root_paths')


def post_delete_site_signal_handler(instance, **kwargs):
    cache.delete('wagtail_site_root_paths')


def pre_delete_page_unpublish(sender, instance, **kwargs):
    # Make sure pages are unpublished before deleting
    if instance.live:
        # Don't bother to save, this page is just about to be deleted!
        instance.unpublish(commit=False)


def post_delete_page_log_deletion(sender, instance, **kwargs):
    logger.info("Page deleted: \"%s\" id=%d", instance.title, instance.id)


def fix_proxy_model_permissions(**kwargs):
    """
    A back-fill that ensures ``Permission`` objects for proxy models are
    associated with the ``ContentType`` of the proxy model, instead of that
    of the concrete model. This is necessary to allow Wagtail to support proxy
    models consitently accross all supported versions of Django (2.0+).

    Because it affects permissions for ALL proxy models in a project,
    regardless of whether they are registered with Wagtail, developers must
    opt in to this behaviour by adding the following to their Django settings::

        WAGTAIL_UPDATE_PROXY_MODEL_PERMISSIONS = True

    Django already associates proxy models permissions and content
    types in this way from 2.2 onwards, so this method only has any affect in
    projects using earlier Django versions.
    """
    if(
        django.VERSION >= (2, 2) or
        not getattr(settings, 'WAGTAIL_UPDATE_PROXY_MODEL_PERMISSIONS', False)
    ):
        return

    for model in django.apps.get_models():
        opts = model._meta

        if not opts.proxy:
            continue

        proxy_content_type, created = ContentType.objects.get_or_create(
            app_label=opts.app_label,
            model=opts.model_name,
        )

        concrete_content_type = ContentType.objects.get_for_model(model, for_concrete_model=True)

        default_permission_codenames = [
            '%s_%s' % (action, opts.model_name)
            for action in opts.default_permissions
        ]
        permissions_query = Q(codename__in=default_permission_codenames)
        for codename, name in opts.permissions:
            permissions_query |= Q(codename=codename, name=name)

        Permission.objects.filter(
            permissions_query,
            content_type=concrete_content_type
        ).update(content_type=proxy_content_type)


def register_signal_handlers():
    post_save.connect(post_save_site_signal_handler, sender=Site)
    post_delete.connect(post_delete_site_signal_handler, sender=Site)

    pre_delete.connect(pre_delete_page_unpublish, sender=Page)
    post_delete.connect(post_delete_page_log_deletion, sender=Page)

    post_migrate.connect(fix_proxy_model_permissions)
