from setuptools import find_packages, setup

setup(
    name="doodle_agent",
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    install_requires=["setuptools"],
    zip_safe=True,
    author="Rohan",
    author_email="myemail.rohan@gmail.com",
    description="DoodleMe AI agent — Claude-powered robot design tools",
    license="MIT",
)
