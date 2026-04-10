import sqlite3

db_path = 'agritech.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

existing = [row[1] for row in cursor.execute('PRAGMA table_info(farms)').fetchall()]

if 'document_url' not in existing:
    cursor.execute('ALTER TABLE farms ADD COLUMN document_url TEXT')
    print('Added document_url to farms')
else:
    print('document_url already exists')

if 'verification_status' not in existing:
    cursor.execute("ALTER TABLE farms ADD COLUMN verification_status TEXT DEFAULT 'pending'")
    print('Added verification_status to farms')
else:
    print('verification_status already exists')

if 'verification_comments' not in existing:
    cursor.execute('ALTER TABLE farms ADD COLUMN verification_comments TEXT')
    print('Added verification_comments to farms')
else:
    print('verification_comments already exists')

conn.commit()
conn.close()
print('Migration complete!')
