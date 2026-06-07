from setuptools import setup

setup(
    name='webcapture',
    version='2.0.0',
    description='CLI client for the website-capture backend',
    py_modules=['webcapture'],
    python_requires='>=3.8',
    install_requires=['requests>=2.31.0'],
    entry_points={
        'console_scripts': [
            'webcapture=webcapture:main',
        ],
    },
)
