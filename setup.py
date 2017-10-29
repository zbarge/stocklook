from setuptools import setup, find_packages

version = '1.0'

with open('README.md') as readme_file:
    readme = readme_file.read()

# requirements
install_requires = set(x.strip() for x in open('requirements.txt'))

# dependency links
dependency_links = []


setup(
    name="stocklook",
    packages=find_packages("."),
    description='Cryptocurrency and stock exchange analysis toolkit',
    long_description=readme,
    url='https://github.com/zbarge/stocklook/',
    install_requires=install_requires,
    tests_require=[],
    dependency_links=dependency_links,
    setup_requires=[
        #    'pytest-runner==2.7'
    ],
    version=version,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
    ],
)