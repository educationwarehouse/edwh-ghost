# coverage run -m pytest -s

import os
import tempfile

import pytest
import requests
from dotenv import load_dotenv
from faker import Faker

from src.ghost import SUPPORTED_VERSIONS, GhostAdmin
from src.ghost.client import GhostContent
from src.ghost.exceptions import *
from src.ghost.resources import *
from src.ghost.results import GhostResult, GhostResultSet


def load_config():
    load_dotenv()
    return dict(os.environ)


@pytest.fixture(scope="module", params=SUPPORTED_VERSIONS)
def ghost(request):
    version = request.param
    config = load_config()

    return GhostAdmin(
        config["GHOST_SITE"],
        adminAPIKey=config["GHOST_ADMIN_KEY"],
        contentAPIKey=config["GHOST_CONTENT_KEY"],
        api_version=version,
    )


def ghost_content(version):
    config = load_config()

    return GhostContent(
        config["GHOST_SITE"],
        contentAPIKey=config["GHOST_CONTENT_KEY"],
        api_version=version,  # works like a train
    )


@pytest.fixture
def faker():
    return Faker()


# decorator to skip a test
def disable(_):
    return None


def _delete_all(ghost):
    assert all(ghost.posts.delete())
    assert all(ghost.pages.delete())
    assert all(ghost.tags.delete())
    with pytest.raises(NotImplementedError):
        # authors should not have a .delete()
        # as it is a Content API
        ghost.authors.delete()

    assert not ghost.posts()
    assert not ghost.pages()
    assert not ghost.tags()


def test_0_delete_old(ghost):
    _delete_all(ghost)


# @disable
def test_1_posts(ghost, faker):
    posts: PostResource = ghost.posts

    posts.delete()

    posts.create(
        title="My First Post",
        slug="first",
    )

    content = faker.sentences(nb=5)

    _third = {
        "title": faker.sentence(),
        "slug": "third",
        "status": "published",
        "authors": [{"slug": "ghost"}],
        "tags": [{"name": "pytest-created", "description": f"Posts created by Ghost API"}],
        "html": "".join([f"<p>{_}</p>" for _ in content]),
        "excerpt": content[0],
        "featured": False,
    }

    # POST /admin/posts/
    posts.create(
        {
            "title": faker.sentence(),
            "slug": "second",
        },
        _third,
    )

    # GET /admin/posts/
    all_posts = list(posts.paginate())
    assert len(all_posts) == 3

    unpublished_posts = posts.get(status="draft")
    assert len(unpublished_posts) == 2

    unpublished_post = posts.get(status="draft", limit=1)
    assert len(unpublished_post) == 1

    published_posts: GhostResultSet = posts.get(status="published")
    assert len(published_posts) == 1

    assert published_posts[0].title == _third["title"]

    # GET /admin/posts/slug/{slug}/
    assert ghost.post(slug="second").title
    assert not ghost.post(slug="second", fields=["id"]).title
    assert not ghost.post(slug="second").unknown

    posts.delete(status="draft")

    assert len(posts()) == 1

    # PUT /admin/posts/{id}/
    assert all(published_posts.update(title=faker.sentence()))

    new_third = ghost.post(slug="third")
    assert new_third.title != _third["title"]

    # DELETE /admin/posts/{id}/
    new_third.delete()

    assert not posts(limit=1)

    # re-create POST 3 to be used for authors:

    temp = tempfile.TemporaryFile().name
    img_path = f"{temp}.png"
    _download_random_image(img_path)

    url = ghost.images.upload(img_path, "third.png")
    _third["feature_image"] = url

    posts.create(_third)

    # posts.create(
    #     {
    #         "title": "With Markdown",
    #         "slug": "md",
    #         "markdown": ["# This is Markdown", "_with_ **multiple** paragraphs"],
    #         "tags": ["is-markdown", "pytest-created"],
    #     }
    # )
    #
    # markdown_post = ghost.post(slug="md")
    # print(markdown_post.as_dict())


