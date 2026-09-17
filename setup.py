from setuptools import setup, find_packages

setup(
    name="amd-control-center",
    version="1.1.0",
    description="AMD Radeon Software Adrenalin Edition for Linux",
    author="Julian",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "amd-control-center = amd_control_center.app:main",
        ],
    },
    install_requires=[
        "PyQt6>=6.4.0",
    ],
    python_requires=">=3.8",
)
