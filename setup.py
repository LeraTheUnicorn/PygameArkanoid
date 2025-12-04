from setuptools import setup, find_packages

setup(
    name="arkanoid-game",
    version="2.1.5",
    description="Игра Арканоид",
    author="Developer",
    author_email="dadbarn@gmail.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pygame>=2.5.2",
        "numpy>=2.1.0",
    ],
    entry_points={
        'console_scripts': [
            'arkanoid=PyGameBall:main',
        ],
    },
)