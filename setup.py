import os

import setuptools


requirements_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "requirements.txt",
)
with open(requirements_path) as requirements_txt:
    requirements = [r.strip() for r in requirements_txt if r.strip()]

setuptools.setup(
    version="1.2.2",

    name="WannaTalkBot",
    author="Anton Yanchenko",
    author_email="simplylizz@gmail.com",

    packages=setuptools.find_packages(),
    package_data={
        "wtb": [
            "wtb/language-codes.csv",
        ],
    },
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,

    entry_points={
        'console_scripts': [
            'wtb-bot = wtb.frontend:main',
        ],
    },
)
