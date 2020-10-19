test:
	pytest -v -n auto

publish: clean
	python setup.py sdist bdist_wheel
	twine upload -s dist/*

clean:
	rm -rf *.egg-info *.egg dist build .pytest_cache

onefile:
	pyinstaller --onefile cli.py
	mv dist/cli dist/lastversion

.PHONY: test publish clean