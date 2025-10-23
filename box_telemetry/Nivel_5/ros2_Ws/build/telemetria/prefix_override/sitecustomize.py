import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/thailon/Documents/telemetria_eracing/box_telemetry/Nivel_5/ros2_Ws/install/telemetria'
