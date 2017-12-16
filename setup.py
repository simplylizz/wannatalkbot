import setuptools


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

    install_requires=[
        "pymongo==3.5.1",
        "python-telegram-bot==9.0.0",
    ],

    zip_safe=False,

    entry_points={
        'console_scripts': [
            'wtb-bot = wtb.frontend:main',
            'wtb-matchmaker = wtb.matchmaker:main',
        ],
    },
)
