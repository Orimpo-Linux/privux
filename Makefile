.PHONY: test deb clean

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

# Needs: build-essential debhelper dh-python pybuild-plugin-pyproject python3-setuptools
deb:
	dpkg-buildpackage -us -uc -b

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pybuild debian/.debhelper debian/privux-cli debian/privux-desktop debian/files debian/*.substvars debian/*.log debian/debhelper-build-stamp
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
