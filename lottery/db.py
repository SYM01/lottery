import sqlite3

import click
from flask import current_app, g, logging
from flask.cli import with_appcontext

def get_db() -> sqlite3.Connection:
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        try:
            init_db(g.db)
        except Exception as e:
            logging.exception(e)

    return g.db

def close_db(e=None):
    """If this request connected to the database, close the
    connection.
    """
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db(conn:sqlite3.Connection):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS `gifts` (
            `id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            `name`	TEXT NOT NULL,
            `desc`	TEXT NOT NULL,
            `total`	INTEGER NOT NULL DEFAULT 0,
            `winners_count`	INTEGER NOT NULL DEFAULT 0,
            `src`	TEXT NOT NULL,
            `batch`	INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS `candidates` (
            `name`	TEXT NOT NULL,
            PRIMARY KEY(`name`)
        );

        CREATE TABLE IF NOT EXISTS `winners` (
            `id`	INTEGER NOT NULL,
            `name`	TEXT NOT NULL,
            PRIMARY KEY(`id`,`name`)
        );
    ''')

    conn.commit()

@click.command('adduser')
@click.option('-l', type=click.File('r'), required=True)
@with_appcontext
def add_user_command(l):
    conn = get_db()
    init_db(conn)
    cur = conn.cursor()
    click.echo('Add users if not exists.')
    for i in l:
        name = i.strip()
        if len(name) > 0:
            click.echo(name)
            cur.execute('INSERT OR IGNORE INTO candidates (name) VALUES (?)', (name,))
    cur.close()
    conn.commit()


def init_app(app):
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(add_user_command)

def get_lottery_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, name, desc, total, winners_count, src, batch FROM gifts')
    data = cur.fetchall()
    ret = []
    for row in data:
        ret.append({
            'id': row[0],
            'name': row[1],
            'desc': row[2],
            'total': row[3],
            'winners_count': row[4],
            'src': row[5],
            'batch': row[6]
        })
    return ret


def get_not_full_lottery_list(limit, exclude=0):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, desc, total, winners_count, src, batch FROM gifts 
        WHERE id <> ? AND winners_count < total LIMIT ?'''
        , (exclude, limit))
    data = cur.fetchall()
    ret = []
    for row in data:
        ret.append({
            'id': row[0],
            'name': row[1],
            'desc': row[2],
            'total': row[3],
            'winners_count': row[4],
            'src': row[5],
            'batch': row[0]
        })
    return ret


def save_lottery(_id, name:str, desc:str, total:int, src:str, batch:int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO gifts (id, name, desc, total, winners_count, src, batch)
        VALUES (?, ?, ?, ?, (SELECT COUNT(1) FROM winners WHERE id=?), ?, ?)
    ''', (_id, name, desc, total, _id, src, batch))

    cur.close()
    conn.commit()


def get_lottery_info(_id:int):
    # more accurate version
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT name, desc, total, src, batch FROM gifts WHERE id=?', (_id, ))
    gift_data = cur.fetchone()

    if gift_data is None:
        cur.close()
        return None
    
    cur.execute('SELECT name FROM winners WHERE id=? ORDER BY name asc', (_id, ))
    winners_data = cur.fetchall()
    cur.close()

    return {
        'id': _id,
        'name': gift_data[0],
        'desc': gift_data[1],
        'total': int(gift_data[2]),
        'src': gift_data[3],
        'batch': int(gift_data[4]),
        'winners': list(map(lambda x: x[0], winners_data)),
        'candidates': get_candidate_list() 
    }


def get_candidate_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT name FROM candidates ORDER BY name asc')
    candidates_data = cur.fetchall()
    cur.close()
    return list(map(lambda x: x[0], candidates_data))


def new_user(name:str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO candidates (name) VALUES (?)', (name,))
    cur.close()
    conn.commit()


def del_user(name:str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM candidates WHERE name=?', (name,))
    cur.close()
    conn.commit()


def get_winner_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT winners.id AS id, winners.name AS uname, gifts.name AS gname FROM winners 
        INNER JOIN gifts ON gifts.id=winners.id
        ''')

    data = cur.fetchall()
    ret = []
    for row in data:
        ret.append({
            'id': int(row[0]),
            'uname': row[1],
            'gname': row[2],
        })
    return ret


def new_winners(_id:int, names:list):
    conn = get_db()
    cur = conn.cursor()
    for name in names:
        cur.execute("DELETE FROM candidates WHERE name=?", (name,))
        if cur.rowcount > 0:
            cur.execute("INSERT INTO winners VALUES (?, ?)", (_id, name))

    cur.execute("UPDATE gifts SET winners_count=(SELECT COUNT(1) FROM winners WHERE id=?) WHERE id=?", (_id, _id))
    conn.commit()
    return get_lottery_info(_id)


def del_winner(_id:int, name:str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM winners WHERE id=? AND name=?", (_id, name))
    if cur.rowcount > 0:
        cur.execute("INSERT INTO candidates (name) VALUES (?)", (name,))
        cur.execute("UPDATE gifts SET winners_count=(SELECT COUNT(1) FROM winners WHERE id=?) WHERE id=?", (_id, _id))

    conn.commit()

def del_gift(_id:int, name:str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM gifts WHERE id=?", (_id, ))
    if cur.rowcount > 0:
        cur.execute("INSERT OR IGNORE INTO candidates (name) SELECT name FROM winners WHERE id=?", (_id,))
        cur.execute("DELETE FROM winners WHERE id=?", (_id, ))

    conn.commit()