# setup.py
from setuptools import setup, find_packages

setup(
    name='tvrename',
    version='0.1.0',  # Or your preferred version
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tvrename = tvrename.main:main',  # Corrected
        ],
    },
    install_requires=[
        'requests',        # Add any dependencies here,
        'python-dotenv',
        'colorama',
        'configparser',
    ],
    # Metadata (optional)
    author='Angus Leung',
    author_email='angus.learn@gmail.com',
    description='A script to rename and organize TV series files.',
    #url='https://github.com/yourusername/tvrename',  # Replace with your repo URL
)
