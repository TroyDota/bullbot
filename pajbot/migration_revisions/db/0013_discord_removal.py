def up(cursor, bot):
    # new: last_pair record
    cursor.execute('ALTER TABLE "user" DROP COLUMN last_pair;')

    cursor.execute('DROP TABLE user_connections;')
