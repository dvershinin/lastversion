test:
	@if [ -f ~/.secrets ]; then \
		echo "Sourcing ~/.secrets..."; \
		. ~/.secrets; \
	fi; \
	if [ -z "$$GITHUB_API_TOKEN" ]; then \
		echo "Error: GITHUB_API_TOKEN is not set. Please set it in ~/.secrets or environment."; \
		exit 1; \
	fi; \
	if [ -f ${HOME}/.virtualenvs/lastversion/bin/python ]; then \
		source ${HOME}/.virtualenvs/lastversion/bin/activate; \
	fi; \
	timeout 600 python -m pytest -v -n auto

publish: clean
	python setup.py sdist bdist_wheel
	twine upload -s dist/*

clean:
	rm -rf *.egg-info *.egg dist build .pytest_cache

one-file:
	pyinstaller --onefile src/lastversion/__main__.py --name lastversion

.PHONY: test publish clean
