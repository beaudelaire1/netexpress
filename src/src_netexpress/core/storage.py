"""Private files are stored outside MEDIA_ROOT and served only after authorization."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property


@deconstructible
class PrivateStorage(FileSystemStorage):
    @cached_property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    def _clear_cached_properties(self, setting, **kwargs):
        if setting == "PRIVATE_MEDIA_ROOT":
            self.__dict__.pop("base_location", None)
            self.__dict__.pop("location", None)
        super()._clear_cached_properties(setting=setting, **kwargs)

    def url(self, name):
        return reverse("private_document", kwargs={"name": name})


private_storage = PrivateStorage()