# @disable
def test_2_pages(ghost, faker):
    pages: PageResource = ghost.pages

    # GET /admin/pages/
    assert not pages()

    # POST /admin/pages/
    pages.create(
        {"title": "My First Page", "slug": "first", "tags": ["page"]},
        {"title": "My Second Page", "slug": "second", "tags": ["not-page"]},
    )

    assert len(pages()) == 2

    # GET /admin/pages/slug/{slug}/
    first_by_slug = ghost.page(slug="first")
    second_by_slug = ghost.page(slug="second")
    # GET /admin/pages/{id}/
    second_by_id = ghost.page(second_by_slug["id"])

    assert second_by_slug == second_by_id

    assert second_by_slug != first_by_slug

    assert len(pages(tags="page")) == 1

    # PUT /admin/pages/{id}/
    second_by_slug.update(tags=["page", "meta-page"])

    assert len(pages(tags="page")) == 2
    assert len(pages.delete(tags="meta-page")) == 1

    # DELETE /admin/pages/{id}/
    first_by_slug.delete()

    assert not pages()


# @disable
def test_3_tags(ghost, faker):
    tags: TagResource = ghost.tags

    tags.delete()

    assert not tags()
    try:
        assert not ghost.tag()
    except GhostResourceNotFoundException as e:
        assert e.error_type == "Resource Not Found"

    tags.create({"name": "tag1"}, {"name": "tag2"}, {"name": "tag3"})

    tag1 = tags(name="tag1")
    tag1.delete()

    assert len(tags()) == 2

    tag2 = ghost.tag(name="tag2")
    tag2.update(name="tag1-and-tag2")

    assert "-and-".join([t["name"] for t in tags()]) == "tag1-and-tag2-and-tag3"

    # DELETE /admin/tags/{id}/
    tag2.delete()

    tag3_by_id = ghost.tag(tags(name="tag3")[0].id)
    assert ghost.tag().name == tag3_by_id.name


# @disable
def test_4_authors(ghost, faker):
    authors: AuthorResource = ghost.authors

    assert len(authors()) == 1, "'Ghost' should be the only author (at this point)"

    ghost_author = ghost.author(slug="ghost-user")
    assert ghost_author.name == "Ghost"

    assert ghost.author(ghost_author.id) == ghost_author


@disable  # Tiers API does not appear to be working right now, same for offers
def test_5_tiers(ghost, faker):
    tiers: GhostAdminResource = ghost.resource("tiers")

    tiers.delete()

    tiers.create(name="My First Tier")

    print(tiers())


def _download_random_image(path="./temp.png"):
    """
    It downloads a random image from the internet and saves it to a file

    Args:
      path (str): The path to save the image to. Defaults to ./temp.png
    """
    url = "https://picsum.photos/300/300"

    resp = requests.get(url, stream=True)
    with open(path, "wb") as f:
        f.write(resp.content)


# @disable
def test_6_images(ghost, faker):
    images: ImageResource = ghost.images

    temp = tempfile.TemporaryFile().name
    img_path = f"{temp}.jpg"
    _download_random_image(img_path)

    assert images.upload(img_path)

    try:
        assert not images.upload("doesnt-exist")
    except FileNotFoundError:
        assert True


def _download_boilerplate_theme(path="./temp.zip"):
    URL = "https://github.com/TryGhost/Starter/archive/refs/heads/main.zip"
    resp = requests.get(URL, stream=True)
    with open(path, "wb") as f:
        f.write(resp.content)


# @disable
def test_7_themes(ghost, faker):
    if ghost.site()["version"] > "5.0":
        # the ghost boilerplate theme is currently not compatible with ghost 5
        return

    themes: ThemeResource = ghost.themes

    temp = tempfile.TemporaryFile().name

    fake_zip_path = f"{temp}.zip"
    _download_random_image(fake_zip_path)

    try:
        assert not themes.upload(fake_zip_path)
    except GhostResponseException as e:
        assert e.error_type == "ValidationError"

    try:
        assert not themes.upload("doesnt-exist")
    except FileNotFoundError:
        assert True

    zip_path = "./boilerplate.zip"
    _download_boilerplate_theme(zip_path)

    name = themes.upload(zip_path)
    os.remove(zip_path)
    assert name

    assert themes.activate(name) == name

    try:
        themes.activate("doesnt-exist")
    except GhostResponseException as e:
        assert e.error_type == "ValidationError"

    # default:
    themes.activate("casper")


