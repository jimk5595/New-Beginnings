import shutil, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'modules', 'weather_and_planetary_intelligence')
if os.path.exists(p):
    shutil.rmtree(p)
    print('module deleted')
else:
    print('already gone')
p2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'static', 'built', 'modules', 'weather_and_planetary_intelligence')
if os.path.exists(p2):
    shutil.rmtree(p2)
    print('built deleted')
