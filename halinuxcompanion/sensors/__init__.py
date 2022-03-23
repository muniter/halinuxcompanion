import os, pathlib

__all__ = []

# Find all the sensor modules
this_dir = pathlib.Path(__file__).parent.absolute()
for root, dirs, files in os.walk(this_dir):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            sensor = os.path.splitext(os.path.basename(file))[0]
            __all__.append(sensor)
