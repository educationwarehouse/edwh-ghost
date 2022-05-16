# coverage run -m pytest -s

import os

import pytest
import tempfile
import requests

from dotenv import dotenv_values
from faker import Faker

from ghost import GhostAdmin
from ghost.client import GhostContent
from ghost.exceptions import *
from ghost.resources import (
    GhostAdminResource,
    PostResource,
    TagResource,
    AuthorResource,
    PageResource,
    ImageResource,
    ThemeResource,
    MemberResource,
)
from ghost.results import GhostResult, GhostResultSet


@pytest.fixture
def ghost():
    config = dotenv_values(".env")

    return GhostAdmin(
        config["GHOST_SITE"],
        adminAPIKey=config["GHOST_ADMIN_KEY"],
        contentAPIKey=config["GHOST_CONTENT_KEY"],
        api_version="v4",  # works like a train
    )


def ghost_content():
    config = dotenv_values(".env")

    return GhostContent(
        config["GHOST_SITE"],
        contentAPIKey=config["GHOST_CONTENT_KEY"],
        api_version="v4",  # works like a train
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
    with pytest.raises(AttributeError):
        # authors should not have a .delete()
        # as it is a Content API
        assert not any(ghost.authors.delete())


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

    author_first = faker.first_name()
    author_last = faker.last_name()
    author_full = f"{author_first} {author_last}"

    content = faker.sentences(nb=5)

    _third = {
        "title": faker.sentence(),
        "slug": "third",
        "status": "published",
        "authors": [{"slug": "ghost"}],
        "tags": [
            {"name": "pytest-created", "description": f"Posts created by Ghost API"}
        ],
        "html": "".join([f"<p>{_}</p>" for _ in content]),
        "excerpt": content[0],
        "featured": False,
        "feature_image": "content/images/2020/09/featureImage1.jpg",
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

    ghost_author = ghost.author(slug="ghost")
    assert ghost_author.name == "Ghost"

    assert ghost.author(ghost_author.id) == ghost_author


@disable
def test_5_tiers(ghost, faker):
    return "Tiers API does not appear to be working right now"

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
    URL = "https://source.unsplash.com/300x300"

    resp = requests.get(URL, stream=True)
    with open(path, "wb") as f:
        f.write(resp.content)


# @disable
def test_6_images(ghost, faker):
    images: ImageResource = ghost.images

    img_path = tempfile.TemporaryFile().name + ".jpg"
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
    themes: ThemeResource = ghost.themes

    fake_zip_path = tempfile.TemporaryFile().name + ".zip"
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
    assert name
    os.remove(zip_path)

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


def test_10_ghost_content():
    ghost = ghost_content()

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
def test_100_delete_new(ghost):
    _delete_all(ghost)
