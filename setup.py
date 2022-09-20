from setuptools import setup
import os

print(
    os.path.join(os.getcwd(), "requirements.txt"),
    os.listdir(),
    "requirements.txt" in os.listdir(),
)

with open(os.path.join(os.getcwd(), "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

# pip-compile requirements.in -> requirements.txt
with open(os.path.join(os.getcwd(), "requirements.txt")) as f:
    required = f.read().splitlines()

# pip-compile requirements-dev.in -> requirements-dev.txt
with open(os.path.join(os.getcwd(), "requirements-dev.txt")) as f:
    dev_required = f.read().splitlines()

setup(
    name="edwh-ghost",
    version="0.1.9",
    description="Python client for Ghost API v3/v4/v5",
    url="https://github.com/educationwarehouse/edwh-ghost",
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
