from setuptools import setup, find_packages

setup(name="bean_importers",
      version=0.2,
      packages=find_packages(),
      install_requires=[
          "avanza-api>=13.0.0",
          "click>=8.1.7",
          "python-dotenv>=1.0.1",
          "nordigen>=1.4.1",
          "beangulp",
          "beancount"
      ],
      entry_points={
          "console_scripts":[
              "avanza_download = bean_importers.avanza_downloader:main",
              "nordigen_download = bean_importers.nordigen_downloader:main",
          ]
      }

)