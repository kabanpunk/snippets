import json

from django.conf import settings
from django.contrib.admin.utils import quote
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.text import get_text_list
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

CREATION = 1
UPDATE = 2
REMOVAL = 3

ACTIVITY_TYPES = [
    (CREATION, _("Creation")),
    (UPDATE, _("Update")),
    (REMOVAL, _("Removal")),
]

class ActivityManager(models.Manager):
    use_in_migrations = True

    def log_activity(
        self,
        user_id: str,
        type_id: str,
        item_id: str,
        item_repr: str,
        action_type: int,
        change_details="",
    ):
        if isinstance(change_details, list):
            change_details = json.dumps(change_details)
        return self.model.objects.create(
            user_id=user_id,
            content_type_id=type_id,
            object_id=str(item_id),
            object_repr=item_repr[:200],
            action_flag=action_type,
            change_message=change_details,
        )

class ActivityRecord(models.Model):
    action_time = models.DateTimeField(
        _("action time"),
        default=timezone.now,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.CASCADE,
        verbose_name=_("user"),
    )
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_("content type"),
        blank=True,
        null=True,
    )
    object_id = models.TextField(_("object id"), blank=True, null=True)
    object_repr = models.CharField(_("object representation"), max_length=200)
    action_flag = models.PositiveSmallIntegerField(
        _("action flag"), choices=ACTIVITY_TYPES
    )
    change_message = models.TextField(_("change details"), blank=True)

    objects = ActivityManager()

    class Meta:
        verbose_name = _("activity record")
        verbose_name_plural = _("activity records")
        db_table = "activity_log"
        ordering = ["-action_time"]

    def __repr__(self):
        return str(self.action_time)

    def __str__(self):
        if self.is_creation():
            return gettext("Created “%(object)s”.") % {"object": self.object_repr}
        elif self.is_update():
            return gettext("Updated “%(object)s” — %(changes)s") % {
                "object": self.object_repr,
                "changes": self.get_change_message(),
            }
        elif self.is_removal():
            return gettext("Removed “%(object)s.”") % {"object": self.object_repr}

        return gettext("ActivityRecord Object")

    def is_creation(self):
        return self.action_flag == CREATION

    def is_update(self):
        return self.action_flag == UPDATE

    def is_removal(self):
        return self.action_flag == REMOVAL

    def get_change_message(self):
        """
        Если change_message является структурой JSON, интерпретируйте его как строку изменения, 
        правильно переведенную.
        """
        if self.change_message and self.change_message[0] == "[":
            try:
                change_message = json.loads(self.change_message)
            except json.JSONDecodeError:
                return self.change_message
            messages = []
            for sub_message in change_message:
                if "added" in sub_message:
                    if sub_message["added"]:
                        sub_message["added"]["name"] = gettext(
                            sub_message["added"]["name"]
                        )
                        messages.append(
                            gettext("Added {name} “{object}”.").format(
                                **sub_message["added"]
                            )
                        )
                    else:
                        messages.append(gettext("Added."))

                elif "changed" in sub_message:
                    sub_message["changed"]["fields"] = get_text_list(
                        [
                            gettext(field_name)
                            for field_name in sub_message["changed"]["fields"]
                        ],
                        gettext("and"),
                    )
                    if "name" in sub_message["changed"]:
                        sub_message["changed"]["name"] = gettext(
                            sub_message["changed"]["name"]
                        )
                        messages.append(
                            gettext("Changed {fields} for {name} “{object}”.").format(
                                **sub_message["changed"]
                            )
                        )
                    else:
                        messages.append(
                            gettext("Changed {fields}.").format(
                                **sub_message["changed"]
                            )
                        )

                elif "deleted" in sub_message:
                    sub_message["deleted"]["name"] = gettext(
                        sub_message["deleted"]["name"]
                    )
                    messages.append(
                        gettext("Deleted {name} “{object}”.").format(
                            **sub_message["deleted"]
                        )
                    )

            change_message = " ".join(msg[0].upper() + msg[1:] for msg in messages)
            return change_message or gettext("No fields changed.")
        else:
            return self.change_message

    def get_edited_object(self):
        """Вернуть измененный объект, представленный этой записью в журнале."""
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        """
        Вернуть URL админки для редактирования объекта, представленного этой записью в журнале.
        """
        if self.content_type and self.object_id:
            url_name = "admin:%s_%s_change" % (
                self.content_type.app_label,
                self.content_type.model,
            )
            try:
                return reverse(url_name, args=(quote(self.object_id),))
            except NoReverseMatch:
                pass
        return None
