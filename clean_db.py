import sqlite3  
conn = sqlite3.connect(r'c:\dev\NewBeginnings\backend\database\system_growth.db')  
conn.execute(\"DELETE FROM module_registry WHERE name='weather_app'\")  
conn.commit()  
conn.close()  
print('Done')  
