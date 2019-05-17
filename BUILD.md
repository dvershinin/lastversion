## Build instructions

Since I'm not exactly a Python guy, I write down stuff here for log of how the build environment is set in CentOS 7.

```
git clone ... lastversion && cd lastversion

# we need a virtualenv for latest pip, setuptools or things will choke on Markdown description
virtualenv venv

# activate the virtualenv
. venv/bin/activate

# update pip
pip install -U pip setuptools twine

# create source distribution
python setup.py sdist

# upload to test PyPi
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# uptload to the real thing
twine upload dist/*
```

