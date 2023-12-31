test:
	pytest -v -n auto

publish: clean
	python setup.py sdist bdist_wheel
	twine upload -s dist/*

clean:
	rm -rf *.egg-info *.egg dist build .pytest_cache

one-file:
	pyinstaller --onefile src/lastversion/__main__.py --name lastversion

.PHONY: test publish clean
