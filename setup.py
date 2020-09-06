from setuptools import find_packages, setup

setup(
    author = 'Patrick Gillan',
    author_email = "pgillan@minorimpact.com",
    description = 'Command line zettelkasten browser/editor.',
    entry_points = { "console_scripts": [ "zlink = zlink.zlink:main" ] },
    install_requires = ["minorimpact"],
    license = 'GPLv3',
    name = 'zlink',
    packages = find_packages(),
    py_modules = ["zlink"],
    #scripts=['zlink'],
    setup_requires = [],
    tests_require = [],
    url = "https://github.com/pgillan145/zlink",
    version = '0.0.5'
)
