from setuptools import find_packages, setup

package_name = 'cross_consistency_observer'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/cross_consistency_observer.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pipeline-team',
    maintainer_email='todo@todo.com',
    description='Cross-consistency observer for G1 ROS2 Pipeline',
    license='BSD-3-Clause',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'cross_consistency_observer = cross_consistency_observer.cross_consistency_observer:main',
        ],
    },
)
