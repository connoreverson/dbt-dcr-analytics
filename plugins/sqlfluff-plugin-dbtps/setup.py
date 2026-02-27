from setuptools import setup, find_packages

setup(
    name="sqlfluff-plugin-dbtps",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["sqlfluff>=2.0.0"],
    entry_points={
        "sqlfluff": ["sqlfluff_plugin_dbtps = sqlfluff_plugin_dbtps.rules"]
    },
)
