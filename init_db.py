import argparse
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
UPLOADS = BASE_DIR / 'static' / 'uploads'
load_dotenv(BASE_DIR / '.env')

def demo_photo(label, colour):
    from PIL import Image, ImageDraw, ImageFont
    UPLOADS.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (800, 600), colour)
    drawing = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    bounds = drawing.textbbox((0, 0), label, font=font)
    drawing.text(((800 - bounds[2]) / 2, (600 - bounds[3]) / 2), label, fill=(245, 245, 245), font=font)
    name = 'demo_' + uuid.uuid4().hex[:12] + '.jpg'
    image.save(UPLOADS / name, quality=85)
    return name

def main():
    parser = argparse.ArgumentParser(description='Initialize or migrate the MUST Swap SQLite database.')
    parser.add_argument('--database', help='Destination SQLite path; defaults to SQLITE_PATH or must_swap.db.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--migrate-from', metavar='DATABASE', help='Copy and migrate an original or earlier SQLite database.')
    group.add_argument('--reset', action='store_true', help='Back up and replace the destination database.')
    parser.add_argument('--empty', action='store_true', help='Create tables without demo accounts or listings.')
    args = parser.parse_args()
    destination = Path(args.database or os.getenv('SQLITE_PATH') or BASE_DIR / 'must_swap.db').expanduser()
    if not destination.is_absolute():
        destination = BASE_DIR / destination
    os.environ['SQLITE_PATH'] = str(destination.resolve())
    import db
    if args.reset:
        backup = db.backup_database(destination)
        for file in [destination, Path(str(destination) + '-wal'), Path(str(destination) + '-shm')]:
            file.unlink(missing_ok=True)
        db.init_sqlite(destination)
        if backup:
            print('Backup saved to ' + backup)
    if args.migrate_from:
        db.migrate_from(args.migrate_from, destination, UPLOADS)
        print('Source database preserved. Migrated copy: ' + str(destination))
    else:
        db.init_sqlite(destination)
    if not args.empty and (not args.migrate_from):
        seed()
    print('SQLite database ready: ' + str(destination))
    print('Start the application with: python app.py')
    if not args.empty and (not args.migrate_from):
        print('Demo administrator: admin@must.edu.mo / Admin12345')
        print('Demo students: lily.wong@student.must.edu.mo, wang.hao@student.must.edu.mo, chen.jie@student.must.edu.mo / Password123')

def seed():
    import bcrypt
    from db import execute_query, now_str, transaction
    with transaction():
        if execute_query('SELECT COUNT(*) AS n FROM users', fetchone=True)['n']:
            print('Existing accounts found. Demo data was not added.')
            return False
        ids = []
        for name, email, password, role in [('MUST Swap Admin', 'admin@must.edu.mo', 'Admin12345', 'admin'), ('Lily Wong', 'lily.wong@student.must.edu.mo', 'Password123', 'student'), ('Wang Hao', 'wang.hao@student.must.edu.mo', 'Password123', 'student')]:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            ids.append(execute_query('INSERT INTO users(name,email,password_hash,role,is_verified,created_at) VALUES(%s,%s,%s,%s,1,%s)', (name, email, password_hash, role, now_str()), commit=True))
        categories = {row['name']: row['id'] for row in execute_query('SELECT id,name FROM categories', fetchall=True)}
        for seller, category, title, description, price, course, colour in [(ids[1], 'Textbooks & Notes', 'Software engineering textbook', 'Notes for the CS250 course.', 120, 'CS250', (31, 58, 104)), (ids[2], 'Dorm & Daily Use', 'Desk lamp', 'A working desk lamp for a dorm room.', 50, None, (120, 70, 40))]:
            photo = demo_photo(title, colour)
            product_id = execute_query('INSERT INTO products(seller_id,category_id,name,description,price,image,course_code,meeting_place,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (seller, categories[category], title, description, price, photo, course, 'Library entrance', now_str(), now_str()), commit=True)
            pass
    print('Created demo accounts and listings.')
    return True
if __name__ == '__main__':
    main()
