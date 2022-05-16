import os.path
import shutil
from io import BytesIO
from pathlib import Path

from .abs_resources import GhostAdminResource, GhostContentResource, GhostResource


# Admin


class PostResource(GhostAdminResource):
    # See: https://ghost.org/docs/admin-api/#the-post-object
    resource = "posts"


class PageResource(GhostAdminResource):
    # See: https://ghost.org/docs/admin-api/#the-post-object
    resource = "pages"


class TagResource(GhostAdminResource):
    # experimental
    resource = "tags"


class MemberResource(GhostAdminResource):
    resource = "members"


# Content


class AuthorResource(GhostContentResource):
    resource = "authors"


class SettingsResource(GhostContentResource):
    resource = "settings"


# Custom


class SiteResource(GhostResource):
    resource = "site"
    api = "admin"

    def get(self, _=None, **__):
        return self.GET()["site"]


class ImageResource(GhostResource):
    resource = "images"
    api = "admin"

    def load(self, path):
        with open(path, "rb") as image:
            return BytesIO(image.read())

    def upload(self, image_obj_or_path, image_name=None):
        # todo: support other filetypes than image/jpeg

        if isinstance(image_obj_or_path, str):
            if not image_name:
                image_name = os.path.basename(image_obj_or_path)

            image_obj_or_path = self.load(image_obj_or_path)

        files = {"file": (image_name, image_obj_or_path, "image/jpeg")}
        params = {
            "purpose": "image",
            "ref": image_name,
        }  # 'image', 'profile_image', 'icon'
        result = self.POST("upload", files=files, params=params)

        return result["images"][0]["url"]


class ThemeResource(GhostResource):
    resource = "themes"
    api = "admin"

    def _create_zip(self, folder):
        archive = Path(f"{folder}.zip")
        shutil.make_archive(str(archive).replace(".zip", ""), "zip", folder)

        return archive

    def _upload_zip(self, zipfile: Path):
        with zipfile.open("rb") as file:
            resp = self.POST(
                "upload",
                files={"file": (zipfile.name, file, "application/zip")},
            )

        return resp["themes"][0]["name"]

    def upload(self, file_or_folder):
        path = Path(file_or_folder)

        if path.is_file():
            return self._upload_zip(path)
        elif path.exists():
            # -> is folder
            file = self._create_zip(file_or_folder)

            return self._upload_zip(file)
        else:
            raise FileNotFoundError(file_or_folder)

    def activate(self, name):
        resp = self.PUT(name, "activate")

        return resp["themes"][0]["name"]


# todo: (admin) tiers, offers, webhooks, ...?
# todo: (content): ...?
