import os

import setuptools


requirements_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "requirements.txt",
)
with open(requirements_path) as requirements_txt:
    requirements = filter(None, (r.strip() for in requirements_txt))


setuptools.setup(
    version="0.0.1",

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
            'wtb-matchmaker = wtb.matchmaker:main',
        ],
    },
)
