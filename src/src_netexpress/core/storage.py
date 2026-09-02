"""Private files are stored outside MEDIA_ROOT and served only after authorization."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property
from whitenoise.storage import CompressedManifestStaticFilesStorage


class ToleranteStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Ne fait pas tomber une page entière pour un fichier statique introuvable.

    Jazzmin écrit ``{% static 'vendor/bootswatch' %}`` — un répertoire, qui ne
    peut par nature figurer dans le manifeste. En mode strict, cette seule ligne
    lève une ValueError et rend toute l'administration inaccessible en 500.

    La garantie n'est pas perdue pour autant : le test
    ``tests/test_static_references`` balaie les gabarits du projet et refuse
    toute référence sans fichier. Le contrôle strict reste donc là où nous
    écrivons le code, et une bizarrerie de dépendance ne peut plus couper
    l'accès à l'administration.
    """

    manifest_strict = False

    def stored_name(self, name: str) -> str:
        """Retombe sur le chemin brut quand le nom haché est introuvable.

        ``manifest_strict = False`` ne suffit pas seul : Django bascule alors
        sur ``hashed_name()``, qui tente d'ouvrir le fichier et lève à son tour
        s'il s'agit d'un répertoire ou d'un chemin inexistant. C'est ici qu'il
        faut rattraper, pas au niveau du manifeste.
        """
        try:
            return super().stored_name(name)
        except ValueError:
            return name


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
