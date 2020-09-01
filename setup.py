from setuptools import find_packages, setup

setup(
    name='zlink',
    packages=find_packages(),
    scripts=['zlink'],
    version='0.0.2',
    description='Commandline zettelkasten browser, editor.',
    author='Patrick Gillan',
    license='GPLv3',
    install_requires=["minorimpact","pyperclip"],
    setup_requires=[],
    tests_require=[],
)
