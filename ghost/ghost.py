# n.a.v. https://xbopp.com/ghost-api-python-3-x-4/
import json
from pathlib import Path

import jwt
import requests
import time
import sys
import shutil

from datetime import datetime as dt
from io import BytesIO

from attr import define, field
from typing import BinaryIO

MAX_ERROR_LIMIT = 3


@define
class GhostAdmin:
    """
    # Admin API

    https://ghost.org/docs/admin-api/#posts
        - GET /admin/posts/ -> getAllPosts()
        - GET /admin/posts/{id}/ -> getPostById(id)
        - GET /admin/posts/slug/{slug}/ -> getPostBySlug(slug)
        - POST /admin/posts/ -> createPost()
        - PUT /admin/posts/{id}/ -> updatePostById(id)
        - DELETE /admin/posts/{id}/ -> deletePostById(id)

    https://ghost.org/docs/admin-api/#pages
        - GET /admin/pages/ -> getAllPages()
        - GET /admin/pages/{id}/ -> getPageById(id)
        - GET /admin/pages/slug/{slug}/ -> getPageBySlug(slug)
        - POST /admin/pages/ -> createPage()
        - PUT /admin/pages/{id}/ -> updatePageById(id)
        - DELETE /admin/pages/{id}/ -> deletePageById(id)

    https://ghost.org/docs/admin-api/#images
        - POST /admin/images/upload/ -> imageUpload()

    https://ghost.org/docs/admin-api/#themes
        - POST /admin/themes/upload -> uploadTheme(folder) / uploadTheme(file)
        - PUT /admin/themes/{name}/activate -> activateTheme(name)

    https://ghost.org/docs/admin-api/#site
        - GET /admin/site/ -> getSite()

    https://ghost.org/docs/admin-api/#webhooks
        (Not Implemented)
        - POST /admin/webhooks/ -> createWebhook()
        - PUT /admin/webhooks/{id}/ -> updateWebhook(id)
        - DELETE /admin/webhooks/{id}/ -> deletewWebhook(id)

    # Content API

    https://ghost.org/docs/content-api/#authors
        - GET /content/authors/ -> getAllAuthors()
        - GET /content/authors/{id}/ -> getAuthorById(id)
        - GET /content/authors/slug/{slug}/ -> getAuthorBySlug(slug)

    https://ghost.org/docs/content-api/#tags
        - GET /content/tags/ -> getAllTags()
        - GET /content/tags/{id}/ -> getTagById(id)
        - GET /content/tags/slug/{slug}/ -> getTagBySlug(slug)

    https://ghost.org/docs/content-api/#settings
        - GET /content/settings/ -> getSettings()
    """

    # todo (admin):
    # - tags (Experimental)
    # - users (Experimental)

    url: str
    adminAPIKey: str = field(repr=lambda _: "***")
    contentAPIKey: str = field(repr=lambda _: "***")
    headers: dict = field(init=False, repr=False)
    api_version: int = "v4"  # or v3

    def __attrs_post_init__(self):
        """
        Setup the JWT Authentication headers
        """

        self.headers = self.createHeaders()

    def interact(
            self, verb, endpoint, params=None, files=None, json=None, api_version=None
    ):
        """
        Sends HTTP requests to the Ghost API Endpoint

        Args:
            verb (string): GET, POST, PUT, DELETE
            endpoint (string): The last part of the API URL; e.g. admin/post
            params (dict|list|tuple): query string parameters
            files (dict):  files to send to the server
            json (dict): data to send to the server
            api_version (string): which version to use (v3 or v4 is supported), overwrites self.api_version

        See Also https://docs.python-requests.org/en/latest/api/

        Returns:
            requests.Response
        """

        if endpoint.startswith("content"):
            endpoint += "?key=" + self.contentAPIKey

        if api_version is None:
            # default
            api_version = self.api_version
            headers = self.headers
        else:
            # custom api version, new headers:
            headers = self.createHeaders(api_version)

        verb = verb.lower()

        # url + /ghost/api/ + /v3/admin/ + ...
        url = "/".join([self.url.strip("/"), "ghost/api", api_version, endpoint])

        error_count = 0
        while error_count < MAX_ERROR_LIMIT:
            if verb == "get":
                resp = requests.get(url, headers=headers, params=params)
            elif verb == "post":
                resp = requests.post(
                    url, headers=headers, params=params, files=files, json=json
                )
            elif verb == "put":
                resp = requests.put(
                    url, headers=headers, params=params, files=files, json=json
                )
            elif verb == "delete":
                resp = requests.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown verb: {verb}")
            if resp.status_code == 401 and not error_count:
                # retry instantly with new headers
                self.createHeaders()
                error_count += 1
            elif resp.status_code == 401 and error_count:
                # after the first error, try again after a timeout
                time.sleep(5)
                self.createHeaders()
                error_count += 1
            else:
                # on other error codes, print and return
                if not resp.ok:
                    print(
                        {
                            "endpoint": url,
                            "method": verb,
                            "code": resp.status_code,
                            "message": resp.text,
                        },
                        file=sys.stderr,
                    )
                return resp

        raise IOError("Could not contact API correctly after 3 tries.")

    def get(self, url, params=None):
        """
        Pass to self.interact with GET
        """
        return self.interact("get", url, params=params)

    def post(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with POST
        """
        return self.interact("post", url, params=params, json=json, files=files)

    def put(self, url, params=None, json=None, files=None):
        """
        Pass to self.interact with PUT
        """
        return self.interact("put", url, params=params, json=json)

    def delete(self, url, params=None):
        """
        Pass to self.interact with DELETE
        """
        return self.interact("delete", url, params=params)

    def createToken(self, api_version=None):
        """
        Create a temporary (5 minutes) JWT token for authentication

        Args:
            api_version (string): v3, v4

        Returns:
            string: Authentication token that can be used in headers
        """

        if not (self.adminAPIKey and self.contentAPIKey):
            raise ValueError("Please enter a valid admin and content api key!")

        if api_version is None:
            api_version = self.api_version

        DURATION_IN_MINUTES = 5
        id, secret = self.adminAPIKey.split(":")
        iat = int(dt.now().timestamp())
        header = {"alg": "HS256", "typ": "JWT", "kid": id}
        payload = {
            "iat": iat,
            "exp": iat + (DURATION_IN_MINUTES * 60),
            "aud": f"/{api_version}/admin/",
        }
        return jwt.encode(
            payload, bytes.fromhex(secret), algorithm="HS256", headers=header
        )

    def createHeaders(self, api_version=None):
        """
        Create the ghost authentication header

        Args:
            api_version (string): for which API version to create a token

        Returns:
            dict: Authorization header
        """

        return {"Authorization": f"Ghost {self.createToken(api_version)}"}

    # === INTERACTIONS ===

    # generic (members/settings)

    def getMembers(self):
        """
        GET /admin/members

        Returns:
            list: info about all members
        """

        result = self.get("admin/members")
        if not result.ok:
            return {}

        members = result.json().get("members", [])
        for i in members:
            if i["name"] is None:
                i["name"] = ""

        return members

    def getSettings(self):
        """

        GET content/settings

        See Also https://ghost.org/docs/content-api/#settings

        Returns:
            dict: Settings object (or error object)
        """
        result = self.get("content/settings")
        data = result.json()
        if result.ok:
            return data["settings"]

        return data

    # re-used by post and pages:
    def _getAll(self, type, api="admin"):
        """
        Reusable code to get all instances of something (post, page, author, ...)
        Args:
            type (string): which resource to query
            api (string): which API to use (content or admin)

        Returns:
            list: All found objects
        """

        params = {"formats": "html,mobiledoc", "limit": "all", "filter": "slug: -tags"}
        result = self.get(f"{api}/{type}", params=params)
        data = result.json()
        if result.ok:
            return data[type]
        return data

    def _getById(self, id, type, api="admin"):
        """
        Get one specific object by ID

        See Also _getAll

        Args:
            id (string): resource ID
            type (string): which resource to query
            api (string): which API to use (content or admin)

        Returns:
            dict: Found object or error object
        """

        params = {"formats": "html,mobiledoc"}
        result = self.get(f"{api}/{type}/{id}", params=params)
        data = result.json()
        if result.ok:
            posts = data[type]
            return posts[0]  # post = dict with keys: slug,id,uuid,title etc.

        return data

    def _getBySlug(self, slug, type, api="admin"):
        """
        Similar to _getById but using slug instead of ID

        See Also _getAll

        Args:
            slug (string): resource slug
            type (string): which resource to query
            api (string): which API to use (content or admin)

        Returns:
            dict: Found object or error object
        """
        return self._getById(f"slug/{slug}", type, api)

    def _getByFilter(self, filter, type, api="admin"):
        """
        GET all with filter(s), limits and other parameters

        See Also https://ghost.org/docs/content-api/#parameters

        Args:
            filter (dict): parameters to apply
            type (string): which resource to query
            api (string): which API to use (content or admin)

        Returns:
            list: list of relevant objects
        """

        filter["formats"] = "html,mobiledoc"
        result = self.get(f"{api}/{type}", params=filter)
        if result.ok:
            posts = result.json()[
                type
            ]  # posts = list with dicts with keys: slug,id,uuid,title etc.
            if not len(posts):
                posts = []
        else:
            posts = [
                result.json()
            ]  # posts = list with 1 element of dict with key 'errors'

        return posts

    def _create(
            self,
            type,
            title,
            body,
            body_format="html",
            excerpt=None,
            tags=None,
            authors=None,
            status="draft",
            featured=False,
            featured_image=None,
            slug=None,
    ):
        """
        POST request for posts and pages

        See Also _createPayload

        Args:
            type (string): post or page
            slug (string): the object's URL slug

        Returns:
            dict: status (success/error) and json response
        """

        content = self._createPayload(
            authors,
            body,
            body_format,
            excerpt,
            featured,
            featured_image,
            title,
            status,
            tags,
        )

        if slug is not None:
            content["slug"] = slug

        params = {"source": "html"}
        result = self.post(f"admin/{type}", params=params, json={type: [content]})
        if result.ok:
            status = f"success: created (status_code: {result.status_code})"
        else:
            status = f"error: not created (status_code: {result.status_code})"

        return {"status": status, "response": result.json()}

    def _update(
            self,
            type,
            obj,  # needs ID and updated_at
            new_title,
            body,
            body_format="html",
            excerpt=None,
            tags=None,
            authors=None,
            status="draft",
            featured=False,
            featured_image=None,
    ):

        """
        Update works similar to create, but requires an existing object to update

        Args:
            obj (dict): ID and updated_at of an existing object

        See Also _create

        Returns:
            string: success/error status
        """

        content = self._createPayload(
            authors,
            body,
            body_format,
            excerpt,
            featured,
            featured_image,
            new_title,
            status,
            tags,
        )

        content["updated_at"] = obj["updated_at"]

        result = self.put(f"admin/{type}/" + obj["id"], json={type: [content]})

        if result.ok:
            result = f"success: post updated (status_code: {result.status_code})"
        else:
            result = f"error: post not updated (status_code: {result.status_code})"

        return result

    def _createPayload(
            self,
            authors,
            body,
            body_format,
            excerpt,
            featured,
            featured_image,
            title,
            status,
            tags,
    ):
        """
        Create a payload for a POST/PUT post/page request

        See Also https://ghost.org/docs/admin-api/#the-post-object

        Args:
            title (string): the title of the object
            body (string): the content of a object
            body_format (string): 'html','markdown'
            excerpt (string): the excerpt for a post
            tags (list): a list of dictionaries e.g. [{'name':'my new tag', 'description': 'a very new tag'}]
            authors (list): a list of dictionaries e.g. [{'name':'Jacques Bopp', 'slug': 'jacques'}]
            status (string): 'published' or 'draft'
            featured (bool): if the page should be featured
            featured_image (string): the image url (e.g. "content/images/2020/09/featureImage1.jpg" -> see imageUpload()

        Returns:
            dict: payload

        """

        content = {"title": title}
        if body_format == "markdown":
            content["mobiledoc"] = json.dumps(
                {
                    "version": "0.3.1",
                    "markups": [],
                    "atoms": [],
                    "cards": [["markdown", {"cardName": "markdown", "markdown": body}]],
                    "sections": [[10, 0]],
                }
            )
        else:
            content["html"] = body
        if excerpt is not None:
            content["custom_excerpt"] = excerpt
        if tags is not None:
            content["tags"] = tags
        if authors is not None:
            content["authors"] = authors
        content["status"] = status
        content["featured"] = featured
        if featured_image is not None:
            content["feature_image"] = self.url + featured_image

        return content

    def _deleteById(self, type, id):
        """
        Delete some object by ID

        Args:
            type (string): type of resource
            id (string): id to remove

        Returns:
            string: success/error status
        """

        result = self.delete(f"admin/{type}/{id}")
        if result.ok:
            result = f"success: deleted (status_code: {result.status_code})"
        else:
            result = f"error: NOT deleted (status_code: {result.status_code})"

        return result

    # admin/posts

    def getAllPosts(self):
        """
        GET /admin/posts/

        Returns:
            list
        """
        return self._getAll("posts")

    def getPostById(self, id):
        """
        GET /admin/posts/{id}/

        Args:
            id (string)

        Returns:
            dict
        """
        return self._getById(id, "posts")

    def getPostBySlug(self, slug):
        """
        GET /admin/posts/slug/{slug}/

        Args:
            slug (string)

        Returns:
            dict
        """
        return self._getBySlug(slug, "posts")

    def getPostsByFilter(self, filter):
        """
        Get all posts, with parameters

        Args:
            filter (dict):

        Returns:
            list

        """
        return self._getByFilter(filter, "posts")

    def getPostByTitle(self, title, property="title"):
        """
        Get all posts with a specific title (or other property)

        Args:
            title (string): title to match (exactly)
            property (string): which field to match (title by default)

        Returns:
            list: Multiple posts could have the same title
        """

        all_posts = self.getAllPosts()

        return [post for post in all_posts if post[property] == title]

    def createPost(
            self,
            title,
            body,
            body_format="html",
            excerpt=None,
            tags=None,
            authors=None,
            status="draft",
            featured=False,
            featured_image=None,
            slug=None,
    ):
        """
        POST /admin/posts/

        Args:
            title (string): the title of the post
            body (string): the content of a post
            body_format (string): 'html','markdown'
            excerpt (string): the excerpt for a post
            tags (list): a list of dictionaries e.g. [{'name':'my new tag', 'description': 'a very new tag'}]
            authors (list): a list of dictionaries e.g. [{'name':'Jacques Bopp', 'slug': 'jacques'}]
            status (string): 'published' or 'draft'
            featured (bool): if the post should be featured
            featured_image (string): the image url (e.g. "content/images/2020/09/featureImage1.jpg" -> see imageUpload()
            slug (string): [todo]

        Returns:
            string: if the creation was successful or not
        """
        return self._create(
            "posts",
            title,
            body,
            body_format,
            excerpt,
            tags,
            authors,
            status,
            featured,
            featured_image,
            slug,
        )

    def _updatePost(self, *a, **kw):
        """
        Shorthand for _update with posts

        See Also _update
        """
        return self._update("posts", *a, **kw)

    def updatePostByTitle(self, old_title, *a, **kw):
        """
        Get a post by title and update it

        See Also _update
        """

        posts = self.getPostByTitle(old_title)
        if len(posts) > 1:
            return "error: more than 1 post found"
        elif len(posts) == 0:
            return "error: no post found"
        else:
            return self._updatePost(posts[0], *a, **kw)

    def updatePostById(self, id, *a, **kw):
        """
        PUT /admin/posts/{id}/

        Get a post by ID and update it

        Supports the same arguments as createPost - See _update
        """

        post = self.getPostById(id)
        return self._updatePost(post, *a, **kw)

    def deletePostById(self, id):
        """
        DELETE /admin/posts/{id}/

        Args:
            id (string)

        Returns:
            string: success/error status
        """
        return self._deleteById("posts", id)

    # admin/pages

    def getAllPages(self):
        """
        GET /admin/pages/

        Returns:
            list
        """
        return self._getAll("pages")

    def getPageByTitle(self, title, property="title"):
        """
        Get all pages with a specific title (or other property)

        Args:
            title (string): title to match (exactly)
            property (string): which field to match (title by default)

        Returns:
            list: Multiple pages could have the same title
        """

        all_posts = self.getAllPages()

        return [page for page in all_posts if page[property] == title]

    def getPageById(self, id):
        """
        GET /admin/pages/{id}/

        Args:
            id (string)

        Returns:
            dict
        """
        return self._getById(id, "pages")

    def getPageBySlug(self, slug):
        """
        GET /admin/pages/slug/{slug}/

        Args:
            slug (string)

        Returns:
            dict
        """
        return self._getBySlug(slug, "pages")

    def getPagesByFilter(self, filter):
        """
        Get all pages, with parameters

        Args:
            filter (dict):

        Returns:
            list

        """

        return self._getByFilter(filter, "pages")

    def createPage(
            self,
            title,
            body,
            body_format="html",
            excerpt=None,
            tags=None,
            authors=None,
            status="draft",
            featured=False,
            featured_image=None,
            slug=None,
    ):
        """
        POST /admin/pages/

        Args:
            title (string): the title of the page
            body (string): the content of a page
            body_format (string): 'html','markdown'
            excerpt (string): the excerpt for a post
            tags (list): a list of dictionaries e.g. [{'name':'my new tag', 'description': 'a very new tag'}]
            authors (list): a list of dictionaries e.g. [{'name':'Jacques Bopp', 'slug': 'jacques'}]
            status (string): 'published' or 'draft'
            featured (bool): if the page should be featured
            featured_image (string): the image url (e.g. "content/images/2020/09/featureImage1.jpg" -> see imageUpload()
            slug (string): the page's URL slug

        Returns:
            result (string): if the creation was successful or not
        """

        return self._create(
            "pages",
            title,
            body,
            body_format,
            excerpt,
            tags,
            authors,
            status,
            featured,
            featured_image,
            slug,
        )

    def _updatePage(self, *a, **kw):
        """
        Shorthand for _update with pages

        See Also _update
        """
        return self._update("pages", *a, **kw)

    def updatePageById(self, id, *a, **kw):
        """
        PUT /admin/posts/{id}/

        Get a page by ID and update it

        Supports the same arguments as createPage - See _update
        """

        page = self.getPageById(id)
        return self._updatePage(page, *a, **kw)

    def updatePageByTitle(self, old_title, *a, **kw):
        """
        Get a page by title and update it

        See Also _update
        """

        pages = self.getPageByTitle(old_title)
        if len(pages) > 1:
            return "error: more than 1 page found"
        elif len(pages) == 0:
            return "error: no page found"
        else:
            return self._updatePage(pages[0], *a, **kw)

    def deletePageById(self, id):
        """
        DELETE /admin/pages/{id}/

        Args:
            id (string)

        Returns:
            string: success/error status
        """
        return self._deleteById("pages", id)

    # admin/images

    def loadImage(self, image_path_and_name):
        """
        Load an image path as BytesIO, can be used to upload files to ghost

        See Also imageUpload

        Args:
            image_path_and_name (string): path to file to load

        Returns:

        """
        with open(image_path_and_name, "rb") as image:
            return BytesIO(image.read())

    def imageUpload(self, image_name, image_obj):
        """
        POST /admin/images/upload/

        Upload an image to ghost

        Args:
            image_name (str): name to upload
            image_obj (BinaryIO): file-like object to upload (-> loadImage)

        Returns:
            string: success/error status

        See Also loadImage
        """

        # todo: support other filetypes than image/jpeg

        files = {"file": (image_name, image_obj, "image/jpeg")}
        params = {
            "purpose": "image",
            "ref": image_name,
        }  # 'image', 'profile_image', 'icon'
        result = self.post("admin/images/upload", files=files, params=params)
        if result.ok:
            result = "success: " + result.json()["images"][0]["url"]
        else:
            result = f"error: upload failed ({result.status_code})"

        return result

    # content/authors
    def getAllAuthors(self):
        """
        GET /content/authors/

        Returns
            list: all authors
        """

        return self._getAll("authors", api="content")

    def getAuthorById(self, id):
        """
        GET /content/authors/{id}/

        Returns:
            dict: specific author by id
        """
        return self._getById(id, "authors", "content")

    def getAuthorBySlug(self, slug):
        """
        GET /content/authors/slug/{slug}/

        Returns:
            dict: specific author by slug
        """
        return self._getBySlug(slug, "authors", "content")

    def getAuthorByName(self, name, property="name"):
        """
        Find author(s) by name or other property

        Args:
            name (string): value to look for
            property (string): key to look in

        Returns:
            list
        """

        all_authors = self.getAllAuthors()
        return [author for author in all_authors if author[property] == name]

    def getAuthorsByFilter(self, filter):
        """
       Get all authors, with parameters

        Args:
            filter (dict):

        Returns:
            list
        """
        return self._getByFilter(filter, "authors", "content")

    # admin/themes
    def getThemes(self):
        """
        Canary feature to find all themes on the blog

        Raises
            NotImplementedError since ghost does not support this yet

        Returns:
            list
        """

        raise NotImplementedError("GET themes is not supported by ghost yet.")
        return self.interact("get", "admin/themes", api_version="canary").json()

    def createThemeZip(self, folder):
        """
        Zip a folder

        Args:
            folder (string): which folder contains the ghost theme files

        Returns:
            Path: to zip
        """
        archive = Path(f"{folder}.zip")
        shutil.make_archive(str(archive).replace(".zip", ""), "zip", folder)

        return archive

    def uploadThemeZip(self, file):
        """
        Upload a theme zip

        Args:
            file (Path): pathlib to zip file

        Returns:
            dict: theme info
        """

        with file.open("rb") as zip:
            resp = self.post(
                "admin/themes/upload",
                files={"file": (file.name, zip, "application/zip")},
            )
            data = resp.json()
            if resp.ok:
                return data["themes"][0]
            return data

    def uploadTheme(self, file_or_folder):
        """
        Upload a theme folder or zip

        Args:
            file_or_folder (string): path

        Returns:
            dict: theme info
        """

        path = Path(file_or_folder)

        if path.is_file():
            return self.uploadThemeZip(path)
        elif path.exists():
            # -> is folder
            file = self.createThemeZip(file_or_folder)

            return self.uploadThemeZip(file)
        else:
            raise FileNotFoundError(file_or_folder)

    def activateTheme(self, name):
        """
        PUT /admin/themes/{name}/activate

        Activate a theme

        Args:
            name (string): theme to activate

        Returns:
            dict: theme info
        """
        resp = self.put(f"admin/themes/{name}/activate")
        data = resp.json()
        if resp.ok:
            return data["themes"][0]
        return data

    # admin/site
    def getSite(self):
        """
        Get basic info about the site

        See Also https://ghost.org/docs/admin-api/#site

        Returns:
            dict:
        """

        return self.get("admin/site").json()["site"]

    # webhooks

    def createWebhook(self, *a, **kw):
        """
        POST /admin/webhooks/

        See Also https://ghost.org/docs/admin-api/#the-webhook-object
        """
        # todo
        raise NotImplementedError()

    def updateWebhook(self, id, *a, **kw):
        """
        PUT /admin/webhooks/{id}/

        Args:
            id (string): Webhook to update

        """
        # todo
        raise NotImplementedError()

    def deleteWebhook(self, id):
        """
        DELETE /admin/webhooks/{id}/

        Args:
            id (string): Webhook to delete
        """
        # todo
        raise NotImplementedError()

    # tags
    def getAllTags(self):
        """
        GET /content/tags/

        Returns
            list: all tags
        """
        return self._getAll("tags", "content")

    def getTagById(self, id):
        """
        GET /content/tags/{id}/

        Returns:
            dict: specific tag by id
        """
        return self._getById(id, "tags", "content")

    def getTagBySlug(self, slug):
        """
        GET /content/tags/slug/{slug}/

        Returns:
            dict: specific tag by slug
        """
        return self._getBySlug(slug, "tags", "content")

    def getTagByName(self, name, property="name"):
        """
        Find tag(s) by name or other property

        Args:
            name (string): value to look for
            property (string): key to look in

        Returns:
            list
        """

        all_tags = self.getAllTags()

        return [tag for tag in all_tags if tag[property] == name]

    def getTagsByFilter(self, filter):
        """
        Get all tags, with parameters

        Args:
            filter (dict):

        Returns:
            list
        """
        return self._getByFilter(filter, "tags", "content")


def demo():
    # ga = GhostAdmin('somedomain1')
    ga = GhostAdmin(
        "https://some.domain.tld",
        adminAPIKey=".....",
        contentAPIKey="...",
    )
    members = ga.getMembers()
    settings = ga.getSettings()
    post = ga.getPostById("5f...5c")
    post = ga.getPostBySlug("new-post")
    posts = ga.getPostsByFilter({"filter": "featured:true"})
    posts = ga.getPostsByFilter({"limit": "all", "filter": "slug: -tags"})
    posts = ga.getAllPosts()
    posts = ga.getPostByTitle("New Post")
    result = ga.deletePostById("0c...f")
    image = ga.loadImage("c:/tmp/image1")
    result = ga.imageUpload("featureImage1.jpg", image)
    # create post ---------------------------------------
    title = "new post x"
    body = """<div>Lorem ipsum dolor sit amet, ...</div>"""
    excerpt = "this post is about ..."
    tags = [{"name": "my new tag x", "description": "a new tag"}]
    authors = [{"name": "Jacques Bopp", "slug": "jacques"}]
    featured_image = "content/images/2020/09/featureImage1.jpg"
    slug = "my-new-postx"
    result = ga.createPost(
        title,
        body,
        body_format="html",
        excerpt=excerpt,
        tags=tags,
        authors=authors,
        status="draft",
        featured=False,
        featured_image=featured_image,
    )
    # update post ---------------------------------------
    old_title = "new post x"
    new_title = "updated post x"
    body = """<div>Lorem ipsum  ...</div>"""
    excerpt = "this post is about an update ..."
    tags = [
        {"name": "my new tag", "description": "a new tag"},
        {"name": "my second new tag", "description": "a second new tag"},
    ]
    authors = [
        {"name": "Jacques Bopp", "slug": "jacques"},
        {"name": "Ghost", "slug": "ghost"},
    ]
    featured_image = "content/images/2020/09/featureImage2.jpg"
    result = ga.updatePostByTitle(
        old_title,
        new_title,
        body,
        body_format="html",
        excerpt=excerpt,
        tags=tags,
        authors=authors,
        status="draft",
        featured=False,
        featured_image=featured_image,
    )


if __name__ == "__main__":
    # demo()
    test()
