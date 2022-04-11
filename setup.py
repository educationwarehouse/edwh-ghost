from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="edwh-ghost",
    version="0.1.0",
    description="Python client for Ghost API v3/v4",
    url="http://github.com/educationwarehouse/edwh-ghost",
    author="Education Warehouse",
    author_email="remco.b@educationwarehouse.nl",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=["ghost"],
    zip_safe=False,
    install_requires=["attrs==21.4.0", "PyJWT==2.3.0", "requests==2.27.1"],
    extras_require={"dev": ["black==22.3.0"]},
)
