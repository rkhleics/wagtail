from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


def fix_proxy_model_permissions(**kwargs):
    for model in apps.get_models():
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
            permissions_query, content_type=concrete_content_type
        ).update(content_type=proxy_content_type)