# @disable
def test_8_site_and_settings(ghost, faker):
    site: GhostResult = ghost.site()
    settings: GhostResult = ghost.settings()

    assert site["title"] == settings["title"]


# @disable
def test_9_members(ghost, faker):
    members: MemberResource = ghost.members

    members.delete()

    assert not members()

    members.create(
        {
            "email": faker.email(),
        },
        {
            "email": faker.email(),
        },
    )

    m = members()
    assert len(m) == 2

    name1 = faker.first_name()

    m1 = m[0]
    m1.update(name=name1)

    assert set([m["name"] for m in members.get(fields=["name"])]) == {name1, None}

    first_member = members(name=name1)
    assert len(first_member) == 1

    first_member.delete()

    assert len(members()) == 1

    members.delete()

    assert not members()


# @disable
def test_10_ghost_content(ghost):
    # use ghost only to parameterize version (v3,v4,v5)
    ghost = ghost_content(ghost.api_version)

    posts = ghost.posts()
    post_id = posts[0]["id"]

    with pytest.raises(GhostWrongApiError):
        ghost.posts.delete(post_id)

    with pytest.raises(GhostWrongApiError):
        ghost.post.delete(post_id)

    with pytest.raises(GhostWrongApiError):
        ghost.posts.update(post_id, {"title": "Illegal"})

    with pytest.raises(GhostWrongApiError):
        ghost.post.update(post_id, {"title": "Illegal"})

    with pytest.raises(GhostWrongApiError):
        ghost.posts.create({"title": "Illegal"})

    with pytest.raises(GhostWrongApiError):
        ghost.post.create({"title": "Illegal"})


# @disable
def test_11_ghost_paginate(ghost, faker):
    posts: PostResource = ghost.posts

    posts.delete()  # clean before

    # create 20 posts
    posts.create(
        *[
            {
                "title": faker.sentence(),
                "authors": [{"slug": "ghost"}],
                "tags": ["even" if _ % 2 else "odd"],
            }
            for _ in range(13)
        ]
    )

    # default pagination

    assert len(posts(limit="all")) == 13

    page1 = posts(limit=5)

    assert len(page1) == 5

    page2 = page1.next()

    assert len(page2) == 5

    page3 = page2.next()

    assert len(page3) == 3  # 13 posts

    # filtered pagination

    assert len(posts(tag="even")) == 6

    page1 = posts(tag="even", limit=4)

    assert len(page1) == 4

    page2 = page1.next()

    assert len(page2) == 2

    page3 = page2.next()

    assert not page3

    # with .paginate and filters:

    n = 0
    for even in posts.paginate(tag="even"):
        assert "even" in even.tags
        n += 1

    assert n == 6


# @disable
def test_12_users(ghost, faker):
    users = ghost.users()
    assert len(users), "No users found"

    user: GhostResult = users[0]

    assert user.as_dict()["id"], "user should have an ID"

    assert not (any(users.delete()) or any(ghost.users.delete())), "Users should not be deletable"
    assert user.delete() == False, "User should not be deletable"

    with pytest.raises(GhostResponseException):
        # not allowed
        users.update(slug="new-slug")
        user.update(slug="new-slug")


def test_13_users_content(ghost, faker):
    ghost = ghost_content(ghost.api_version)

    with pytest.raises(GhostResponseException):
        # should throw 404
        ghost.users()


def test_14_resultset_or(ghost):
    posts: PostResource = ghost.posts
    pages: PageResource = ghost.pages

    posts.create(
        {"title": "Test 14 pt 1", "tags": ["part-1"]},
        {"title": "Test 14 pt 2", "tags": ["part-2"]},
    )

    with pytest.raises(TypeError):
        posts.get() | pages.get()

    assert len(posts.get(tag="part-1") | posts.get(tag="part-2")) == 2


# @disable
def test_100_delete_new(ghost):
    _delete_all(ghost)
