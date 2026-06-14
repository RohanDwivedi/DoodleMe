from setuptools import find_packages, setup

package_name = "rqt_doodle"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml", "plugin.xml"]),
        (
            f"share/{package_name}/assets/themes",
            ["rqt_doodle/assets/themes/dark.qss"],
        ),
        (
            f"share/{package_name}/assets/icons",
            [
                "rqt_doodle/assets/icons/logo.svg",
                "rqt_doodle/assets/icons/chat.svg",
                "rqt_doodle/assets/icons/viewer.svg",
                "rqt_doodle/assets/icons/bom.svg",
                "rqt_doodle/assets/icons/wiring.svg",
                "rqt_doodle/assets/icons/send.svg",
                "rqt_doodle/assets/icons/export.svg",
                "rqt_doodle/assets/icons/simulate.svg",
                "rqt_doodle/assets/icons/settings.svg",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    author="Rohan",
    author_email="myemail.rohan@gmail.com",
    description="DoodleMe rqt plugin — AI-assisted robot design",
    license="MIT",
    entry_points={
        "console_scripts": [],
    },
)
