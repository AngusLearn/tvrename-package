# setup.py
from setuptools import setup, find_packages

setup(
    name='tvrename',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tvrename = tvrename.main:main',
        ],
    },
    install_requires=[
        'requests', 
        'python-dotenv',
        'colorama',
        'configparser',
    ],
    author='Angus Learn',
    author_email='angus.learn@gmail.com',
    description='A command-line tool to rename and organize TV series files.',
    url='https://github.com/AngusLearn/tvrename-package',
)
