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
        """
        The site resource simple returns info about the site
        """
        return self.GET()["site"]


class ImageResource(GhostResource):
    resource = "images"
    api = "admin"

    def _load(self, path: str):
        """
        Load an image by path

        Args:
            path (str): to the image

        Returns:
            BytesIO: image bytes
        """
        with open(path, "rb") as image:
            return BytesIO(image.read())

    def upload(self, image_obj_or_path, image_name: str=None):
        """
        Args:
            image_obj_or_path (BytesIO | str): either a path to the image or its bytes
            image_name (str): optional image title (can also be used from path)

        Returns:
            str: uploaded image URL
        """
        # todo: support other filetypes than image/jpeg

        if isinstance(image_obj_or_path, str):
            if not image_name:
                image_name = os.path.basename(image_obj_or_path)

            image_obj_or_path = self._load(image_obj_or_path)

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

    def _create_zip(self, folder: str):
        """
        Create a zip of folder

        Args:
            folder (str): what to zip

        Returns:
            Path: to zip
        """

        archive = Path(f"{folder}.zip")
        shutil.make_archive(str(archive).replace(".zip", ""), "zip", folder)

        return archive

    def _upload_zip(self, zipfile: Path):
        """
        POST a zipfile to Ghost.

        Returns:
            str: uploaded filename
        """
        with zipfile.open("rb") as file:
            resp = self.POST(
                "upload",
                files={"file": (zipfile.name, file, "application/zip")},
            )

        return resp["themes"][0]["name"]

    def upload(self, file_or_folder: str):
        """
        Upload a zipfile or folder as a Ghost theme.
        If a folder is selected it will be zipped before upload.

        Args:
            file_or_folder (str): path to theme.

        """
        path = Path(file_or_folder)

        if path.is_file():
            return self._upload_zip(path)
        elif path.exists():
            # -> is folder
            file = self._create_zip(file_or_folder)

            return self._upload_zip(file)
        else:
            raise FileNotFoundError(file_or_folder)

    def activate(self, name: str):
        """
        Enable a theme by name

        Returns:
            str: the activated theme's name
        """
        resp = self.PUT(name, "activate")

        return resp["themes"][0]["name"]


# todo: (admin) tiers, offers, webhooks, ...?
# todo: (content): ...?
