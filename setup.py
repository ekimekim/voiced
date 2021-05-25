from setuptools import setup, find_packages

setup(
	name='voiced',
	version='0.0.1',
	author='Mike Lang',
	author_email='mikelang3000@gmail.com',
	description='Voice-activated command system',
	packages=find_packages(),
	install_requires=[
		'argh',
		'gevent',
	],
)
