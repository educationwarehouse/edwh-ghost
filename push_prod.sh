rm dist/ -r
python -m build
twine upload dist/*