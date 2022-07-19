rm dist/*
python -m build
twine upload --repository testpypi dist/*