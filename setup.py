import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="memory",  # Replace with your own username
    version="1.0.0",
    author="zhenghaohui",
    author_email="zhenghaohui.cn@gmail.com",
    description="A small tool help you to easily architect this beautiful world ;)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zhenghaohui/memory",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
