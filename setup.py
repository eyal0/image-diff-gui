"""Install image-diff-gui."""

from setuptools import setup, find_packages

with open('README.md') as f:
  readme = f.read()

setup(
    name='image-diff-gui',
    version='1.0',
    description='Graphically compare two images',
    author='eyal0',
    author_email='109809+eyal0@users.noreply.github.com',
    long_description=readme,
    url='https://github.com/eyal0/image-diff-gui',
    packages=find_packages(exclude=('tests', 'docs')),
    entry_points = {
      'console_scripts': [
        'image-diff-gui = image_diff_gui:main',
      ],
    },
)
