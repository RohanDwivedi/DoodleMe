from setuptools import find_packages, setup

setup(
    name="rqt_doodle",
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    install_requires=["setuptools"],
    zip_safe=True,
    author="Rohan",
    author_email="myemail.rohan@gmail.com",
    description="DoodleMe rqt plugin — AI-assisted robot design",
    license="MIT",
)
