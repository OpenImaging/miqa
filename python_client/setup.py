from setuptools import setup

with open('README.md', 'r') as readMeFile:

    setup(
        name='miqa_python_client',
        version='0.1.2',
        description='A python library for interacting with a MIQA API',
        long_description_content_type='text/markdown',
        long_description=str(readMeFile.read()),
        license='Apache 2.0',
        author='Kitware, Inc.',
        author_email='kitware@kitware.com',
        keywords='',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Web Environment',
            'Framework :: Django :: 3.0',
            'Framework :: Django',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python',
        ],
        python_requires='>=3.8',
        packages=['miqa_python_client'],
        package_dir={"miqa_python_client": "./src"},
        include_package_data=True,
        install_requires=[
            "django-s3-file-field-client",
            "requests",
        ],
    )
