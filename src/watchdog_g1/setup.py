from setuptools import find_packages, setup

package_name = 'watchdog_g1'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/watchdog_g1.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pipeline-team',
    maintainer_email='todo@todo.com',
    description='Watchdog node for G1 ROS2 Pipeline',
    license='BSD-3-Clause',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'watchdog_g1 = watchdog_g1.watchdog_g1:main',
        ],
    },
)
