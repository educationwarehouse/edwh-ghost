from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# pip-compile requirements.in -> requirements.txt
with open("requirements.txt") as f:
    required = f.read().splitlines()

# pip-compile requirements-dev.in -> requirements-dev.txt
with open("requirements-dev.txt") as f:
    dev_required = f.read().splitlines()

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
    python_requires=">=3.7",
    install_requires=required,
    extras_require={"dev": dev_required},
)
