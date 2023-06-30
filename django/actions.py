from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.decorators import task
from django.contrib.admin.utils import model_ngettext
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy


@action(
    permissions=["delete"],
    description=gettext_lazy("Удалить выбранные %(verbose_name_plural)s"),
)
def delete_selected(modeladmin, request, queryset):
    """
    Стандартное действие, которое удаляет выбранные объекты.

    Это действие сначала отображает страницу подтверждения, которая показывает все
    удаляемые объекты, или, если у пользователя нет разрешения на один из связанных
    детей (foreignkeys), сообщение "разрешение отклонено".

    Затем он удаляет все выбранные объекты и возвращает обратно к списку изменений.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Заполняем deletable_objects, структура данных всех связанных объектов, которые
    # также будут удалены.
    (
        deletable_objects,
        model_count,
        perms_needed,
        protected,
    ) = modeladmin.get_deleted_objects(queryset, request)

    # Пользователь уже подтвердил удаление.
    # Выполняем удаление и возвращаем None, чтобы снова отобразить представление списка изменений.
    if request.POST.get("post") and not protected:
        if perms_needed:
            raise PermissionDenied
        n = len(queryset)
        if n:
            for obj in queryset:
                obj_display = str(obj)
                modeladmin.log_deletion(request, obj, obj_display)
            modeladmin.delete_queryset(request, queryset)
            modeladmin.message_user(
                request,
                _("Успешно удалено %(count)d %(items)s.")
                % {"count": n, "items": model_ngettext(modeladmin.opts, n)},
                messages.SUCCESS,
            )
        # Возвращаем None, чтобы снова отобразить страницу списка изменений.
        return None

    objects_name = model_ngettext(queryset)

    if perms_needed or protected:
        title = _("Не удается удалить %(name)s") % {"name": objects_name}
    else:
        title = _("Вы уверены?")

    context = {
        **modeladmin.admin_site.each_context(request),
        "title": title,
        "subtitle": None,
        "objects_name": str(objects_name),
        "deletable_objects": [deletable_objects],
        "model_count": dict(model_count).items(),
        "queryset": queryset,
        "perms_lacking": perms_needed,
        "protected": protected,
        "opts": opts,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "media": modeladmin.media,
    }

    request.current_app = modeladmin.admin_site.name

    # Отображаем страницу подтверждения
    return TemplateResponse(
        request,
        modeladmin.delete_selected_confirmation_template
        or [
            "admin/%s/%s/delete_selected_confirmation.html"
            % (app_label, opts.model_name),
            "admin/%s/delete_selected_confirmation.html" % app_label,
            "admin/delete_selected_confirmation.html",
        ],
        context,
    )
