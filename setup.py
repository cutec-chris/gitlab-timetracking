from setuptools import setup
with open("README.md", 'r') as f:
    long_description = f.read()

setup(name='gitlab-timetracking',
      version='0.0.1',
      description='simple timetracking commandline application that uses the Gitlab api to get / store times in gitlab directly in the project/repository',
      long_description=long_description,
      url='https://github.com/cutec-chris/gitlab-timetracking',
      author='Christian Ulrich',
      author_email='pypi@chris.ullihome.de',
      license='MIT',
      python_requires='>=3.6',
      packages=['gitlab_timetracking'],
      scripts=['bin/tt'],
      zip_safe=False,
      include_package_data=True,
      install_requires=['python-gitlab','timesheet-gitlab']
      )