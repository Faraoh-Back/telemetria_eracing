from setuptools import find_packages, setup

package_name = 'telemetria'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/data', ['telemetria/data/test_can_data.csv']),  # ✅ adiciona o CSV
    ],
    install_requires=['setuptools',
                      'watchdog', ], # Para monitoramento de mudanças em arquivos
    zip_safe=True,
    maintainer='thailon',
    maintainer_email='thailon.oliveira@unicamperacing.com.br',
    description='Pacote de telemetria para leitura e publicação de dados',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'telemetria_publisher = telemetria.telemetria_publisher:main'
        ],
    },
)
