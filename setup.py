from setuptools import setup, find_packages

setup(name="bean_importers",
      version=0.10,
      packages=find_packages(),
      install_requires=[
          "avanza-api>=15.0.0",
          "click>=8.1.7",
          "python-dotenv>=1.0.1",
          "nordigen>=1.4.1",
          "beangulp>=0.2.0",
          "beancount>=3.1",
          "undetected-chromedriver>=3.1.5",
          "selenium>=4.11.2",
          "xvfbwrapper>=0.2.9",

      ],
      entry_points={
          "console_scripts":[
              "avanza_download = bean_importers.avanza_downloader:main",
              "nordigen_download = bean_importers.nordigen_downloader:main",
              "amex_download = bean_importers.amex_downloader:main",
          ]
      }

)